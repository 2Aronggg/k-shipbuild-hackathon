#!/usr/bin/env python3
"""
WeldScan AI 관리자 대시보드용 합성 판정 이력 생성기 (기획안 반영판).

실데이터 근거
 - RT 판정기준: kr_reg_vectordb/tables/kr_appx2-7_rt_tables.json 표13·14·15·16
 - VT 판정기준: 동 파일 표12 (외관검사·MT·PT 합격기준)
 - 인용 조항:   kr_reg_vectordb/out/chunks.jsonl 244청크 (citation/page/topics 실값)
 - 클래스 비율: README 용접 RT·일반강재 54,053장 분포
 - 모델 성능·한계: main 브랜치 docs/porosity-yolo-usage.md
   (recall 0.83 / precision 0.97, 기공 단일 클래스, pixel_spacing_mm 0.1 임시값,
    원본 필름 오탐률 27% vs 크롭 0.3%)
 - 에스컬레이션 사유: feature/rag-pipeline-architecture docs 7절 6개 조건

합성 부분: 사람 판정, 보고서 검토 결과, 소요시간, 검색 유사도.
"""
import json, math, random, collections, statistics

random.seed(20261113)
ROOT = "/home/claude/repo/kr_reg_vectordb"
TBL = json.load(open(f"{ROOT}/tables/kr_appx2-7_rt_tables.json"))
CLAUSES = json.load(open("/home/claude/dash/clauses.json"))
DAYS = 90

# ══════════════════════════════════════════ RT 룰 엔진 (표13~16)
T14 = [(1.0, 1), (2.0, 2), (3.0, 3), (4.0, 6), (6.0, 10), (8.0, 15), (float("inf"), 25)]
def score_t14(d):
    for hi, s in T14:
        if d <= hi: return s
    return 25

def limits_t15(t):
    if t <= 10: return ("10x10", 4.0, 6)
    if t <= 25: return ("10x10", 5.0, 12)
    if t <= 50: return ("10x20", t / 5, 24)
    return ("10x20", 10.0, 30)

def limit_t16(t):
    return 6.0 if t <= 12 else (t / 2 if t <= 50 else 24.0)

def ignore_below(t):
    return 0.5 if t <= 25 else 0.7

# ══════════════════════════════════════════ VT 룰 엔진 (표12)
def vt_porosity_limit(t, fillet):
    # 맞대기 d ≤ 0.25t, 필릿 d ≤ 0.25a. 최대지름 3 mm
    return min(0.25 * t, 3.0)

def vt_undercut_limit(fillet, cont_len):
    if fillet: return 0.8
    return 0.8 if cont_len <= 90 else 0.5

# ══════════════════════════════════════════ 등급 (KS B 0845 잠정 매핑)
# KS 원문 미확보. KR 표15·16 상한을 2급 경계로 두고 1급 = 상한의 1/2, 3급 = 상한의 2배로 잠정 설정.
GRADE_ASSUMPTION = "KS B 0845 원문 미확보 — 1·3급 경계는 KR 표15·16 상한의 1/2·2배로 잠정 설정"
def grade_of(margin, hard_fail):
    if hard_fail: return 4
    if margin <= 0.50: return 1
    if margin <= 1.00: return 2
    if margin <= 2.00: return 3
    return 4

# ══════════════════════════════════════════ 현장 컨텍스트
SHIPS = ["컨테이너선", "LNG운반선", "탱커", "벌크선"]
PARTS = [
    ("외판 맞대기",       (14, 34), "porosity", 1, False),
    ("격벽 맞대기",       (10, 22), "slag",     1, False),
    ("후미 곡면부",       (22, 55), "porosity", 3, False),
    ("데크 필릿",         (8, 18),  "lof",      2, True),
    ("배관 원주 용접부",  (8, 26),  "lof",      3, False),
    ("LNG 탱크 멤브레인", (4, 12),  "crack",    3, False),
]
RT_BASE = {"none": 0.438, "porosity": 0.450, "crack": 0.038, "lof": 0.054, "slag": 0.019}
VT_BASE = {"none": 0.52, "surface_porosity": 0.22, "undercut": 0.16,
           "crack_v": 0.04, "lof_v": 0.04, "root_lp": 0.02}
# 모델이 자동 탐지하는 클래스 (main 브랜치: 기공 단일 클래스 학습)
AI_SUPPORTED = {"porosity"}
HARD_FAIL = {"crack", "crack_v", "lof_v", "root_lp"}   # 표13 제3종 / 표12 허용하지 않음

INSPECTORS = []
for i, (name, lvl, bias, k) in enumerate([
    ("정하윤", "신입", +0.24, 3.0), ("Rizky P.", "신입", +0.30, 2.7),
    ("Nguyen T.", "신입", -0.22, 2.9), ("김도현", "신입", +0.14, 3.2),
    ("박서진", "중급", +0.11, 4.4), ("Andi S.", "중급", -0.12, 4.6),
    ("최민규", "중급", +0.03, 4.8), ("이수빈", "중급", -0.19, 4.3),
    ("장영호", "숙련", +0.04, 6.4), ("한재민", "숙련", -0.05, 6.2),
    ("오태석", "숙련", +0.09, 6.0),
    ("윤경석", "시니어", +0.06, 7.0), ("서동현", "시니어", -0.03, 7.2),
]):
    INSPECTORS.append(dict(id=f"I{i+1:02d}", name=name, lvl=lvl, bias=bias, k=k))
SENIORS = [p for p in INSPECTORS if p["lvl"] == "시니어"]
WORKERS = [p for p in INSPECTORS if p["lvl"] != "시니어"]

# ══════════════════════════════════════════ 조항 인용 풀
def pool(*topics):
    c = [x for x in CLAUSES if set(topics) & set(x["topics"])]
    return c or CLAUSES
CITE_POOL = {
    "porosity": pool("porosity", "RT", "acceptance"),
    "crack": pool("crack", "repair"), "crack_v": pool("crack", "repair"),
    "slag": pool("slag", "RT"),
    "lof": pool("lack_of_fusion", "RT"), "lof_v": pool("lack_of_fusion", "MT_PT"),
    "none": pool("RT", "acceptance"),
    "surface_porosity": pool("porosity", "MT_PT", "acceptance"),
    "undercut": pool("MT_PT", "acceptance"), "root_lp": pool("lack_of_fusion", "acceptance"),
}
CITE_W = {k: [1.0 / (i + 1) ** 0.75 for i in range(len(v))] for k, v in CITE_POOL.items()}
def pick_cite(cls):
    return random.choices(CITE_POOL[cls], weights=CITE_W[cls])[0]

def sigmoid(x):
    return 1 / (1 + math.exp(-max(-30, min(30, x))))

# ══════════════════════════════════════════ 케이스 생성
cases, cid = [], 0
for day in range(DAYS):
    dow = (day + 3) % 7
    n = max(1, int(random.gauss((17 if dow < 5 else 5) + day * 0.07, 3)))
    for _ in range(n):
        cid += 1
        method = "VT" if random.random() < 0.27 else "RT"
        ship = random.choices(SHIPS, weights=[4, 3, 2, 2])[0]
        part, (tlo, thi), dom, access, fillet = random.choice(PARTS)
        t = round(random.uniform(tlo, thi), 1)

        score = maxd = len2 = 0.0
        ndef = 0
        lim_a = lim_b = 0.0
        hard = False

        if method == "RT":
            w = dict(RT_BASE); w[dom] *= 2.6
            cls = random.choices(list(w), weights=list(w.values()))[0]
            fov, maxd_lim, score_lim = limits_t15(t)
            len_lim = limit_t16(t)
            ig = ignore_below(t)
            lim_a, lim_b = score_lim, maxd_lim
            if cls == "none":
                margin = random.uniform(0.02, 0.45)
            elif cls == "porosity":
                ds = [d for d in (abs(random.gauss(1.6, 1.5)) + 0.2 for _ in range(random.randint(1, 9))) if d > ig]
                if not ds:
                    cls, margin = "none", random.uniform(0.02, 0.32)
                else:
                    ndef, score, maxd = len(ds), sum(score_t14(d) for d in ds), max(ds)
                    margin = max(score / score_lim, maxd / maxd_lim)
            elif cls in ("slag", "lof"):
                ndef = random.randint(1, 4)
                len2 = round(sum(abs(random.gauss(t * 0.22, t * 0.20)) + 0.6 for _ in range(ndef)), 1)
                lim_a = len_lim
                margin = len2 / len_lim
            else:                                     # crack — 표13 제3종
                hard, ndef = True, random.randint(1, 2)
                len2 = round(abs(random.gauss(t * 0.3, t * 0.2)) + 1.0, 1)
                margin = 3.0
            rule_fov = fov
        else:                                         # ───────── VT, 표12
            w = dict(VT_BASE)
            cls = random.choices(list(w), weights=list(w.values()))[0]
            rule_fov = "육안"
            if cls == "none":
                margin = random.uniform(0.02, 0.45)
            elif cls == "surface_porosity":
                lim_a = vt_porosity_limit(t, fillet)
                maxd = round(abs(random.gauss(lim_a * 0.75, lim_a * 0.45)) + 0.15, 2)
                ndef = random.randint(1, 5)
                margin = maxd / lim_a
            elif cls == "undercut":
                cont = round(abs(random.gauss(70, 45)) + 8, 0)
                lim_a = vt_undercut_limit(fillet, cont)
                maxd = round(abs(random.gauss(lim_a * 0.8, lim_a * 0.5)) + 0.05, 2)
                len2 = cont
                margin = maxd / lim_a
            else:                                     # 균열·융합부족·루트 용입부족 — 허용하지 않음
                hard = True
                maxd = round(abs(random.gauss(2.0, 1.2)) + 0.4, 2)
                margin = 3.0

        rule = 0 if (not hard and margin <= 1.0) else 1
        grade = grade_of(margin, hard)

        # ── 모델 가용 범위 (main 브랜치 실측 반영)
        ai_cls = cls in AI_SUPPORTED and method == "RT"
        cropped = random.random() < 0.78                       # 1280×720 크롭 입력 비율
        scale_known = random.random() < 0.82                   # pixel_spacing_mm 확정 여부
        if ai_cls:
            conf = min(0.99, max(0.05, random.betavariate(7, 2.2)))
            # recall 0.83 → 기공인데 모델이 놓치는 경우
            ai_miss = random.random() > 0.83
        else:
            conf = min(0.99, max(0.05, random.betavariate(3, 3)))
            ai_miss = False
        # 원본(크롭 아님) 정상 필름 오탐률 27% vs 크롭 0.3%
        false_alarm = (cls in ("none",)) and (random.random() < (0.27 if not cropped else 0.003))
        unsupported = (not ai_cls) and cls != "none" and random.random() < 0.28

        insp = random.choices(WORKERS, weights=[2.6] * 8 + [2.3] * 3)[0]
        sim = min(0.97, max(0.05, random.betavariate(5, 3) * (0.78 + 0.19 * day / DAYS)))

        if hard:
            pdet = {"신입": 0.74, "중급": 0.89, "숙련": 0.97}[insp["lvl"]]
            human = 1 if random.random() < pdet else 0
        else:
            theta = 1.0 + insp["bias"] + (0.05 if access == 3 else 0.0)
            human = 1 if random.random() < sigmoid(insp["k"] * (margin - theta)) else 0
        human_grade = grade if human == rule else grade_of(
            margin * (0.75 if human == 0 else 1.35), hard and human == 1)

        gray = 0.85 <= margin <= 1.18
        rule_input_missing = random.random() < 0.018            # 룰 엔진 필수 입력 누락

        # ── 에스컬레이션 사유 (아키텍처 문서 7절 6개 + 판정 불일치·회색지대)
        why = None
        if human != rule:                 why = "판정 불일치"
        elif rule == 1 or grade == 4:     why = "불합격·중대 결함"
        elif ai_cls and conf < 0.35:      why = "탐지 신뢰도 미만"
        elif not scale_known:             why = "스케일 정보 없음"
        elif unsupported:                 why = "미지원 결함 유형"
        elif sim < 0.46:                  why = "RAG 근거 부족"
        elif rule_input_missing:          why = "룰 엔진 입력 누락"
        elif gray:                        why = "회색지대"
        esc = int(why is not None)

        senior = sid = None
        if esc:
            s = random.choice(SENIORS); sid = s["id"]
            if cls == "porosity" and access == 3 and 1.0 < margin <= 1.20:
                senior = 0 if random.random() < 0.78 else 1
            elif hard:
                senior = 1
            else:
                senior = rule if random.random() < 0.93 else 1 - rule

        # ── 판독 소요시간 (기획안 05절: 기존 30~60분 → 목표 5분)
        base = {"신입": 372, "중급": 258, "숙련": 181}[insp["lvl"]]
        learn = 1 - 0.30 * (day / DAYS) * (1.6 if insp["lvl"] == "신입" else 0.6)
        sec = int(max(38, random.gauss(base * learn * (1.5 if gray else 1.0), 46)))

        # ── LLM 보고서 검토 (기획안 05절: 수작업 20~30분 → 목표 5분)
        w_rep = {"accept": 0.62, "edit_text": 0.18, "edit_cite": 0.11, "edit_grade": 0.07, "reject": 0.02}
        if gray: w_rep["edit_grade"] *= 3.2; w_rep["accept"] *= 0.7
        if sim < 0.5: w_rep["edit_cite"] *= 2.6
        rep = random.choices(list(w_rep), weights=list(w_rep.values()))[0]
        rep_sec = int(max(25, random.gauss({"accept": 74, "edit_text": 152, "edit_cite": 243,
                                            "edit_grade": 331, "reject": 402}[rep], 40)))
        c = pick_cite(cls)
        cases.append(dict(
            id=f"WS-{2600+cid:05d}", day=day, method=method, ship=ship, part=part, t=t,
            fillet=fillet, cls=cls, ndef=ndef, score=round(score, 1), maxd=round(maxd, 2),
            len2=len2, lim_a=round(lim_a, 2), lim_b=round(lim_b, 2), fov=rule_fov,
            margin=round(margin, 3), hard=int(hard), grade=grade, rule=rule,
            insp=insp["id"], lvl=insp["lvl"], human=human, hgrade=human_grade,
            gray=int(gray), esc=esc, why=why, senior=senior, sid=sid,
            ai_cls=int(ai_cls), conf=round(conf, 3), ai_miss=int(ai_miss),
            cropped=int(cropped), scale=int(scale_known), falarm=int(false_alarm),
            unsup=int(unsupported), sim=round(sim, 3), sec=sec, rep=rep, rsec=rep_sec,
            cite=c["citation"], cite_title=c["title"], cite_page=c["page"], cite_id=c["chunk_id"],
        ))

# ══════════════════════════════════════════ 집계
rate = lambda a, b: round(a / b, 4) if b else None
N = len(cases)

def reason(c): return c["why"] or "—"
PRIO = {"판정 불일치": 0, "불합격·중대 결함": 1, "탐지 신뢰도 미만": 2, "스케일 정보 없음": 3,
        "미지원 결함 유형": 4, "RAG 근거 부족": 5, "룰 엔진 입력 누락": 6, "회색지대": 7}
queue = sorted([c for c in cases if c["esc"] and c["day"] >= DAYS - 4],
               key=lambda c: (PRIO[c["why"]], -c["margin"]))[:14]

USED = [k for k, _ in collections.Counter(c["cite_id"] for c in cases).most_common()]
by_clause = {x["chunk_id"]: x for x in CLAUSES}
grp = lambda x: f"{x['chapter']}장 {x['section']}절" if x["section"] else str(x["chapter"])
CLIST = [dict(citation=by_clause[k]["citation"], title=by_clause[k]["title"], page=by_clause[k]["page"],
              doc=by_clause[k]["doc_type"], group=grp(by_clause[k])) for k in USED]
CIDX = {k: i for i, k in enumerate(USED)}

tac = collections.defaultdict(lambda: dict(n=0, dev=0, marg=[]))
for c in cases:
    if c["senior"] is None: continue
    g = tac[(c["part"], c["cls"])]; g["n"] += 1
    if c["senior"] != c["rule"]: g["dev"] += 1; g["marg"].append(c["margin"])
tacit = sorted([dict(part=p, cls=cl, n=v["n"], dev=v["dev"], r=rate(v["dev"], v["n"]),
                     marg=round(statistics.mean(v["marg"]), 2) if v["marg"] else None,
                     dirn="관대" if v["marg"] and statistics.mean(v["marg"]) > 1 else "엄격")
                for (p, cl), v in tac.items() if v["dev"] >= 4], key=lambda x: -x["r"])[:8]

QMAP = {"porosity": "기공 결함점수 판정기준", "crack": "터짐 보수 용접 요건", "crack_v": "표면 균열 처리",
        "slag": "슬래그 혼입 합계길이 상한", "lof": "융합불량 판정 및 재검사", "lof_v": "표면 융합부족 허용 여부",
        "none": "RT 시험시야 및 투과사진 등급", "surface_porosity": "표면 기공 지름 허용치",
        "undercut": "언더컷 깊이 허용치", "root_lp": "일면 맞대기 루트 용입부족"}
failq = [dict(id=c["id"], q=f'{c["part"]} / {QMAP[c["cls"]]} (t={c["t"]}mm)', sim=c["sim"],
              part=c["part"], method=c["method"], day=c["day"])
         for c in sorted([c for c in cases if c["sim"] < 0.45], key=lambda c: c["sim"])[:16]]

out = dict(
    meta=dict(service="WeldScan AI", n=N, days=DAYS, generated="2026-11-06",
              corpus_public=54053, corpus_clauses=244,
              model="YOLOv8-seg (기공 단일 클래스)", recall=0.83, precision=0.97, accuracy=0.90,
              pixel_spacing="0.1 mm/px (임시값 — 실측 필요)",
              grade_assumption=GRADE_ASSUMPTION,
              ks_status="KS B 0845 원문 미확보 (sources.yaml skip: true)",
              note="판정 이력·보고서 검토는 합성. 판정표·조항·모델 성능 지표는 실데이터."),
    targets=[  # 기획안 05절 정량 지표
        dict(key="sec", label="판독 소요시간", unit="분", base_lo=30, base_hi=60, goal=5, dir="down"),
        dict(key="dis", label="판정 불일치율", unit="%", base_lo=15, base_hi=20, goal=5, dir="down"),
        dict(key="rsec", label="보고서 작성", unit="분", base_lo=20, base_hi=30, goal=5, dir="down"),
    ],
    tables=TBL["tables"],
    clause_list=CLIST,
    group_total=dict(collections.Counter(grp(x) for x in CLAUSES)),
    inspectors=[dict(id=p["id"], name=p["name"], lvl=p["lvl"]) for p in INSPECTORS],
    tacit=tacit, failq=failq,
    queue=[dict(id=c["id"], method=c["method"], part=c["part"], ship=c["ship"], cls=c["cls"], t=c["t"],
                margin=c["margin"], grade=c["grade"], hgrade=c["hgrade"], rule=c["rule"], human=c["human"],
                lvl=c["lvl"], sim=c["sim"], conf=c["conf"], day=c["day"], cite=c["cite"], why=c["why"],
                score=c["score"], maxd=c["maxd"], len2=c["len2"], lim_a=c["lim_a"], lim_b=c["lim_b"],
                fov=c["fov"], ai_cls=c["ai_cls"], scale=c["scale"], ndef=c["ndef"], hard=c["hard"])
           for c in queue],
    cases=[dict(m=c["margin"], g=c["grade"], hg=c["hgrade"], r=c["rule"], h=c["human"], c=c["cls"],
                p=c["part"], l=c["lvl"], d=c["day"], e=c["esc"], w=c["why"], s=c["sim"], t=c["t"],
                i=c["insp"], sh=c["ship"], mt=c["method"], sv=(-1 if c["senior"] is None else c["senior"]),
                sec=c["sec"], rp=c["rep"], rs=c["rsec"], k=CIDX[c["cite_id"]], ai=c["ai_cls"],
                cf=c["conf"], cr=c["cropped"], sc=c["scale"], fa=c["falarm"], us=c["unsup"],
                am=c["ai_miss"], hd=c["hard"])
           for c in cases],
)
json.dump(out, open("/home/claude/dash/data2.json", "w"), ensure_ascii=False, separators=(",", ":"))

# ══════════════════════════════════════════ 요약
gd = collections.Counter(c["grade"] for c in cases)
print(f"cases={N}  RT={sum(1 for c in cases if c['method']=='RT')}  VT={sum(1 for c in cases if c['method']=='VT')}")
print("등급 분포", {f"{k}급": v for k, v in sorted(gd.items())})
print("규정 일치율", rate(sum(c['human']==c['rule'] for c in cases), N),
      "| 불일치율", round(1-rate(sum(c['human']==c['rule'] for c in cases), N), 4))
print("에스컬레이션", rate(sum(c['esc'] for c in cases), N),
      collections.Counter(c['why'] for c in cases if c['why']).most_common())
print("판독 평균", round(statistics.mean(c['sec'] for c in cases)), "초 |",
      "보고서 평균", round(statistics.mean(c['rsec'] for c in cases)), "초")
print("보고서 검토", collections.Counter(c['rep'] for c in cases).most_common())
print("AI 자동탐지 비율", rate(sum(c['ai_cls'] for c in cases), N),
      "| 크롭 입력", rate(sum(c['cropped'] for c in cases), N),
      "| 스케일 확정", rate(sum(c['scale'] for c in cases), N),
      "| 원본 오탐", sum(c['falarm'] for c in cases))
print("조항 커버리지", rate(len(CLIST), 244))
import os; print("bytes", os.path.getsize("/home/claude/dash/data2.json"))

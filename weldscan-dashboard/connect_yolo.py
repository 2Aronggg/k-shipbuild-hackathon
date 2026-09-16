#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
connect_yolo.py — YOLOv8-seg 검출기와 관리자 대시보드를 잇는 연결 계층.

    [RT 필름]
        ↓ PorosityDetector.predict()          ← weldscan_porosity (main 브랜치)
    [instances[].polygon_xy]
        ↓ major_diameter_px()                  ← 이 파일. 등가지름이 아니라 긴지름
    [긴지름 리스트]
        ↓ margin_rt() / grade_of()             ← KR 2편 적용지침 부록2-7 표14·15·16
    [마진 · 등급]
        ↓ to_payload()
    [real_labels.json]  →  대시보드의 const REAL

────────────────────────────────────────────────────────────────────────
왜 등가지름을 안 쓰는가
────────────────────────────────────────────────────────────────────────
detector.py 문서는 룰엔진 입력으로 instances[].equivalent_diameter_mm 를
쓰라고 안내하지만, 그 값은 2*sqrt(면적/pi) 즉 '같은 면적의 원의 지름'이다.
KR 표14가 요구하는 값은 '결함의 긴지름'이다.

AI허브 RT 일반강재 기공 라벨 10,945개 실측 결과
    긴지름 중앙값   54.4 px
    등가지름 중앙값 40.5 px
    등가/긴지름 중앙값 비율 0.765
등가지름을 그대로 넣으면 결함이 일관되게 ~24% 작게 들어가고,
t=20mm / spacing=0.1 기준 이미지의 10.3%에서 불합격이 합격으로 뒤집힌다.
방향이 '놓치는' 쪽이라 선급 검사에서 터지는 종류의 오류다.

그래서 이 파일은 polygon_xy 에서 긴지름을 직접 계산한다.
polygon_xy 는 스키마 v1.0 에 이미 들어 있으므로 detector 수정이 필요 없다.

────────────────────────────────────────────────────────────────────────
사용법
────────────────────────────────────────────────────────────────────────
1) 가중치로 실제 추론 (best.pt 확보 후)

    python connect_yolo.py detect \
        --artifacts  /path/to/porosity_yolov8seg \
        --images     /path/to/films \
        --src        weldscan_porosity/src \
        --spacing    0.1 \
        --thickness  20 \
        --out        real_labels.json

2) 가중치 없이 라벨로 페이로드 생성 (지금 대시보드가 쓰는 경로)

    python connect_yolo.py from-labels \
        --labels  "02.라벨링데이터/TL_RTST_결함_2. 기공" \
        --out     real_labels.json

3) 파이썬에서 직접

    from connect_yolo import judge_detection
    r = judge_detection(det.predict(img, pixel_spacing_mm=0.1), thickness_mm=20.0)
    r["margin"], r["grade"], r["verdict"]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from typing import Any, Iterable, Sequence

import numpy as np

SCHEMA_IN = "1.0"          # 소비하는 detector 출력 스키마
PAYLOAD_VERSION = "2.0"    # 이 파일이 뱉는 대시보드 페이로드 버전

# ══════════════════════════════════════════════════════════════════════
# 1. 기하 — 긴지름
# ══════════════════════════════════════════════════════════════════════
def major_diameter_px(polygon_xy: Sequence[Sequence[float]]) -> float:
    """폴리곤 정점 간 최대 거리 = 결함의 긴지름(px).

    KR 표14의 '결함의 긴지름'에 대응한다.
    정점 수가 많아도 실측 기공 라벨은 수십 점 수준이라 완전탐색으로 충분하다.
    """
    p = np.asarray(polygon_xy, dtype=float)
    if p.ndim != 2 or p.shape[0] < 2:
        return 0.0
    d2 = ((p[:, None, :] - p[None, :, :]) ** 2).sum(-1)
    return float(math.sqrt(d2.max()))


def polygon_area_px(polygon_xy: Sequence[Sequence[float]]) -> float:
    """shoelace 면적(px^2). 참고용 — 판정에는 쓰지 않는다."""
    p = np.asarray(polygon_xy, dtype=float)
    if p.ndim != 2 or p.shape[0] < 3:
        return 0.0
    x, y = p[:, 0], p[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)


# ══════════════════════════════════════════════════════════════════════
# 2. 룰 엔진 — KR 2편 적용지침 부록 2-7 7항
#    출처: kr_reg_vectordb/tables/kr_appx2-7_rt_tables.json
# ══════════════════════════════════════════════════════════════════════
def score_t14(d_mm: float) -> int:
    """표14 결함점수. d = 결함의 긴지름(mm)."""
    if d_mm <= 1.0:  return 1
    if d_mm <= 2.0:  return 2
    if d_mm <= 3.0:  return 3
    if d_mm <= 4.0:  return 6
    if d_mm <= 6.0:  return 10
    if d_mm <= 8.0:  return 15
    return 25


def limits_t15(t_mm: float) -> tuple[str, float, int]:
    """표15 제1종(둥근 결함). 반환 = (시험시야, 최대결함크기 상한mm, 결함점수 상한)."""
    if t_mm <= 10:  return ("10x10", 4.0, 6)
    if t_mm <= 25:  return ("10x10", 5.0, 12)
    if t_mm <= 50:  return ("10x20", t_mm / 5, 24)
    return ("10x20", 10.0, 30)


def limit_t16(t_mm: float) -> float:
    """표16 제2종(가늘고 긴 결함) 합계길이 상한mm."""
    if t_mm <= 12:  return 6.0
    if t_mm <= 50:  return t_mm / 2
    return 24.0


def ignore_below(t_mm: float) -> float:
    """무시할 수 있는 결함의 긴지름 상한mm."""
    return 0.5 if t_mm <= 25 else 0.7


def margin_rt_porosity(diams_mm: Iterable[float], t_mm: float) -> dict:
    """RT 제1종(기공) 규정 마진.

    마진 = max(결함점수합 / 점수상한, 최대결함크기 / 크기상한)
    1.0 이 합격선.
    """
    ig = ignore_below(t_mm)
    ds = [d for d in diams_mm if d > ig]
    fov, maxd_lim, score_lim = limits_t15(t_mm)
    if not ds:
        return dict(margin=0.0, hard=False, n_counted=0, score=0, max_d=0.0,
                    fov=fov, limit_score=score_lim, limit_maxd=round(maxd_lim, 3),
                    ignored_below=ig)
    score = sum(score_t14(d) for d in ds)
    max_d = max(ds)
    return dict(
        margin=round(max(score / score_lim, max_d / maxd_lim), 4),
        hard=False, n_counted=len(ds), score=score, max_d=round(max_d, 3),
        fov=fov, limit_score=score_lim, limit_maxd=round(maxd_lim, 3),
        ignored_below=ig,
    )


def margin_rt_elongated(lengths_mm: Iterable[float], t_mm: float) -> dict:
    """RT 제2종(슬래그·융합불량) 마진 = 합계길이 / 길이상한."""
    lim = limit_t16(t_mm)
    tot = float(sum(lengths_mm))
    return dict(margin=round(tot / lim, 4), hard=False, total_len=round(tot, 3),
                limit_len=round(lim, 3))


def grade_of(margin: float, hard_fail: bool = False) -> int:
    """KS B 0845 1~4급 잠정 매핑.

    ⚠ KS B 0845 원문 미확보. KR 표15·16 상한을 2급 경계로 두고
      1급 = 상한의 1/2, 3급 = 상한의 2배로 잠정 설정한 값이다.
      원문 확보 시 이 함수만 교체하면 된다.
    """
    if hard_fail:      return 4
    if margin <= 0.50: return 1
    if margin <= 1.00: return 2
    if margin <= 2.00: return 3
    return 4


GRADE_ASSUMPTION = ("KS B 0845 원문 미확보 — 1·3급 경계는 "
                    "KR 표15·16 상한의 1/2·2배로 잠정 설정")


# ══════════════════════════════════════════════════════════════════════
# 3. detector 출력 → 판정
# ══════════════════════════════════════════════════════════════════════
def judge_detection(det_out: dict, thickness_mm: float,
                    pixel_spacing_mm: float | None = None) -> dict:
    """PorosityDetector.predict() / tile_predict() 출력 한 건을 판정한다.

    det_out : 스키마 v1.0 dict
    thickness_mm : 모재두께. 규정표 조회에 필수.
    pixel_spacing_mm : 생략하면 det_out["image"]["pixel_spacing_mm"] 사용.
    """
    if det_out.get("schema_version") != SCHEMA_IN:
        raise ValueError(
            f'detector 스키마 {det_out.get("schema_version")} != {SCHEMA_IN}. '
            "detector.py 갱신 여부 확인 필요."
        )
    sp = pixel_spacing_mm
    if sp is None:
        sp = det_out.get("image", {}).get("pixel_spacing_mm")

    warn = list(det_out.get("warnings", []))
    if not sp:
        warn.append("pixel_spacing_mm 없음 — mm 환산 불가, 판정 보류")
        return dict(verdict="보류", margin=None, grade=None, reason="스케일 정보 없음",
                    majors_px=[], majors_mm=[], warnings=warn,
                    n_instances=det_out.get("n_instances", 0))

    majors_px = [major_diameter_px(i["polygon_xy"]) for i in det_out.get("instances", [])]
    majors_mm = [d * sp for d in majors_px]

    r = margin_rt_porosity(majors_mm, thickness_mm)
    g = grade_of(r["margin"], r["hard"])

    # detector 가 안내하는 등가지름을 그대로 썼을 때와의 차이 — 감사용
    eq_mm = [i.get("equivalent_diameter_mm") for i in det_out.get("instances", [])]
    eq_mm = [v for v in eq_mm if v]
    r_eq = margin_rt_porosity(eq_mm, thickness_mm) if eq_mm else None

    out = dict(
        verdict="불합격" if (r["hard"] or r["margin"] > 1.0) else "합격",
        margin=r["margin"], grade=g, defect_type="porosity",
        thickness_mm=thickness_mm, pixel_spacing_mm=sp,
        majors_px=[round(d, 2) for d in majors_px],
        majors_mm=[round(d, 3) for d in majors_mm],
        rule=r, warnings=warn,
        n_instances=det_out.get("n_instances", 0),
        detector_score=det_out.get("score"),
        image=det_out.get("image", {}).get("path"),
    )
    if r_eq is not None:
        out["audit_equivalent_diameter"] = dict(
            margin=r_eq["margin"], grade=grade_of(r_eq["margin"]),
            flipped=(r["margin"] > 1.0) and (r_eq["margin"] <= 1.0),
            note="detector 문서가 안내하는 등가지름을 그대로 썼을 경우. flipped=true면 그 경로에서 판정이 뒤집힘",
        )
    return out


# ══════════════════════════════════════════════════════════════════════
# 4. 대시보드 페이로드
#    대시보드의 const REAL 이 기대하는 형태와 동일.
#    행 = [검사방법코드, 결함클래스코드, 긴지름px, 긴지름px, ...]
#    px 로 넣어야 대시보드의 pixel_spacing 슬라이더가 계속 동작한다.
# ══════════════════════════════════════════════════════════════════════
TYPE_CODES = {"RT": 0, "VT": 1}
CLASS_CODES = {"none": 0, "porosity": 1, "slag": 2, "lof": 3,
               "crack": 4, "lp": 5, "undercut": 6}


def to_payload(records: list[dict], *, source: str,
               n_images_total: int | None = None,
               n_defects_total: int | None = None,
               sample_rate: float = 1.0) -> dict:
    """판정 레코드 목록 → 대시보드 REAL 페이로드."""
    rows = []
    for r in records:
        mt = TYPE_CODES.get(r.get("method", "RT"), 0)
        cl = CLASS_CODES.get(r.get("cls", "porosity"), 1)
        rows.append([mt, cl] + [round(float(d)) for d in r.get("majors_px", [])])
    n_def = sum(len(x) - 2 for x in rows)
    return {
        "payload_version": PAYLOAD_VERSION,
        "source": source,
        "measured": "긴지름 = 폴리곤 정점 간 최대 거리(px). 등가지름 아님",
        "grade_assumption": GRADE_ASSUMPTION,
        "n_images_total": n_images_total if n_images_total is not None else len(rows),
        "n_defects_total": n_defects_total if n_defects_total is not None else n_def,
        "sample_rate": sample_rate,
        "n_sample": len(rows),
        "type_codes": TYPE_CODES,
        "class_codes": CLASS_CODES,
        "note": "행 = [검사방법코드, 결함클래스코드, 긴지름px...]. 긴지름 0개면 정상",
        "rows": rows,
    }


# ══════════════════════════════════════════════════════════════════════
# 5. 실행 경로 A — 가중치로 추론
# ══════════════════════════════════════════════════════════════════════
def load_detector(artifacts_dir: str, src_dir: str | None = None, device: str | None = None):
    """weldscan_porosity 의 PorosityDetector 를 로드한다."""
    if src_dir:
        sys.path.insert(0, os.path.abspath(src_dir))
    try:
        from porosity.detector import PorosityDetector
    except ImportError as e:
        raise SystemExit(
            "porosity 패키지를 찾을 수 없음.\n"
            "  --src 로 weldscan_porosity/src 경로를 지정하거나 PYTHONPATH에 추가할 것.\n"
            f"  원인: {e}"
        )
    need = ["best.pt", "thresholds.json", "model_config.json"]
    missing = [f for f in need if not os.path.exists(os.path.join(artifacts_dir, f))]
    if missing:
        raise SystemExit(
            f"가중치 아티팩트 누락: {', '.join(missing)}\n"
            f"  경로: {artifacts_dir}\n"
            "  best.pt(~24MB)는 용량 문제로 Git에 없음. 담당자에게 "
            "porosity_yolov8seg.zip 을 받아 압축 해제할 것 (docs/porosity-yolo-usage.md)."
        )
    return PorosityDetector.from_artifacts(artifacts_dir, device=device)


def run_detect(args) -> None:
    det = load_detector(args.artifacts, args.src, args.device)
    paths = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tif", "*.tiff"):
        paths += glob.glob(os.path.join(args.images, "**", ext), recursive=True)
    paths.sort()
    if not paths:
        raise SystemExit(f"이미지 없음: {args.images}")

    recs, flips, n_hold = [], 0, 0
    for i, p in enumerate(paths, 1):
        out = (det.tile_predict(p, pixel_spacing_mm=args.spacing) if args.tiled
               else det.predict(p, pixel_spacing_mm=args.spacing))
        j = judge_detection(out, args.thickness)
        if j["margin"] is None:
            n_hold += 1
            continue
        if j.get("audit_equivalent_diameter", {}).get("flipped"):
            flips += 1
        recs.append(dict(method="RT", cls="porosity", majors_px=j["majors_px"],
                         margin=j["margin"], grade=j["grade"], verdict=j["verdict"],
                         image=p))
        if i % 50 == 0:
            print(f"  {i}/{len(paths)}", file=sys.stderr)

    pay = to_payload(recs, source=f"YOLOv8-seg 추론 · {args.images}")
    json.dump(pay, open(args.out, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    rej = sum(1 for r in recs if r["margin"] > 1.0)
    print(f"판정 {len(recs)}건 (보류 {n_hold}건) · 불합격 {rej}건 "
          f"({100*rej/max(1,len(recs)):.1f}%) → {args.out}")
    if flips:
        print(f"⚠ 등가지름 경로였다면 판정이 뒤집혔을 건: {flips}건 "
              f"({100*flips/max(1,len(recs)):.1f}%)")
    if args.report:
        json.dump(recs, open(args.report, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"건별 상세 → {args.report}")


# ══════════════════════════════════════════════════════════════════════
# 6. 실행 경로 B — 라벨 JSON 으로 페이로드 생성 (가중치 불필요)
#    지금 대시보드가 쓰고 있는 경로. detector 연결 전까지의 기준선.
# ══════════════════════════════════════════════════════════════════════
KO_CLASS = {"정상": "none", "균열": "crack", "기공": "porosity", "융합불량": "lof",
            "슬래그혼입": "slag", "용입부족": "lp", "언더컷": "undercut"}


def run_from_labels(args) -> None:
    files = []
    for d in args.labels:
        files += glob.glob(os.path.join(d, "**", "*.json"), recursive=True)
    if not files:
        raise SystemExit(f"라벨 JSON 없음: {args.labels}")
    if args.sample_rate < 1.0:
        import random
        random.seed(args.seed)
        files = [f for f in files if random.random() < args.sample_rate]

    recs, n_def = [], 0
    for p in files:
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        info, img = d.get("info", {}), d.get("image_data", {})
        cls = KO_CLASS.get(img.get("information"), "none")
        method = "VT" if str(info.get("type", "")).upper().startswith("VT") else "RT"
        majors = []
        for a in d.get("annotations", []):
            if a.get("class") == "normal":      # 정상 이미지의 비드 영역 — 결함 아님
                continue
            c = a.get("coordinate", {})
            poly = list(zip(c.get("x", []), c.get("y", [])))
            m = major_diameter_px(poly)
            if m > 0:
                majors.append(m)
        n_def += len(majors)
        recs.append(dict(method=method, cls=cls, majors_px=majors))

    pay = to_payload(recs, source="AI허브 창원 용접 AI 학습데이터 · 라벨 폴리곤 실측",
                     sample_rate=args.sample_rate)
    json.dump(pay, open(args.out, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"이미지 {len(recs)} · 결함 {n_def} → {args.out} "
          f"({os.path.getsize(args.out)/1024:.0f} KB)")


# ══════════════════════════════════════════════════════════════════════
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("detect", help="가중치로 추론 후 페이로드 생성")
    d.add_argument("--artifacts", required=True, help="best.pt 가 있는 폴더")
    d.add_argument("--images", required=True, help="RT 이미지 폴더")
    d.add_argument("--src", default=None, help="weldscan_porosity/src 경로")
    d.add_argument("--spacing", type=float, default=0.1, help="pixel_spacing_mm")
    d.add_argument("--thickness", type=float, default=20.0, help="모재두께 mm")
    d.add_argument("--tiled", action="store_true", help="원본 파노라마면 타일 추론")
    d.add_argument("--device", default=None, help='"0" 또는 "cpu"')
    d.add_argument("--out", default="real_labels.json")
    d.add_argument("--report", default=None, help="건별 상세 JSON 경로")
    d.set_defaults(func=run_detect)

    l = sub.add_parser("from-labels", help="라벨 JSON 으로 페이로드 생성 (가중치 불필요)")
    l.add_argument("--labels", required=True, nargs="+", help="라벨 JSON 폴더(들)")
    l.add_argument("--sample-rate", type=float, default=1.0)
    l.add_argument("--seed", type=int, default=20261113)
    l.add_argument("--out", default="real_labels.json")
    l.set_defaults(func=run_from_labels)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()

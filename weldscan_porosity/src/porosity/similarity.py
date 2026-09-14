"""
porosity.similarity
====================
형태·분포·크기 프로파일(CaseProfile) 기반 유사사례 검색 + 보고서 생성.

파이프라인 ⑤ "유사사례 매칭 + 위험도 산출" 단계를 구현한다.

역할 분리 주의:
  - 이 모듈은 "GT 라벨상 기공이 있었는가(abnormal/normal)"만 판정 근거로 쓴다.
  - KS B 0845 등급(합격/불합격) 판정은 이 모듈의 책임이 아니다 (룰엔진 담당 파트).
    여기서 말하는 "위험도"는 등급 판정이 아니라 "유사 사례 중 결함이 있었던 비율"이다.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from .case_features import CaseProfile, WEIGHT_DISTRIBUTION, WEIGHT_SHAPE, WEIGHT_SIZE

FINE_TIEBREAK_WEIGHT = 0.12
# ↑ 형태/분포/크기 카테고리 유사도(coarse)가 순위를 주도하되, 그 안에서 동점이
#   나면 연속값(개수/평균직경/공간퍼짐)으로 미세하게 갈라준다.
# 근거: shape_elongated_ratio·size_hist는 인스턴스 개수(n)로 나눈 비율이라
#   n이 작을 때(중앙값 3~4개) 0/0.25/0.5/0.75/1.0 같은 이산값에만 찍힌다.
#   24,000+ 건 DB에서는 이 이산값 + 분포 카테고리 조합이 우연히 겹치는 사례가
#   흔해서, tiebreak 없이는 서로 다른 사례들이 전부 score=1.000으로 묶여
#   "그중 무엇이 더 비슷한지" 구분이 안 됐다 (실제로 발생한 문제, 수정함).


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def continuous_tiebreak(p1: CaseProfile, p2: CaseProfile) -> float:
    """카테고리로 뭉개지기 전의 연속값들로 미세 유사도 계산 (0~1)."""
    n1, n2 = p1.n_instances, p2.n_instances
    n_sim = 1.0 - min(1.0, abs(n1 - n2) / max(n1, n2, 1))

    d1, d2 = _safe_mean(p1.diameters), _safe_mean(p2.diameters)
    ref = max(d1, d2, 1e-6)
    d_sim = 1.0 - min(1.0, abs(d1 - d2) / ref)

    e1 = (p1.distribution_stats or {}).get("extent_ratio")
    e2 = (p2.distribution_stats or {}).get("extent_ratio")
    e_sim = (1.0 - min(1.0, abs(e1 - e2))) if (e1 is not None and e2 is not None) else 0.5

    # 내부 패킹 패턴(평균 최근접 거리) - extent가 같아도 "몇 개씩 뭉쳐있는지 vs
    # 고르게 퍼졌는지"를 구분해준다. 단독/군집(값 없음)이면 중립값 사용.
    nn1 = (p1.distribution_stats or {}).get("mean_nn_norm")
    nn2 = (p2.distribution_stats or {}).get("mean_nn_norm")
    nn_sim = (1.0 - min(1.0, abs(nn1 - nn2))) if (nn1 is not None and nn2 is not None) else 0.5

    return (n_sim + d_sim + e_sim + nn_sim) / 4.0


# 분포 카테고리 간 "완전히 다르진 않은" 정도 (0~1). 대각선(자기 자신)은 1.0.
_DIST_ADJACENCY = {
    ("산재", "군집"): 0.5, ("군집", "산재"): 0.5,
    ("산재", "선상"): 0.3, ("선상", "산재"): 0.3,
    ("군집", "선상"): 0.3, ("선상", "군집"): 0.3,
    ("단독", "산재"): 0.2, ("산재", "단독"): 0.2,
    ("단독", "군집"): 0.2, ("군집", "단독"): 0.2,
}


def distribution_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if a == "해당없음" or b == "해당없음":
        return 0.0
    return _DIST_ADJACENCY.get((a, b), 0.0)


def distribution_similarity_detailed(p1: CaseProfile, p2: CaseProfile) -> float:
    """
    분포(형태) 축 최종 유사도 = 카테고리 일치 여부(60%) + 실제 퍼진 정도(extent_ratio,
    40%)의 혼합.

    카테고리만으로 판단하면 "둘 다 산재"인 경우 무조건 1.0이 찍혀서(퍼진 정도가
    실제로 얼마나 다르든 상관없이), 가장 큰 가중치(★★★)를 가진 이 축이 너무 쉽게
    포화(1.0)돼버린다. 그 결과 전체 유사도 점수가 좁은 고득점 구간에만 몰리는
    문제가 생겼다(실측: top5가 전부 0.997~0.998). extent_ratio(점들 간 최대거리/
    이미지 대각선, distribution_category()가 이미 계산해둔 값)를 섞어, 같은
    카테고리 안에서도 실제 배치가 얼마나 비슷한지에 따라 점수가 자연스럽게
    퍼지도록 한다.
    """
    cat_sim = distribution_similarity(p1.distribution, p2.distribution)
    e1 = (p1.distribution_stats or {}).get("extent_ratio")
    e2 = (p2.distribution_stats or {}).get("extent_ratio")
    if e1 is None or e2 is None:
        return cat_sim  # 단독/해당없음처럼 extent 정보가 없는 경우 카테고리만 사용
    spatial_sim = 1.0 - min(1.0, abs(e1 - e2))
    return 0.6 * cat_sim + 0.4 * spatial_sim


def size_hist_similarity(h1: dict, h2: dict) -> float:
    """크기 분포(소/중/대 비율)의 L1 거리 -> 유사도. 완전 동일=1, 완전 반대=0."""
    l1 = sum(abs(h1.get(k, 0.0) - h2.get(k, 0.0)) for k in ("소", "중", "대"))
    return 1.0 - l1 / 2.0


def profile_similarity(
    p1: CaseProfile, p2: CaseProfile,
    w_dist: float = WEIGHT_DISTRIBUTION, w_shape: float = WEIGHT_SHAPE,
    w_size: float = WEIGHT_SIZE,
    fine_weight: float = FINE_TIEBREAK_WEIGHT,
) -> tuple[float, dict]:
    """가중 유사도 점수(0~1) + 축별 기여도 breakdown.
    coarse(형태/분포/크기 카테고리) 점수가 순위를 주도하고, fine(연속값)
    tiebreak은 작은 비중(기본 12%)으로만 섞여 같은 카테고리 안의 동점을 갈라준다."""
    s_dist = distribution_similarity_detailed(p1, p2)
    s_shape = 1.0 - abs(p1.shape_elongated_ratio - p2.shape_elongated_ratio)
    s_size = size_hist_similarity(p1.size_hist, p2.size_hist)

    total_w = w_dist + w_shape + w_size
    coarse = (s_dist * w_dist + s_shape * w_shape + s_size * w_size) / total_w
    fine = continuous_tiebreak(p1, p2)
    score = coarse * (1.0 - fine_weight) + fine * fine_weight

    breakdown = {"distribution": round(s_dist, 3), "shape": round(s_shape, 3),
                "size": round(s_size, 3), "fine_tiebreak": round(fine, 3),
                "coarse": round(coarse, 3)}
    return float(score), breakdown


# --- Case DB -------------------------------------------------------------
def profile_to_row(p: CaseProfile) -> dict:
    row = asdict(p)
    row["size_hist"] = json.dumps(row["size_hist"], ensure_ascii=False)
    row["distribution_stats"] = json.dumps(row["distribution_stats"], ensure_ascii=False)
    row["diameters"] = json.dumps(row["diameters"])
    row["meta"] = json.dumps(row["meta"], ensure_ascii=False)
    return row


def row_to_profile(row: pd.Series) -> CaseProfile:
    return CaseProfile(
        n_instances=int(row["n_instances"]),
        distribution=row["distribution"],
        distribution_stats=json.loads(row["distribution_stats"]),
        shape_elongated_ratio=float(row["shape_elongated_ratio"]),
        size_hist=json.loads(row["size_hist"]),
        diameters=json.loads(row["diameters"]),
        verdict=row.get("verdict"),
        meta=json.loads(row["meta"]),
    )


def save_case_db(profiles: list[CaseProfile], size_thresholds: tuple[float, float],
                 path: str | Path) -> Path:
    """case DB를 parquet(프로필) + json(크기 임계값)으로 저장."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([profile_to_row(p) for p in profiles])
    df.to_parquet(path / "case_db.parquet", index=False)
    (path / "size_thresholds.json").write_text(
        json.dumps({"lo": size_thresholds[0], "hi": size_thresholds[1]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_case_db(path: str | Path) -> tuple[pd.DataFrame, tuple[float, float]]:
    path = Path(path)
    df = pd.read_parquet(path / "case_db.parquet")
    th = json.loads((path / "size_thresholds.json").read_text(encoding="utf-8"))
    return df, (th["lo"], th["hi"])


# --- 검색 ------------------------------------------------------------------
def find_similar_cases(
    new_profile: CaseProfile, case_db: pd.DataFrame, k: int = 5,
    w_dist: float = WEIGHT_DISTRIBUTION, w_shape: float = WEIGHT_SHAPE,
    w_size: float = WEIGHT_SIZE,
) -> list[dict]:
    """case_db 전체와 비교해 유사도 상위 k건 반환.
    반환 항목: {"score", "breakdown", "profile": CaseProfile}"""
    results = []
    for _, row in case_db.iterrows():
        cp = row_to_profile(row)
        score, breakdown = profile_similarity(new_profile, cp, w_dist, w_shape, w_size)
        results.append({"score": score, "breakdown": breakdown, "profile": cp})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]


def find_similar_cases_diverse(
    new_profile: CaseProfile, case_db: pd.DataFrame, k: int = 5,
    pool_size: int = 50, lambda_relevance: float = 0.5,
    w_dist: float = WEIGHT_DISTRIBUTION, w_shape: float = WEIGHT_SHAPE,
    w_size: float = WEIGHT_SIZE,
) -> list[dict]:
    """
    MMR(Maximal Marginal Relevance) 기반 유사사례 선택.

    단순 top-k는 24,000+ 건 DB에서 "신규 사진과 거의 완전히 동일한 복제품 여러 개"를
    반환하기 쉽다(실측: n/평균직경/퍼짐정도가 거의 같은 사례가 다수 존재) - 유사도
    수치 자체는 정확하지만, 5건을 나란히 보여줄 때는 서로 다른 관점의 사례를
    보여주는 게 검사자에게 더 유용하다.

    그래서 가중치를 조작해 점수를 억지로 벌리는 대신(진짜 유사도를 왜곡함),
    "1등은 무조건 최고 매치, 2등부터는 신규 사진과 충분히 비슷하면서도(관련성)
    이미 뽑힌 사례들과는 겹치지 않는(다양성) 것"을 고르는 방식으로 바꾼다.
    반환되는 score는 여전히 신규 사진과의 **진짜** 유사도이며, MMR은 오직
    "어떤 걸 보여줄지" 선택에만 관여한다. 단, 클론들이 압도적으로 촘촘하고
    실제로 다른 유형의 사례는 점수 낙폭이 크다면(예: 0.999 -> 0.6), 그 경우엔
    다양성보다 관련성이 우선이라 계속 클론이 뽑히는 게 오히려 정직한 결과다 -
    이때는 lambda_relevance를 낮춰서 다양성 비중을 늘릴 수 있다.

    lambda_relevance: 1.0에 가까울수록 관련성 우선(=일반 top-k와 동일),
        낮을수록 다양성을 더 중시한다. 기본 0.5.
    pool_size: MMR을 적용할 후보 풀 크기. 전체 DB가 아니라 이 안에서만
        다양성을 따져 계산 비용을 낮춘다.
    """
    pool = find_similar_cases(new_profile, case_db, k=pool_size,
                              w_dist=w_dist, w_shape=w_shape, w_size=w_size)
    if len(pool) <= k:
        return pool

    selected: list[dict] = [pool[0]]
    remaining = pool[1:]

    while len(selected) < k and remaining:
        best_idx, best_val = None, -1e9
        for i, cand in enumerate(remaining):
            max_sim_to_selected = max(
                profile_similarity(cand["profile"], s["profile"],
                                   w_dist, w_shape, w_size)[0]
                for s in selected
            )
            mmr_val = (lambda_relevance * cand["score"]
                      - (1 - lambda_relevance) * max_sim_to_selected)
            if mmr_val > best_val:
                best_idx, best_val = i, mmr_val
        selected.append(remaining.pop(best_idx))

    # 선택은 MMR 순서로 했지만, 화면에는 진짜 유사도 순으로 정렬해서 보여준다
    # (선택 순서와 표시 순서를 분리 - 헷갈리지 않게).
    selected.sort(key=lambda r: r["score"], reverse=True)
    return selected


# --- 보고서 ------------------------------------------------------------------
_DIM_KOR = {"distribution": "기공 배치 패턴", "shape": "기공 형태", "size": "기공 크기"}


def generate_report(new_profile: CaseProfile, matches: list[dict]) -> dict:
    """
    초보 검사자가 바로 이해할 수 있는 요약 보고서.
    schema:
      risk_level: "높음"|"보통"|"낮음"|"해당없음"
      n_similar, n_abnormal_in_similar
      summary_text: 자연어 한 줄 요약 (템플릿 기반, 고정 규칙 - LLM 아님)
      avg_similarity_breakdown: 축별 평균 기여도
      matches: [{"score","breakdown","verdict","n_instances","distribution",
                 "shape_elongated_ratio","size_hist","meta"}, ...]
    """
    n = len(matches)
    if n == 0:
        return {"risk_level": "해당없음", "n_similar": 0, "n_abnormal_in_similar": 0,
                "summary_text": "비교할 유사 사례가 없습니다.",
                "avg_similarity_breakdown": {}, "matches": []}

    n_abnormal = sum(1 for m in matches if m["profile"].verdict == "abnormal")
    ratio = n_abnormal / n
    risk = "높음" if ratio >= 0.6 else ("보통" if ratio >= 0.3 else "낮음")

    avg_breakdown = {
        dim: float(np.mean([m["breakdown"][dim] for m in matches]))
        for dim in ("distribution", "shape", "size")
    }
    top_dim = max(avg_breakdown, key=avg_breakdown.get)

    new_desc = (f"이번 사진은 기공 {new_profile.n_instances}개, "
               f"배치는 '{new_profile.distribution}'"
               + (f", 크기는 대부분 '{max(new_profile.size_hist, key=new_profile.size_hist.get)}'"
                  if new_profile.n_instances else "") + " 입니다.")

    summary_text = (
        f"유사 사례 {n}건 중 {n_abnormal}건이 실제로 기공 결함이 있었습니다 "
        f"(위험도: {risk}). 가장 비슷했던 특징은 {_DIM_KOR[top_dim]}입니다. {new_desc}"
    )

    match_out = []
    for m in matches:
        p = m["profile"]
        match_out.append({
            "score": round(m["score"], 3),
            "breakdown": m["breakdown"],
            "verdict": p.verdict,
            "n_instances": p.n_instances,
            "distribution": p.distribution,
            "shape_elongated_ratio": round(p.shape_elongated_ratio, 3),
            "size_hist": {k: round(v, 3) for k, v in p.size_hist.items()},
            "meta": p.meta,
        })

    return {
        "risk_level": risk,
        "n_similar": n,
        "n_abnormal_in_similar": n_abnormal,
        "summary_text": summary_text,
        "avg_similarity_breakdown": {k: round(v, 3) for k, v in avg_breakdown.items()},
        "matches": match_out,
    }

"""
porosity.case_db_build
=======================
metadata.csv의 GT 라벨을 그대로 "실제 판정"으로 취급해 초기 사례 DB를 구축한다.

  annotation_case == 'porosity' (단일결함만, is_crowd==0) -> verdict='abnormal'
  annotation_case == 'normal'   (원본 1280x720 타일만)     -> verdict='normal'

나중에 실제 현장 판정 이력(파이프라인 ⑨ 단계에서 누적)이 쌓이면, 이 초기 DB에
이어붙이거나 교체하면 된다 - CaseProfile 스키마가 동일해 호환된다.

2단계로 진행하는 이유: 크기(소/중/대) 임계값은 "이 데이터셋 전체 기공이 대략
몇 mm대인가"를 봐야 정할 수 있다. 그래서 1차로 전체 폴리곤을 파싱해 등가직경
분포부터 모으고, 그 분포의 33/67 백분위로 임계값을 고정한 뒤, 2차로 각 이미지의
CaseProfile을 생성한다. 이 임계값은 신규 이미지 분류에도 동일하게 재사용해야
"소/중/대" 기준이 일관된다 - similarity.save_case_db()가 함께 저장해준다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from . import config as cfg
from . import label_io as L
from .case_features import CaseProfile, build_case_profile, compute_size_thresholds
from .detector import _poly_area  # 순수 함수 - 이 임포트는 torch/ultralytics를 끌어오지 않음


def _gt_polygons_to_instances(
    polygons: list[list[float]], img_w: int, img_h: int,
    pixel_spacing_mm: float | None,
) -> list[dict]:
    """label_io가 뽑은 정규화 폴리곤 -> case_features가 기대하는
    instance-like dict(픽셀 좌표/면적/등가직경). PorosityDetector.predict()의
    instances 스키마 중 case_features가 실제로 쓰는 필드만 채운다."""
    out = []
    for i, poly in enumerate(polygons):
        pts = np.asarray(poly, dtype=float).reshape(-1, 2)
        pts_px = pts * np.array([img_w, img_h], dtype=float)
        area = _poly_area(pts_px)
        d_px = float(2.0 * np.sqrt(area / np.pi)) if area > 0 else 0.0
        out.append({
            "id": i,
            "polygon_xy": pts_px.tolist(),
            "centroid_xy": pts_px.mean(axis=0).tolist(),
            "area_px": area,
            "equivalent_diameter_px": d_px,
            "equivalent_diameter_mm": (d_px * pixel_spacing_mm
                                       if pixel_spacing_mm else None),
        })
    return out


def build_case_database(
    df: pd.DataFrame,
    paths: cfg.Paths | None = None,
    pixel_spacing_mm: float | None = None,
    max_positive: int | None = None,
    max_normal: int | None = None,
    seed: int = 42,
    verbose: bool = True,
) -> tuple[list[CaseProfile], tuple[float, float]]:
    """
    반환: (CaseProfile 리스트, 크기임계값(lo,hi))

    max_positive/max_normal: None이면 전체 사용(24,000+ 장 -> 수 분 소요 가능).
    빠른 확인용으로는 각각 2000~3000 정도로 제한해서 먼저 돌려볼 것을 권장.
    """
    paths = paths or cfg.PATHS
    diameter_key = "equivalent_diameter_mm" if pixel_spacing_mm else "equivalent_diameter_px"

    pos = df[(df["annotation_case"] == "porosity") & (df["is_crowd"] == 0)
             & (df["image_exists"])].copy()
    neg = df[(df["annotation_case"] == "normal") & (df["is_tile"])
             & (df["image_exists"])].copy()

    if max_positive is not None and len(pos) > max_positive:
        pos = pos.sample(n=max_positive, random_state=seed)
    if max_normal is not None and len(neg) > max_normal:
        neg = neg.sample(n=max_normal, random_state=seed)

    # --- 1단계: 기공 폴리곤 파싱 + 등가직경 분포 수집 ---
    all_diameters: list[float] = []
    parsed: list[tuple] = []  # (row(namedtuple), instances)
    n_no_poly = 0

    it = tqdm(pos.itertuples(index=False), total=len(pos),
              desc="기공 라벨 파싱", disable=not verbose)
    for r in it:
        label_path = paths.raw_root / r.label_path
        polys, _ = L.extract_porosity_polygons(label_path, int(r.width), int(r.height))
        if not polys:
            n_no_poly += 1
            continue
        instances = _gt_polygons_to_instances(polys, int(r.width), int(r.height),
                                              pixel_spacing_mm)
        for ins in instances:
            d = ins[diameter_key]
            if d:
                all_diameters.append(d)
        parsed.append((r, instances))

    size_thresholds = compute_size_thresholds(all_diameters)
    if verbose:
        print(f"파싱 완료: 기공 {len(parsed)}건 (폴리곤 없어 제외 {n_no_poly}건)")
        print(f"크기 임계값(diameter 33/67백분위, {diameter_key} 기준): "
              f"소<{size_thresholds[0]:.3f}  중<{size_thresholds[1]:.3f}  대")

    # --- 2단계: CaseProfile 생성 ---
    profiles: list[CaseProfile] = []
    for r, instances in parsed:
        profiles.append(build_case_profile(
            instances, int(r.width), int(r.height), size_thresholds,
            diameter_key=diameter_key,
            verdict="abnormal",
            meta={"stem": Path(r.filename).stem, "label_id": int(r.label_id),
                  "image_path": r.image_path},
        ))

    it = tqdm(neg.itertuples(index=False), total=len(neg),
              desc="정상 사례 등록", disable=not verbose)
    for r in it:
        profiles.append(build_case_profile(
            [], int(r.width), int(r.height), size_thresholds,
            diameter_key=diameter_key,
            verdict="normal",
            meta={"stem": Path(r.filename).stem, "label_id": int(r.label_id),
                  "image_path": r.image_path},
        ))

    if verbose:
        n_abn = sum(1 for p in profiles if p.verdict == "abnormal")
        n_nor = sum(1 for p in profiles if p.verdict == "normal")
        print(f"case DB 구축 완료: 이상 {n_abn}건 + 정상 {n_nor}건 = 총 {len(profiles)}건")

    return profiles, size_thresholds

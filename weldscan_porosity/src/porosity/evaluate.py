"""
porosity.evaluate
=================
YOLO의 mAP는 '인스턴스 검출' 성능이다. 대시보드가 실제로 필요로 하는 건
**이미지 단위 정상/이상 판정** 이므로 별도로 평가·튜닝한다.

절차
  1) val 이미지 전체에 대해 낮은 conf로 추론 -> 인스턴스 후보 수집
  2) 이미지 점수 = max(instance confidence)  (없으면 0)
  3) val을 tune/test 두 반쪽으로 결정적 분할
     - tune 반쪽에서 임계값 선택 (미검출이 치명적이므로 recall 우선)
     - test 반쪽에서만 최종 수치 보고  (같은 데이터로 튜닝+보고 = 낙관 편향)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from . import config as cfg


# --- 1. 점수 수집 -------------------------------------------------------------
def score_images(model, manifest: pd.DataFrame, images_dir: str | Path,
                 infer: cfg.InferConfig | None = None,
                 batch: int = 8, verbose: bool = True) -> pd.DataFrame:
    """
    manifest(stem, label) 기준으로 이미지별 점수 산출.
    반환 컬럼: stem, label, source, score, n_inst, max_area_ratio
    """
    infer = infer or cfg.INFER
    images_dir = Path(images_dir)

    rows: list[dict] = []
    stems = manifest["stem"].tolist()
    meta = manifest.set_index("stem")[["label", "source"]].to_dict("index")

    for i in tqdm(range(0, len(stems), batch), desc="scoring", disable=not verbose):
        chunk = stems[i:i + batch]
        paths = [str(images_dir / f"{s}.jpg") for s in chunk]
        results = model.predict(
            paths, imgsz=infer.imgsz, conf=infer.conf, iou=infer.iou,
            max_det=infer.max_det, verbose=False, retina_masks=True,
        )
        for stem, res in zip(chunk, results):
            confs = (res.boxes.conf.cpu().numpy()
                     if res.boxes is not None and len(res.boxes) else np.array([]))
            score = float(confs.max()) if confs.size else 0.0

            area_ratio = 0.0
            if res.masks is not None and len(res.masks) > 0:
                m = res.masks.data.cpu().numpy()          # (n, H, W)
                denom = float(m.shape[1] * m.shape[2])
                if denom > 0:
                    area_ratio = float(m.reshape(m.shape[0], -1).sum(axis=1).max() / denom)

            rows.append({
                "stem": stem,
                "label": meta[stem]["label"],
                "source": meta[stem]["source"],
                "score": score,
                "n_inst": int(confs.size),
                "max_area_ratio": area_ratio,
                "conf_list": confs.tolist(),
            })
    return pd.DataFrame(rows)


# --- 2. tune/test 분할 --------------------------------------------------------
def split_tune_test(scores: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """stem 해시 기반 결정적 50:50 분할. 재실행해도 동일."""
    def side(stem: str) -> str:
        h = int(hashlib.md5(f"{seed}:{stem}".encode()).hexdigest()[:8], 16)
        return "tune" if h % 2 == 0 else "test"
    out = scores.copy()
    out["fold"] = out["stem"].map(side)
    return out


# --- 3. 임계값 스윕 -----------------------------------------------------------
def sweep(scores: pd.DataFrame, min_instances: int = 1,
          grid: np.ndarray | None = None, min_thr: float | None = None) -> pd.DataFrame:
    """
    임계값별 이미지 단위 지표.
    판정 규칙: conf >= thr 인 인스턴스가 min_instances개 이상 -> '이상'

    min_thr: 그리드 하한. None이면 scores에 실제로 존재하는 최소 confidence값을
        자동으로 사용한다. score_images()가 이미 conf=cfg.INFER.conf 이상만
        수집했으므로, 그보다 낮은 임계값은 결과가 전부 동일한(평평한) 구간이라
        의미가 없다 - 잘못하면 그 평평한 구간에서 동점 처리로 conf 미만의
        비현실적인 decision_conf가 뽑혀 PorosityDetector 로딩 시 거부당한다.
    """
    if min_thr is None:
        all_confs = [c for cl in scores["conf_list"] for c in cl]
        min_thr = min(all_confs) if all_confs else 0.05
    if grid is None:
        grid = np.round(np.arange(max(0.01, min_thr), 0.951, 0.01), 3)

    y = scores["label"].to_numpy().astype(int)
    conf_lists = scores["conf_list"].tolist()

    rows = []
    for thr in grid:
        pred = np.array(
            [1 if sum(c >= thr for c in cl) >= min_instances else 0 for cl in conf_lists],
            dtype=int,
        )
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        spec = tn / (tn + fp) if tn + fp else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        rows.append({
            "thr": float(thr), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": prec, "recall": rec, "specificity": spec,
            "fpr": 1 - spec, "f1": f1,
            "accuracy": (tp + tn) / len(y) if len(y) else 0.0,
            "balanced_acc": (rec + spec) / 2,
        })
    return pd.DataFrame(rows)


def pick_operating_point(sw: pd.DataFrame, min_recall: float = 0.97) -> dict:
    """
    미검출(FN)이 치명적인 도메인이므로 recall 하한을 먼저 만족시키고,
    그 안에서 FP가 가장 적은(=precision 최대) 임계값을 고른다.
    하한을 만족하는 점이 없으면 F1 최대점으로 폴백.
    """
    ok = sw[sw["recall"] >= min_recall]
    if len(ok):
        best = ok.sort_values(["precision", "thr"], ascending=[False, False]).iloc[0]
        rule = f"recall>={min_recall} 중 precision 최대"
    else:
        best = sw.sort_values(["f1", "thr"], ascending=[False, False]).iloc[0]
        rule = "recall 하한 미달 -> F1 최대점 폴백"
    return {"rule": rule, **{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                             for k, v in best.to_dict().items()}}


def evaluate_at(scores: pd.DataFrame, thr: float, min_instances: int = 1) -> dict:
    """특정 임계값에서의 단일 평가 결과."""
    row = sweep(scores, min_instances=min_instances,
                grid=np.array([thr])).iloc[0].to_dict()
    return {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
            for k, v in row.items()}


def pr_auc(scores: pd.DataFrame) -> dict:
    """임계값 비의존 지표 (ROC-AUC / Average Precision). sklearn 있으면 사용."""
    try:
        from sklearn.metrics import average_precision_score, roc_auc_score
    except ImportError:
        return {"note": "scikit-learn 미설치 - AUC 생략"}
    y = scores["label"].to_numpy()
    s = scores["score"].to_numpy()
    if len(set(y.tolist())) < 2:
        return {"note": "단일 클래스만 존재 - AUC 계산 불가"}
    return {"roc_auc": float(roc_auc_score(y, s)),
            "average_precision": float(average_precision_score(y, s))}


# --- 4. 저장 ------------------------------------------------------------------
def save_thresholds(out_path: str | Path, decision_conf: float,
                    min_instances: int, metrics: dict,
                    infer: cfg.InferConfig | None = None) -> Path:
    """대시보드가 읽어갈 임계값 파일. 이 파일이 판정의 계약이다."""
    infer = infer or cfg.INFER
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": cfg.SCHEMA_VERSION,
        "decision_conf": float(decision_conf),
        "min_instances": int(min_instances),
        "infer": {"imgsz": infer.imgsz, "conf": infer.conf,
                  "iou": infer.iou, "max_det": infer.max_det},
        "metrics_on_heldout": metrics,
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p

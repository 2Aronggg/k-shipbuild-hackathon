"""
porosity.detector
=================
**대시보드/백엔드와의 계약(contract) 레이어.**

다른 팀원(RAG, 룰엔진, API 오케스트레이션)은 이 클래스 하나만 알면 된다.
내부에서 모델을 교체하든 임계값을 바꾸든 아래 출력 스키마는 유지한다.

    from porosity.detector import PorosityDetector
    det = PorosityDetector.from_artifacts("artifacts/porosity_yolov8seg")
    out = det.predict("sample.jpg", pixel_spacing_mm=0.1)

출력 스키마 v1.0
{
  "schema_version": "1.0",
  "model": {"name": str, "weights": str, "imgsz": int,
            "conf": float, "iou": float, "decision_conf": float,
            "min_instances": int},
  "image": {"path": str|None, "width": int, "height": int,
            "pixel_spacing_mm": float|None},
  "verdict": "abnormal" | "normal",
  "defect_type": "porosity",
  "score": float,                 # 이미지 이상 점수 = max instance conf
  "n_instances": int,             # decision_conf 이상인 인스턴스 수
  "total_area_px": float,
  "total_area_ratio": float,
  "instances": [
     {"id": int, "conf": float,
      "bbox_xyxy": [x1,y1,x2,y2],
      "polygon_xy": [[x,y], ...],       # 원본 이미지 픽셀 좌표
      "area_px": float,
      "area_ratio": float,
      "equivalent_diameter_px": float,
      "equivalent_diameter_mm": float|None,
      "centroid_xy": [x,y]}
  ],
  "timing_ms": float,
  "warnings": [str]
}

룰엔진(KS B 0845)은 instances[].equivalent_diameter_mm 와 n_instances 를 입력으로
등급을 판정하면 된다. 이 모듈은 등급 판정을 하지 않는다(책임 분리).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from . import config as cfg

_ARTIFACT_WEIGHTS = "best.pt"
_ARTIFACT_THRESHOLDS = "thresholds.json"
_ARTIFACT_CONFIG = "model_config.json"


def _poly_area(poly: np.ndarray) -> float:
    """shoelace. poly: (n,2)"""
    if poly.shape[0] < 3:
        return 0.0
    x, y = poly[:, 0], poly[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)


class PorosityDetector:
    """YOLOv8-seg 기공 검출기. 스레드 안전하지 않음(요청당 1회 호출 가정)."""

    def __init__(
        self,
        weights: str | Path,
        *,
        imgsz: int | None = None,
        conf: float | None = None,
        iou: float | None = None,
        max_det: int | None = None,
        decision_conf: float | None = None,
        min_instances: int | None = None,
        device: str | None = None,
        model_name: str = "yolov8s-seg",
    ) -> None:
        from ultralytics import YOLO  # 지연 임포트: 이 모듈 import만으로 GPU를 잡지 않도록

        self.weights = str(Path(weights).resolve())
        self.model = YOLO(self.weights)
        self.model_name = model_name
        self.device = device

        self.imgsz = imgsz if imgsz is not None else cfg.INFER.imgsz
        self.conf = conf if conf is not None else cfg.INFER.conf
        self.iou = iou if iou is not None else cfg.INFER.iou
        self.max_det = max_det if max_det is not None else cfg.INFER.max_det
        self.decision_conf = (decision_conf if decision_conf is not None
                              else cfg.INFER.decision_conf)
        self.min_instances = (min_instances if min_instances is not None
                              else cfg.INFER.min_instances)

        if self.min_instances < 1:
            raise ValueError("min_instances는 1 이상이어야 한다 (0이면 항상 abnormal).")
        if self.conf > self.decision_conf:
            raise ValueError(
                f"conf({self.conf}) > decision_conf({self.decision_conf}): "
                "후보 수집 하한이 판정 임계값보다 높으면 판정이 왜곡된다."
            )

    # --- 로딩 -----------------------------------------------------------------
    @classmethod
    def from_artifacts(cls, artifacts_dir: str | Path,
                       device: str | None = None) -> "PorosityDetector":
        """artifacts 폴더(best.pt + thresholds.json)에서 결정적으로 로드."""
        d = Path(artifacts_dir)
        w = d / _ARTIFACT_WEIGHTS
        if not w.exists():
            raise FileNotFoundError(f"가중치 없음: {w}")

        kw: dict[str, Any] = {"device": device}
        th_path = d / _ARTIFACT_THRESHOLDS
        if th_path.exists():
            th = json.loads(th_path.read_text(encoding="utf-8"))
            if th.get("schema_version") != cfg.SCHEMA_VERSION:
                raise ValueError(
                    f"thresholds.json schema_version={th.get('schema_version')} != "
                    f"{cfg.SCHEMA_VERSION}. 호환성 확인 필요."
                )
            kw["decision_conf"] = th["decision_conf"]
            kw["min_instances"] = th["min_instances"]
            inf = th.get("infer", {})
            kw.update({k: inf[k] for k in ("imgsz", "conf", "iou", "max_det") if k in inf})

        cf_path = d / _ARTIFACT_CONFIG
        if cf_path.exists():
            cf = json.loads(cf_path.read_text(encoding="utf-8"))
            kw["model_name"] = cf.get("model_name", "yolov8s-seg")

        return cls(w, **kw)

    # --- 추론 -----------------------------------------------------------------
    def predict(self, image: str | Path | np.ndarray,
                pixel_spacing_mm: float | None = None) -> dict:
        """단일 이미지 판정. 반환은 위 문서의 v1.0 스키마."""
        t0 = time.perf_counter()
        warnings: list[str] = []

        src = str(image) if isinstance(image, (str, Path)) else image
        res = self.model.predict(
            src, imgsz=self.imgsz, conf=self.conf, iou=self.iou,
            max_det=self.max_det, device=self.device,
            retina_masks=True, verbose=False,
        )[0]

        H, W = int(res.orig_shape[0]), int(res.orig_shape[1])
        if (W, H) != (cfg.TILE_W, cfg.TILE_H):
            warnings.append(
                f"입력 크기 {W}x{H}가 학습 타일 {cfg.TILE_W}x{cfg.TILE_H}과 다름. "
                "원본 RT 파노라마라면 타일로 분할해 tile_predict()를 쓸 것."
            )

        instances: list[dict] = []
        if res.boxes is not None and len(res.boxes) > 0:
            confs = res.boxes.conf.cpu().numpy()
            boxes = res.boxes.xyxy.cpu().numpy()
            polys = (res.masks.xy if res.masks is not None
                     else [None] * len(confs))
            if res.masks is None:
                warnings.append("마스크 없음 - seg 모델이 맞는지 확인")

            for i, (c, b) in enumerate(zip(confs, boxes)):
                if float(c) < self.decision_conf:
                    continue
                poly = np.asarray(polys[i], dtype=float) if polys[i] is not None else None
                if poly is not None and poly.shape[0] >= 3:
                    area = _poly_area(poly)
                    cxy = poly.mean(axis=0).tolist()
                    poly_list = np.round(poly, 2).tolist()
                else:  # 마스크 실패 시 bbox로 폴백
                    area = float(max(0.0, (b[2] - b[0]) * (b[3] - b[1])))
                    cxy = [float((b[0] + b[2]) / 2), float((b[1] + b[3]) / 2)]
                    poly_list = [[float(b[0]), float(b[1])], [float(b[2]), float(b[1])],
                                 [float(b[2]), float(b[3])], [float(b[0]), float(b[3])]]

                d_px = float(2.0 * np.sqrt(area / np.pi)) if area > 0 else 0.0
                instances.append({
                    "id": len(instances),
                    "conf": float(c),
                    "bbox_xyxy": [round(float(v), 2) for v in b],
                    "polygon_xy": poly_list,
                    "area_px": round(area, 2),
                    "area_ratio": round(area / (W * H), 8) if W * H else 0.0,
                    "equivalent_diameter_px": round(d_px, 3),
                    "equivalent_diameter_mm": (round(d_px * pixel_spacing_mm, 4)
                                               if pixel_spacing_mm else None),
                    "centroid_xy": [round(float(v), 2) for v in cxy],
                })

        n = len(instances)
        # score는 decision_conf 미만 후보까지 포함한 raw max conf.
        # 위험도 산출/임계값 재조정에 쓰려면 절단되지 않은 값이어야 한다.
        score = (float(res.boxes.conf.cpu().numpy().max())
                 if res.boxes is not None and len(res.boxes) > 0 else 0.0)

        total_area = float(sum(ins["area_px"] for ins in instances))
        if pixel_spacing_mm is None:
            warnings.append("pixel_spacing_mm 미제공 - mm 환산 불가(룰엔진 등급판정 제한)")

        return {
            "schema_version": cfg.SCHEMA_VERSION,
            "model": {
                "name": self.model_name, "weights": self.weights,
                "imgsz": self.imgsz, "conf": self.conf, "iou": self.iou,
                "decision_conf": self.decision_conf,
                "min_instances": self.min_instances,
            },
            "image": {
                "path": str(image) if isinstance(image, (str, Path)) else None,
                "width": W, "height": H, "pixel_spacing_mm": pixel_spacing_mm,
            },
            "verdict": "abnormal" if n >= self.min_instances else "normal",
            "defect_type": "porosity",
            "score": round(float(score), 6),
            "n_instances": n,
            "total_area_px": round(total_area, 2),
            "total_area_ratio": round(total_area / (W * H), 8) if W * H else 0.0,
            "instances": instances,
            "timing_ms": round((time.perf_counter() - t0) * 1000, 2),
            "warnings": warnings,
        }

    # --- 파노라마 대응 --------------------------------------------------------
    def tile_predict(self, image: str | Path, overlap: float = 0.2,
                     pixel_spacing_mm: float | None = None) -> dict:
        """
        원본 RT 파노라마용: 1280x720 타일로 슬라이딩 윈도우 추론 후 좌표를 합친다.
        (학습은 타일 단위이므로 파노라마를 통째로 넣으면 스케일이 깨진다)
        경계 중복은 단순 좌표 병합만 수행 - 정밀 중복 제거가 필요하면 후처리 추가.
        """
        from PIL import Image as PILImage
        PILImage.MAX_IMAGE_PIXELS = None

        t0 = time.perf_counter()
        with PILImage.open(image) as im:
            im = im.convert("RGB")
            W, H = im.size
            sx = max(1, int(cfg.TILE_W * (1 - overlap)))
            sy = max(1, int(cfg.TILE_H * (1 - overlap)))
            xs = list(range(0, max(1, W - cfg.TILE_W + 1), sx)) or [0]
            ys = list(range(0, max(1, H - cfg.TILE_H + 1), sy)) or [0]
            if xs[-1] != max(0, W - cfg.TILE_W):
                xs.append(max(0, W - cfg.TILE_W))
            if ys[-1] != max(0, H - cfg.TILE_H):
                ys.append(max(0, H - cfg.TILE_H))

            if W < cfg.TILE_W or H < cfg.TILE_H:
                # 타일보다 작은 이미지는 가장자리를 복제 패딩해 스케일을 보존
                canvas = PILImage.new("RGB", (max(W, cfg.TILE_W), max(H, cfg.TILE_H)))
                canvas.paste(im, (0, 0))
                im = canvas
                W, H = im.size

            merged: list[dict] = []
            for y0 in ys:
                for x0 in xs:
                    tile = im.crop((x0, y0, x0 + cfg.TILE_W, y0 + cfg.TILE_H))
                    # ultralytics는 BGR numpy를 기대. 음수 stride 뷰는 torch에서 실패하므로 연속 배열로.
                    arr = np.ascontiguousarray(np.array(tile)[:, :, ::-1])
                    out = self.predict(arr, pixel_spacing_mm=pixel_spacing_mm)
                    for ins in out["instances"]:
                        ins["bbox_xyxy"] = [ins["bbox_xyxy"][0] + x0, ins["bbox_xyxy"][1] + y0,
                                            ins["bbox_xyxy"][2] + x0, ins["bbox_xyxy"][3] + y0]
                        ins["polygon_xy"] = [[px + x0, py + y0] for px, py in ins["polygon_xy"]]
                        ins["centroid_xy"] = [ins["centroid_xy"][0] + x0,
                                              ins["centroid_xy"][1] + y0]
                        ins["tile_origin"] = [x0, y0]
                        merged.append(ins)

        for i, ins in enumerate(merged):
            ins["id"] = i
            ins["area_ratio"] = round(ins["area_px"] / (W * H), 10) if W * H else 0.0

        total_area = float(sum(ins["area_px"] for ins in merged))
        return {
            "schema_version": cfg.SCHEMA_VERSION,
            "model": {"name": self.model_name, "weights": self.weights,
                      "imgsz": self.imgsz, "conf": self.conf, "iou": self.iou,
                      "decision_conf": self.decision_conf,
                      "min_instances": self.min_instances},
            "image": {"path": str(image), "width": W, "height": H,
                      "pixel_spacing_mm": pixel_spacing_mm},
            "verdict": "abnormal" if len(merged) >= self.min_instances else "normal",
            "defect_type": "porosity",
            "score": round(max((i["conf"] for i in merged), default=0.0), 6),
            "n_instances": len(merged),
            "total_area_px": round(total_area, 2),
            "total_area_ratio": round(total_area / (W * H), 10) if W * H else 0.0,
            "instances": merged,
            "timing_ms": round((time.perf_counter() - t0) * 1000, 2),
            "warnings": ["tiled inference: 타일 경계 중복 인스턴스 미제거"],
        }

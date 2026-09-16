"""
porosity.config
===============
모든 경로/하이퍼파라미터의 단일 진실 공급원(single source of truth).

git 병합 시 다른 모듈은 건드리지 말고 이 파일(혹은 환경변수)만 바꾸면 되도록 설계.
환경변수 WELDSCAN_ROOT / WELDSCAN_WORK 로 오버라이드 가능.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

SCHEMA_VERSION = "1.0"

# 클래스 정의 - 단일 클래스 세그멘테이션
CLASS_NAMES: list[str] = ["porosity"]
CLASS_ID_POROSITY = 0

# 라벨 JSON 안에서 '기공'을 가리킬 수 있는 표기들 (소문자/공백제거 후 비교)
POROSITY_ALIASES: set[str] = {
    "기공", "porosity", "pore", "blowhole", "gas_pore", "gasporosity",
    "porosities", "기공결함",
}
# 배경으로 취급해야 하는 표기들 (정상 이미지의 어노테이션)
NORMAL_ALIASES: set[str] = {"정상", "normal", "ok", "sound", "no_defect", "nodefect"}

# 타깃 타일 크기 (기공 크롭과 동일하게 맞춘다 - 누수 제거의 핵심)
TILE_W = 1280
TILE_H = 720


def _env_path(key: str, default: str) -> Path:
    return Path(os.environ.get(key, default)).expanduser()


@dataclass
class Paths:
    """원본 데이터셋 루트와 작업 디렉터리."""
    # 원본: metadata.csv / images/ / labels/ 가 들어있는 폴더
    raw_root: Path = field(
        default_factory=lambda: _env_path("WELDSCAN_ROOT", r"C:\Users\user\weldscan\weld_db")
    )
    # 산출물: YOLO 데이터셋, 학습 결과, 배포 아티팩트
    work_root: Path = field(
        default_factory=lambda: _env_path("WELDSCAN_WORK", r"C:\Users\user\weldscan\work")
    )

    @property
    def metadata_csv(self) -> Path:
        return self.raw_root / "metadata.csv"

    @property
    def yolo_root(self) -> Path:
        """YOLO 규격 데이터셋 루트 (images/{train,val}, labels/{train,val})."""
        return self.work_root / "yolo_porosity"

    def subset_root(self, variant: str) -> Path:
        """서브셋 데이터셋 루트. variant별로 폴더를 분리해 서로 오염되지 않게 한다.
        예: subset_root("quick") -> 스모크 테스트용 소규모 서브셋
            subset_root("demo")  -> 데모/발표용 중간 규모 서브셋
        """
        return self.work_root / f"yolo_porosity_{variant}"

    def subset_dataset_yaml(self, variant: str) -> Path:
        return self.subset_root(variant) / "dataset.yaml"

    @property
    def quick_root(self) -> Path:
        return self.subset_root("quick")

    @property
    def quick_dataset_yaml(self) -> Path:
        return self.subset_dataset_yaml("quick")

    @property
    def dataset_yaml(self) -> Path:
        return self.yolo_root / "dataset.yaml"

    @property
    def runs_dir(self) -> Path:
        return self.work_root / "runs"

    @property
    def artifacts_dir(self) -> Path:
        """대시보드가 로드할 배포 아티팩트(가중치/임계값/설정)."""
        return self.work_root / "artifacts" / "porosity_yolov8seg"

    def ensure(self) -> None:
        for p in (self.work_root, self.yolo_root, self.runs_dir, self.artifacts_dir):
            p.mkdir(parents=True, exist_ok=True)


@dataclass
class DataConfig:
    """데이터셋 구성 정책."""
    # 양성: annotation_case가 정확히 'porosity'인 이미지만 (다중결함 제외)
    positive_case: str = "porosity"
    # 음성 비율 - 양성 대비 몇 배의 배경 이미지를 넣을지
    neg_ratio: float = 1.0
    # 파노라마에서 뽑을 크롭의 최대 개수(장당)
    max_crops_per_pano: int = 2
    # 빠른 반복 실험용 상한 (None이면 전량)
    max_pos_train: int | None = None
    max_pos_val: int | None = None
    # 폴리곤 점 개수 상한 (과도하게 촘촘한 폴리곤 방어)
    max_polygon_points: int = 1000
    # 정규화 좌표 기준 최소 폴리곤 면적 (이보다 작으면 폐기)
    min_polygon_area_norm: float = 1e-7
    # 이미지 복사 방식: "symlink" | "copy" | "hardlink"
    #   Windows에서 symlink는 관리자 권한/개발자 모드가 필요 -> 기본 hardlink
    link_mode: str = "hardlink"
    seed: int = 42


@dataclass
class TrainConfig:
    """Ultralytics YOLOv8-seg 학습 설정."""
    model: str = "yolov8s-seg.pt"
    imgsz: int = 1280          # 1280x720 네이티브. 기공이 작아서 축소하면 손해가 큼
    epochs: int = 60
    batch: int = 8             # VRAM 부족하면 4로, 넉넉하면 16
    device: str = "0"          # CPU면 "cpu"
    workers: int = 4           # Windows는 0~4 권장
    optimizer: str = "auto"
    patience: int = 15
    cos_lr: bool = True
    amp: bool = True
    seed: int = 42
    # --- 증강: RT 필름은 사실상 그레이스케일 -> 색상 증강 최소화 ---
    hsv_h: float = 0.0
    hsv_s: float = 0.0
    hsv_v: float = 0.30        # 필름 농도/노출 편차 모사
    degrees: float = 3.0       # 필름은 수평 정렬됨 -> 큰 회전 금지
    translate: float = 0.10
    scale: float = 0.30
    shear: float = 0.0
    perspective: float = 0.0
    flipud: float = 0.5
    fliplr: float = 0.5
    mosaic: float = 1.0
    close_mosaic: int = 10
    mixup: float = 0.0
    copy_paste: float = 0.0    # seg에서 유용하나 단일클래스+배경혼합 시 라벨 오염 위험
    overlap_mask: bool = True
    mask_ratio: int = 4
    project_name: str = "porosity_seg"


@dataclass
class InferConfig:
    """추론/판정 기본값. 04 노트북의 임계값 튜닝 결과로 덮어쓴다."""
    imgsz: int = 1280
    conf: float = 0.15         # 인스턴스 후보 수집용 하한 (낮게)
    iou: float = 0.50          # NMS IoU
    max_det: int = 300
    # 이미지 단위 '이상' 판정 임계값 (04에서 튜닝 후 thresholds.json으로 저장)
    decision_conf: float = 0.35
    min_instances: int = 1


PATHS = Paths()
DATA = DataConfig()
TRAIN = TrainConfig()
INFER = InferConfig()


def snapshot() -> dict:
    """현재 설정을 JSON 직렬화 가능한 dict로 (실험 재현성 기록용)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "class_names": CLASS_NAMES,
        "tile": [TILE_W, TILE_H],
        "paths": {k: str(v) for k, v in asdict(PATHS).items()},
        "data": asdict(DATA),
        "train": asdict(TRAIN),
        "infer": asdict(INFER),
    }

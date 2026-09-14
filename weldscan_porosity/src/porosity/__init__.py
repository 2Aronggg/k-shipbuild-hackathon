"""weldscan - 기공(porosity) YOLOv8-seg 결함 탐지 모듈."""
from .config import (
    CLASS_NAMES, SCHEMA_VERSION, TILE_H, TILE_W,
    DATA, INFER, PATHS, TRAIN, snapshot,
)

__all__ = [
    "CLASS_NAMES", "SCHEMA_VERSION", "TILE_W", "TILE_H",
    "PATHS", "DATA", "TRAIN", "INFER", "snapshot",
    "PorosityDetector",
    "case_features", "similarity", "case_db_build",
]
__version__ = "1.0.0"


def __getattr__(name):
    # ultralytics/torch를 실제로 쓸 때만 로드 (import porosity 가 가벼워지도록)
    if name == "PorosityDetector":
        from .detector import PorosityDetector
        return PorosityDetector
    if name in ("case_features", "similarity", "case_db_build"):
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(name)
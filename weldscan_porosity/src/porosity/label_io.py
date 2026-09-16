"""
porosity.label_io
=================
라벨 JSON -> YOLO-seg 폴리곤 변환.

AI Hub 라벨 스키마가 확정되지 않았으므로 **재귀 탐색 기반 자동 검출**로 구현한다.
지원 형태:
  - COCO 계열   : {"annotations":[{"segmentation":[[x,y,...]], "bbox":[x,y,w,h], ...}]}
  - LabelMe 계열: {"shapes":[{"label":..., "points":[[x,y],...], "shape_type":"polygon|rectangle|circle"}]}
  - AI Hub 커스텀: {"objects"/"label_info"/... :[{"polygon"/"points"/"coordinates": ...}]}
  - 원(circle)  : {"cx","cy","r"} / {"center":[x,y], "radius":r}

좌표 포맷:
  - flat  [x1,y1,x2,y2,...]
  - nested[[x1,y1],[x2,y2],...]
  - dict  [{"x":..,"y":..}, ...]

반드시 `inspect_schema()` 로 실제 구조를 눈으로 확인한 뒤 변환할 것.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

from .config import (
    CLASS_ID_POROSITY,
    NORMAL_ALIASES,
    POROSITY_ALIASES,
)

# --- 키 사전 ------------------------------------------------------------------
POLY_KEYS = ("segmentation", "polygon", "polygons", "points", "coordinates", "coordinate",
             "coords", "poly", "seg", "contour", "vertices")
BBOX_KEYS = ("bbox", "box", "bndbox", "rect", "rectangle", "boundingbox", "bounding_box")
LABEL_KEYS = ("label", "class", "class_name", "category", "category_name", "categories",
              "name", "defect", "defect_type", "type", "annotation_case", "tag", "title",
              "case")

# 라벨 키 우선순위. dict의 등장 순서가 아니라 이 순서로 찾는다.
# AI Hub 커스텀 스키마 실측: {"tool":"polygon","coordinate":...,"class":"defect","case":"porosity"}
# 'class'는 모든 결함에서 공통값 "defect"인 무의미한 placeholder이고
# 실제 결함 종류는 'case'에 들어있다. dict 순서대로 찾으면 'class'가 먼저 걸려
# 조용히 오분류(스킵)된다 - 그래서 도메인 구체적인 키를 최우선으로 둔다.
LABEL_PRIORITY = (
    "case", "defect_type", "defect", "annotation_case",
    "category_name", "class_name", "label", "category",
    "name", "tag", "title", "class", "type",
)
CIRCLE_CENTER_KEYS = ("center", "centre")
CIRCLE_R_KEYS = ("r", "radius", "rad")


# --- 스키마 관찰 --------------------------------------------------------------
def describe(obj: Any, depth: int = 0, max_depth: int = 4, max_items: int = 3) -> str:
    """JSON 구조를 타입 트리로 요약 출력 (값이 길면 잘라냄)."""
    pad = "  " * depth
    if depth > max_depth:
        return f"{pad}..."
    if isinstance(obj, dict):
        lines = [f"{pad}dict({len(obj)} keys)"]
        for k, v in list(obj.items())[:12]:
            if isinstance(v, (dict, list, tuple)):
                lines.append(f"{pad}  '{k}':")
                lines.append(describe(v, depth + 2, max_depth, max_items))
            else:  # 스칼라는 한 줄로 붙여서 depth를 낭비하지 않는다
                s = repr(v)
                if len(s) > 70:
                    s = s[:70] + "..."
                lines.append(f"{pad}  '{k}': {type(v).__name__} = {s}")
        if len(obj) > 12:
            lines.append(f"{pad}  ... (+{len(obj) - 12} keys)")
        return "\n".join(lines)
    if isinstance(obj, (list, tuple)):
        lines = [f"{pad}list(len={len(obj)})"]
        for v in list(obj)[:max_items]:
            lines.append(describe(v, depth + 1, max_depth, max_items))
        if len(obj) > max_items:
            lines.append(f"{pad}  ... (+{len(obj) - max_items} items)")
        return "\n".join(lines)
    s = repr(obj)
    if len(s) > 90:
        s = s[:90] + "..."
    return f"{pad}{type(obj).__name__}: {s}"


def inspect_schema(json_path: str | Path, max_depth: int = 4) -> dict:
    """라벨 JSON 하나를 열어 구조를 출력하고 원본 dict를 반환."""
    p = Path(json_path)
    with open(p, "r", encoding="utf-8-sig") as f:
        obj = json.load(f)
    print(f"=== {p.name} ===")
    print(describe(obj, max_depth=max_depth))
    return obj


def collect_keys(obj: Any, out: set[str] | None = None) -> set[str]:
    """JSON 트리 전체에서 등장하는 모든 키 이름 수집 (스키마 정찰용)."""
    if out is None:
        out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k)
            collect_keys(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            collect_keys(v, out)
    return out


# --- 좌표 정규화 --------------------------------------------------------------
def _to_xy_pairs(raw: Any) -> list[tuple[float, float]] | None:
    """여러 좌표 표현을 [(x,y), ...] 로 통일. 실패 시 None."""
    if raw is None:
        return None

    # dict 형태의 병렬 배열: {"x":[...], "y":[...]}
    if isinstance(raw, dict):
        low = {k.lower(): v for k, v in raw.items()}
        if ("x" in low and "y" in low
                and isinstance(low["x"], (list, tuple))
                and isinstance(low["y"], (list, tuple))
                and len(low["x"]) == len(low["y"]) >= 3):
            try:
                xs = [float(v) for v in low["x"]]
                ys = [float(v) for v in low["y"]]
            except (TypeError, ValueError):
                return None
            return list(zip(xs, ys))
        return None

    # COCO segmentation: [[x,y,x,y,...]] 형태 -> 첫 번째 링만 사용
    if (isinstance(raw, (list, tuple)) and len(raw) > 0
            and isinstance(raw[0], (list, tuple))
            and len(raw[0]) >= 6
            and all(isinstance(v, (int, float)) for v in raw[0])):
        raw = raw[0]

    if not isinstance(raw, (list, tuple)) or len(raw) == 0:
        return None

    first = raw[0]

    # [[x,y], [x,y], ...]
    if isinstance(first, (list, tuple)):
        pts = []
        for it in raw:
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                try:
                    pts.append((float(it[0]), float(it[1])))
                except (TypeError, ValueError):
                    return None
            else:
                return None
        return pts if len(pts) >= 3 else None

    # [{"x":..,"y":..}, ...]
    if isinstance(first, dict):
        pts = []
        for it in raw:
            if not isinstance(it, dict):
                return None
            xk = next((k for k in it if k.lower() in ("x", "cx", "col")), None)
            yk = next((k for k in it if k.lower() in ("y", "cy", "row")), None)
            if xk is None or yk is None:
                return None
            try:
                pts.append((float(it[xk]), float(it[yk])))
            except (TypeError, ValueError):
                return None
        return pts if len(pts) >= 3 else None

    # [x1,y1,x2,y2,...]
    if isinstance(first, (int, float)):
        if len(raw) < 6 or len(raw) % 2 != 0:
            return None
        try:
            vals = [float(v) for v in raw]
        except (TypeError, ValueError):
            return None
        return list(zip(vals[0::2], vals[1::2]))

    return None


def _bbox_to_pairs(raw: Any) -> list[tuple[float, float]] | None:
    """bbox -> 사각 폴리곤 4점. [x,y,w,h] 와 [x1,y1,x2,y2] 및 dict 형태 지원."""
    if isinstance(raw, dict):
        low = {k.lower(): v for k, v in raw.items()}
        if all(k in low for k in ("xmin", "ymin", "xmax", "ymax")):
            x1, y1, x2, y2 = (float(low["xmin"]), float(low["ymin"]),
                              float(low["xmax"]), float(low["ymax"]))
        elif all(k in low for k in ("x", "y", "w", "h")):
            x1, y1 = float(low["x"]), float(low["y"])
            x2, y2 = x1 + float(low["w"]), y1 + float(low["h"])
        elif all(k in low for k in ("left", "top", "right", "bottom")):
            x1, y1, x2, y2 = (float(low["left"]), float(low["top"]),
                              float(low["right"]), float(low["bottom"]))
        else:
            return None
    elif isinstance(raw, (list, tuple)) and len(raw) == 4:
        try:
            a, b, c, d = (float(v) for v in raw)
        except (TypeError, ValueError):
            return None
        # w,h 형태인지 x2,y2 형태인지 추정: c,d가 a,b보다 크면 모호하므로
        # COCO 관례([x,y,w,h])를 우선하되 w/h가 음수면 x2y2로 해석
        if c <= 0 or d <= 0:
            x1, y1, x2, y2 = a, b, c, d
        else:
            x1, y1, x2, y2 = a, b, a + c, b + d
    else:
        return None

    if x2 <= x1 or y2 <= y1:
        return None
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def _circle_to_pairs(node: dict, n: int = 24) -> list[tuple[float, float]] | None:
    """원 정의 -> 다각형 근사. 기공은 원형이라 circle 어노테이션 가능성이 있음."""
    low = {k.lower(): v for k, v in node.items()}
    cx = cy = r = None

    for ck in CIRCLE_CENTER_KEYS:
        if ck in low and isinstance(low[ck], (list, tuple)) and len(low[ck]) >= 2:
            cx, cy = float(low[ck][0]), float(low[ck][1])
            break
    if cx is None and "cx" in low and "cy" in low:
        cx, cy = float(low["cx"]), float(low["cy"])

    for rk in CIRCLE_R_KEYS:
        if rk in low:
            try:
                r = float(low[rk])
            except (TypeError, ValueError):
                r = None
            break

    if cx is None or cy is None or r is None or r <= 0:
        return None
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# --- 라벨명 판정 --------------------------------------------------------------
def _norm_label(v: Any) -> str:
    return str(v).strip().lower().replace(" ", "").replace("-", "_")


def _find_label(node: dict) -> str | None:
    low = {k.lower(): (k, v) for k, v in node.items()}
    for pk in LABEL_PRIORITY:
        if pk in low:
            _, v = low[pk]
            if isinstance(v, (str, int)):
                return _norm_label(v)
            if isinstance(v, dict):
                for kk in v:
                    if kk.lower() in ("name", "label", "class", "kor", "eng"):
                        return _norm_label(v[kk])
    return None


def _label_matches(lab: str | None, aliases: set[str], *, default: bool) -> bool:
    """라벨이 없으면 default(이미지 단위 class를 신뢰) 반환."""
    if lab is None:
        return default
    norm_aliases = {_norm_label(a) for a in aliases}
    return lab in norm_aliases


# --- 핵심: 어노테이션 노드 재귀 수집 -------------------------------------------
def iter_annotation_nodes(obj: Any) -> Iterable[dict]:
    """폴리곤/bbox/원 키를 가진 dict 노드를 트리 전체에서 수집."""
    if isinstance(obj, dict):
        keys_low = {k.lower() for k in obj}
        has_geom = (
            bool(keys_low & set(POLY_KEYS))
            or bool(keys_low & set(BBOX_KEYS))
            or ({"cx", "cy"} <= keys_low and bool(keys_low & set(CIRCLE_R_KEYS)))
            or (bool(keys_low & set(CIRCLE_CENTER_KEYS)) and bool(keys_low & set(CIRCLE_R_KEYS)))
        )
        if has_geom:
            yield obj
        for v in obj.values():
            yield from iter_annotation_nodes(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from iter_annotation_nodes(v)


def _node_to_polygon(node: dict) -> list[tuple[float, float]] | None:
    """우선순위: 폴리곤 > 원 > bbox."""
    low = {k.lower(): v for k, v in node.items()}

    shape_type = _norm_label(low.get("shape_type", "")) if "shape_type" in low else ""

    if shape_type == "circle":
        # LabelMe circle = [중심점, 원주상의 점] 2개 -> _to_xy_pairs(>=3점 요구)로는 못 잡음
        raw = low.get("points")
        if (isinstance(raw, (list, tuple)) and len(raw) >= 2
                and all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in raw[:2])):
            try:
                cx, cy = float(raw[0][0]), float(raw[0][1])
                ex, ey = float(raw[1][0]), float(raw[1][1])
            except (TypeError, ValueError):
                cx = cy = ex = ey = 0.0
            r = math.hypot(ex - cx, ey - cy)
            if r > 0:
                return [(cx + r * math.cos(2 * math.pi * i / 24),
                         cy + r * math.sin(2 * math.pi * i / 24)) for i in range(24)]

    if shape_type == "rectangle":
        pts = _to_xy_pairs(low.get("points"))
        if pts is None:
            raw = low.get("points")
            if isinstance(raw, (list, tuple)) and len(raw) == 2:
                (x1, y1), (x2, y2) = raw[0], raw[1]
                return [(float(x1), float(y1)), (float(x2), float(y1)),
                        (float(x2), float(y2)), (float(x1), float(y2))]
        elif pts is not None:
            return pts

    for k in POLY_KEYS:
        if k in low:
            pts = _to_xy_pairs(low[k])
            if pts:
                return pts
            # LabelMe rectangle: points가 2개뿐인 경우
            raw = low[k]
            if isinstance(raw, (list, tuple)) and len(raw) == 2 \
                    and all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in raw):
                (x1, y1), (x2, y2) = raw[0], raw[1]
                x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
                if x2 != x1 and y2 != y1:
                    return [(min(x1, x2), min(y1, y2)), (max(x1, x2), min(y1, y2)),
                            (max(x1, x2), max(y1, y2)), (min(x1, x2), max(y1, y2))]

    circ = _circle_to_pairs(node)
    if circ:
        return circ

    for k in BBOX_KEYS:
        if k in low:
            bb = _bbox_to_pairs(low[k])
            if bb:
                return bb

    return None


# --- 폴리곤 후처리 ------------------------------------------------------------
def _shoelace_area(pts: list[tuple[float, float]]) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def normalize_polygon(
    pts: list[tuple[float, float]],
    img_w: int,
    img_h: int,
    *,
    max_points: int = 1000,
    min_area_norm: float = 1e-7,
) -> list[float] | None:
    """픽셀 좌표 -> [0,1] 정규화 flat 리스트. 부적합하면 None."""
    if not pts or len(pts) < 3 or img_w <= 0 or img_h <= 0:
        return None

    # 이미 정규화된 좌표가 들어온 경우 감지 (모든 값이 <=1.5)
    mx = max(max(abs(x) for x, _ in pts), max(abs(y) for _, y in pts))
    if mx <= 1.5:
        norm = [(min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0)) for x, y in pts]
    else:
        norm = [(min(max(x / img_w, 0.0), 1.0), min(max(y / img_h, 0.0), 1.0))
                for x, y in pts]

    # 연속 중복점 제거
    dedup: list[tuple[float, float]] = []
    for p in norm:
        if not dedup or (abs(p[0] - dedup[-1][0]) > 1e-9 or abs(p[1] - dedup[-1][1]) > 1e-9):
            dedup.append(p)
    if len(dedup) > 1 and abs(dedup[0][0] - dedup[-1][0]) < 1e-9 \
            and abs(dedup[0][1] - dedup[-1][1]) < 1e-9:
        dedup.pop()
    if len(dedup) < 3:
        return None

    # 과도한 점 개수는 균등 서브샘플링
    if len(dedup) > max_points:
        step = len(dedup) / max_points
        dedup = [dedup[int(i * step)] for i in range(max_points)]

    if _shoelace_area(dedup) < min_area_norm:
        return None

    flat: list[float] = []
    for x, y in dedup:
        flat.extend([round(x, 6), round(y, 6)])
    return flat


# --- 공개 API -----------------------------------------------------------------
def extract_porosity_polygons(
    json_path: str | Path,
    img_w: int,
    img_h: int,
    *,
    assume_all_porosity: bool = True,
    max_points: int = 1000,
    min_area_norm: float = 1e-7,
) -> tuple[list[list[float]], dict]:
    """
    라벨 JSON에서 기공 폴리곤만 뽑아 정규화 flat 리스트들로 반환.

    assume_all_purosity=True  : 라벨명이 없는 노드는 기공으로 간주
        (호출부에서 annotation_case == 'porosity' 인 순수 기공 이미지만 넘기므로 안전)
    반환: (polygons, stats)
    """
    stats = {"nodes": 0, "matched": 0, "skipped_label": 0,
             "skipped_geom": 0, "skipped_invalid": 0}
    p = Path(json_path)
    try:
        with open(p, "r", encoding="utf-8-sig") as f:
            obj = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        stats["error"] = f"{type(e).__name__}: {e}"
        return [], stats

    polys: list[list[float]] = []
    for node in iter_annotation_nodes(obj):
        stats["nodes"] += 1
        lab = _find_label(node)

        # 정상 어노테이션은 무조건 배제
        if _label_matches(lab, NORMAL_ALIASES, default=False):
            stats["skipped_label"] += 1
            continue
        if not _label_matches(lab, POROSITY_ALIASES, default=assume_all_porosity):
            stats["skipped_label"] += 1
            continue

        pts = _node_to_polygon(node)
        if pts is None:
            stats["skipped_geom"] += 1
            continue

        flat = normalize_polygon(pts, img_w, img_h,
                                 max_points=max_points, min_area_norm=min_area_norm)
        if flat is None:
            stats["skipped_invalid"] += 1
            continue

        polys.append(flat)
        stats["matched"] += 1

    return polys, stats


def write_yolo_seg_label(txt_path: str | Path, polygons: list[list[float]],
                         class_id: int = CLASS_ID_POROSITY) -> None:
    """YOLOv8-seg 라벨 파일 기록. polygons가 비면 빈 파일(=background)."""
    txt_path = Path(txt_path)
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{class_id} " + " ".join(f"{v:.6f}" for v in poly)
        for poly in polygons
    ]
    txt_path.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")

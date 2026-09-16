"""
porosity.data_prep
==================
metadata.csv -> YOLOv8-seg 데이터셋 빌드.

핵심 설계(누수 제거):
  기공 이미지는 전량 1280x720 크롭인데 정상은 91%가 원본 파노라마(평균 3165x917)다.
  그대로 학습하면 모델이 '이미지 크기/종횡비 = 클래스'를 외운다.
  따라서 음성 샘플을 다음 두 소스에서만 취한다.
    (a) 이미 1280x720인 정상 이미지 (train 1,850 / val 240)
    (b) 정상 파노라마(>=1280x720)에서 **네이티브 스케일 랜덤 크롭** 1280x720
  -> 양성/음성이 픽셀 통계상 구분 불가능해진다.

정상 이미지의 라벨 JSON에는 '정상' 어노테이션이 1개 들어있으나,
YOLO에서는 **빈 .txt = background** 로 기록한다. (class 0으로 넣으면 학습이 붕괴)
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
from pathlib import Path

import pandas as pd
from PIL import Image
from tqdm.auto import tqdm

from . import config as cfg
from .label_io import extract_porosity_polygons, write_yolo_seg_label

Image.MAX_IMAGE_PIXELS = None  # 대형 파노라마 DecompressionBomb 경고 방지


# --- 1. 메타데이터 ------------------------------------------------------------
REQUIRED_COLS = [
    "label_id", "filename", "image_path", "label_path", "type", "material",
    "class", "width", "height", "is_crowd", "annotation_case",
    "num_annotations", "split", "image_exists",
]


def load_metadata(csv_path: str | Path | None = None) -> pd.DataFrame:
    """metadata.csv 로드 + 무결성 검증 + 파생 컬럼."""
    csv_path = Path(csv_path) if csv_path else cfg.PATHS.metadata_csv
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"metadata.csv에 필수 컬럼 없음: {missing}")

    if df["label_id"].duplicated().any():
        n = int(df["label_id"].duplicated().sum())
        raise ValueError(f"label_id 중복 {n}건 - 데이터 무결성 확인 필요")

    df["is_tile"] = (df["width"] == cfg.TILE_W) & (df["height"] == cfg.TILE_H)
    df["croppable"] = (df["width"] >= cfg.TILE_W) & (df["height"] >= cfg.TILE_H)
    df["aspect"] = df["width"] / df["height"]
    return df


def leakage_report(df: pd.DataFrame) -> pd.DataFrame:
    """클래스별 타일/파노라마 분포 -> 누수 존재 여부를 눈으로 확인."""
    rep = (df.groupby("class")
             .agg(n=("label_id", "size"),
                  n_tile=("is_tile", "sum"),
                  w_mean=("width", "mean"),
                  h_mean=("height", "mean"),
                  ar_mean=("aspect", "mean"))
             .assign(tile_ratio=lambda d: (d["n_tile"] / d["n"]).round(3)))
    return rep.sort_values("n", ascending=False)


# --- 2. 서브셋 선택 -----------------------------------------------------------
def select_positives(df: pd.DataFrame, split: str,
                     data: cfg.DataConfig | None = None) -> pd.DataFrame:
    """순수 기공 이미지 (다중결함 제외)."""
    data = data or cfg.DATA
    sel = df[(df["annotation_case"] == data.positive_case)
             & (df["split"] == split)
             & (df["image_exists"])
             & (df["is_tile"])].copy()
    cap = data.max_pos_train if split == "train" else data.max_pos_val
    if cap is not None and len(sel) > cap:
        sel = sel.sample(n=cap, random_state=data.seed)
    return sel.reset_index(drop=True)


def select_negatives(df: pd.DataFrame, split: str,
                     n_needed: int,
                     data: cfg.DataConfig | None = None
                     ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    음성 후보를 (네이티브 타일, 크롭용 파노라마)로 나눠 반환.
    네이티브 타일을 우선 전량 사용하고, 모자란 만큼만 파노라마에서 크롭한다.
    """
    data = data or cfg.DATA
    base = df[(df["annotation_case"] == "normal")
              & (df["split"] == split)
              & (df["image_exists"])]

    tiles = base[base["is_tile"]].copy()
    panos = base[(~base["is_tile"]) & (base["croppable"])].copy()

    n_from_tiles = min(len(tiles), n_needed)
    tiles = tiles.sample(n=n_from_tiles, random_state=data.seed) if n_from_tiles else tiles.iloc[:0]

    remain = max(0, n_needed - n_from_tiles)
    if remain > 0 and len(panos) > 0:
        # 장당 최대 max_crops_per_pano 개까지
        n_pano = min(len(panos), -(-remain // data.max_crops_per_pano))  # ceil
        panos = panos.sample(n=n_pano, random_state=data.seed).copy()
        # 각 파노라마에 할당할 크롭 수를 균등 분배
        per = [remain // n_pano] * n_pano
        for i in range(remain % n_pano):
            per[i] += 1
        panos["n_crops"] = per
    else:
        panos = panos.iloc[:0].copy()
        panos["n_crops"] = pd.Series(dtype=int)

    return tiles.reset_index(drop=True), panos.reset_index(drop=True)


# --- 3. 파일 배치 -------------------------------------------------------------
def _place(src: Path, dst: Path, mode: str) -> None:
    """symlink/hardlink/copy. 실패 시 copy로 폴백."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    try:
        if mode == "symlink":
            os.symlink(src, dst)
        elif mode == "hardlink":
            os.link(src, dst)
        else:
            shutil.copy2(src, dst)
    except (OSError, NotImplementedError):
        shutil.copy2(src, dst)


def _rng_for(label_id: int, k: int, seed: int) -> random.Random:
    """label_id 기반 결정적 난수 - 재실행해도 같은 크롭이 나오게."""
    h = hashlib.md5(f"{seed}:{label_id}:{k}".encode()).hexdigest()
    return random.Random(int(h[:16], 16))


# --- 4. 빌드 ------------------------------------------------------------------
def build_split(df: pd.DataFrame, split: str,
                paths: cfg.Paths | None = None,
                data: cfg.DataConfig | None = None,
                verbose: bool = True) -> dict:
    """한 split(train/val)에 대해 YOLO 데이터셋을 생성."""
    paths = paths or cfg.PATHS
    data = data or cfg.DATA

    img_dir = paths.yolo_root / "images" / split
    lbl_dir = paths.yolo_root / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    pos = select_positives(df, split, data)
    n_neg = int(round(len(pos) * data.neg_ratio))
    neg_tiles, neg_panos = select_negatives(df, split, n_neg, data)

    manifest: list[dict] = []
    stat = {"split": split, "pos_ok": 0, "pos_no_poly": 0, "pos_missing": 0,
            "neg_tile": 0, "neg_crop": 0, "neg_missing": 0,
            "total_polygons": 0}

    # --- 4-1. 양성 ---
    it = tqdm(pos.itertuples(index=False), total=len(pos),
              desc=f"[{split}] positives", disable=not verbose)
    for r in it:
        src_img = paths.raw_root / r.image_path
        src_lbl = paths.raw_root / r.label_path
        if not src_img.exists() or not src_lbl.exists():
            stat["pos_missing"] += 1
            continue

        polys, _ = extract_porosity_polygons(
            src_lbl, int(r.width), int(r.height),
            assume_all_porosity=True,
            max_points=data.max_polygon_points,
            min_area_norm=data.min_polygon_area_norm,
        )
        if not polys:
            # 폴리곤을 하나도 못 뽑았으면 양성으로 쓰면 안 됨(라벨 없는 결함 = 오답 학습)
            stat["pos_no_poly"] += 1
            continue

        stem = Path(r.filename).stem
        dst_img = img_dir / f"{stem}.jpg"
        _place(src_img, dst_img, data.link_mode)
        write_yolo_seg_label(lbl_dir / f"{stem}.txt", polys)

        stat["pos_ok"] += 1
        stat["total_polygons"] += len(polys)
        manifest.append({"stem": stem, "label": 1, "source": "tile",
                         "label_id": int(r.label_id), "n_poly": len(polys),
                         "src_image": str(src_img)})

    # --- 4-2. 음성: 네이티브 타일 ---
    it = tqdm(neg_tiles.itertuples(index=False), total=len(neg_tiles),
              desc=f"[{split}] neg-tiles", disable=not verbose)
    for r in it:
        src_img = paths.raw_root / r.image_path
        if not src_img.exists():
            stat["neg_missing"] += 1
            continue
        stem = Path(r.filename).stem
        _place(src_img, img_dir / f"{stem}.jpg", data.link_mode)
        write_yolo_seg_label(lbl_dir / f"{stem}.txt", [])  # 빈 파일 = background
        stat["neg_tile"] += 1
        manifest.append({"stem": stem, "label": 0, "source": "tile",
                         "label_id": int(r.label_id), "n_poly": 0,
                         "src_image": str(src_img)})

    # --- 4-3. 음성: 파노라마 랜덤 크롭 ---
    it = tqdm(neg_panos.itertuples(index=False), total=len(neg_panos),
              desc=f"[{split}] neg-crops", disable=not verbose)
    for r in it:
        src_img = paths.raw_root / r.image_path
        if not src_img.exists():
            stat["neg_missing"] += 1
            continue

        W0, H0 = int(r.width), int(r.height)
        if W0 < cfg.TILE_W or H0 < cfg.TILE_H:
            continue

        # 좌표는 metadata의 width/height로 이미 결정 가능 -> 디코딩 전에 존재 여부 확인
        stems, coords = [], []
        for k in range(int(r.n_crops)):
            rng = _rng_for(int(r.label_id), k, data.seed)
            x0 = rng.randint(0, W0 - cfg.TILE_W)
            y0 = rng.randint(0, H0 - cfg.TILE_H)
            stems.append(f"{Path(r.filename).stem}_crop{k}_{x0}_{y0}")
            coords.append((x0, y0))

        if all((img_dir / f"{s}.jpg").exists() and (lbl_dir / f"{s}.txt").exists()
               for s in stems):
            stat["neg_crop"] += len(stems)          # 이미 존재 -> 디코딩 없이 스킵
            for s in stems:
                manifest.append({"stem": s, "label": 0, "source": "crop",
                                 "label_id": int(r.label_id), "n_poly": 0,
                                 "src_image": str(src_img)})
            continue

        try:
            with Image.open(src_img) as im:
                im = im.convert("RGB")
                W, H = im.size
                if (W, H) != (W0, H0):
                    # metadata와 실제 파일 크기가 다르면 좌표가 안 맞으므로 재계산
                    stems, coords = [], []
                    for k in range(int(r.n_crops)):
                        rng = _rng_for(int(r.label_id), k, data.seed)
                        x0 = rng.randint(0, W - cfg.TILE_W)
                        y0 = rng.randint(0, H - cfg.TILE_H)
                        stems.append(f"{Path(r.filename).stem}_crop{k}_{x0}_{y0}")
                        coords.append((x0, y0))
                for stem, (x0, y0) in zip(stems, coords):
                    dst_jpg = img_dir / f"{stem}.jpg"
                    if not dst_jpg.exists():
                        crop = im.crop((x0, y0, x0 + cfg.TILE_W, y0 + cfg.TILE_H))
                        crop.save(dst_jpg, quality=95, subsampling=0)
                        write_yolo_seg_label(lbl_dir / f"{stem}.txt", [])
                    stat["neg_crop"] += 1
                    manifest.append({"stem": stem, "label": 0, "source": "crop",
                                     "label_id": int(r.label_id), "n_poly": 0,
                                     "src_image": str(src_img)})
        except (OSError, ValueError) as e:
            stat["neg_missing"] += 1
            if verbose:
                print(f"  crop 실패 {src_img.name}: {e}")

    # --- 4-4. 매니페스트 저장 (평가/추적용) ---
    mf = pd.DataFrame(manifest)
    mf.to_csv(paths.yolo_root / f"manifest_{split}.csv", index=False, encoding="utf-8-sig")
    stat["n_images"] = len(mf)
    return stat


def build_quick_subset(
    paths: cfg.Paths | None = None,
    n_pos_train: int = 300, n_neg_train: int = 300,
    n_pos_val: int = 60, n_neg_val: int = 60,
    seed: int = 42,
    variant: str = "quick",
) -> Path:
    """
    양성/음성 균형이 보장된 소규모(또는 중간 규모) 서브셋을 별도 폴더에 만든다.
    스모크 테스트(--quick)와 데모용 학습(--demo)이 서로 다른 크기를 요구하므로
    `variant`별로 폴더를 분리하고, 호출할 때마다 **해당 폴더를 비우고 재생성**한다
    (이전 실행의 파일이 남아 섞이는 것을 방지 - Ultralytics는 매니페스트가 아니라
    폴더 안 파일을 그대로 긁어가므로, 남은 파일이 있으면 의도한 구성이 깨진다).

    Ultralytics의 `fraction` 인자는 무작위 샘플링이 아니라
    `sorted(im_files)[:count]` 로 앞부분만 자른다 (실제 소스 확인됨).
    우리 파일명이 "RT_ST_00_*"(정상) / "RT_ST_02_*"(기공) 로 클래스별로
    뭉쳐 있어서, fraction을 쓰면 잘린 서브셋이 정상 이미지로만
    채워지는 사고가 난다 (실제로 재현됨: loss가 전부 0으로 찍힘).
    그래서 fraction 대신, manifest_{split}.csv의 label 컬럼을 이용해
    양성/음성을 직접 균형 샘플링하고, 이미 만들어진 본 데이터셋의
    이미지/라벨 파일을 hardlink로 가져와 별도 폴더를 구성한다.
    본 데이터셋(images/train 등)은 전혀 건드리지 않는다.
    """
    paths = paths or cfg.PATHS
    subset_root = paths.subset_root(variant)
    if subset_root.exists():
        shutil.rmtree(subset_root)  # 이전 실행 잔재 제거 - 정확한 재현성 보장

    for split, n_pos, n_neg in (("train", n_pos_train, n_neg_train),
                                ("val", n_pos_val, n_neg_val)):
        mf = pd.read_csv(paths.yolo_root / f"manifest_{split}.csv")
        pos = mf[mf["label"] == 1]
        neg = mf[mf["label"] == 0]
        if len(pos) == 0:
            raise ValueError(f"{split}: manifest에 양성(label=1) 이미지가 0개. "
                             f"build_all()을 먼저 실행했는지 확인할 것.")

        n_pos_eff, n_neg_eff = min(n_pos, len(pos)), min(n_neg, len(neg))
        pos_s = pos.sample(n=n_pos_eff, random_state=seed)
        neg_s = neg.sample(n=n_neg_eff, random_state=seed)

        img_dir = subset_root / "images" / split
        lbl_dir = subset_root / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        src_img_dir = paths.yolo_root / "images" / split
        src_lbl_dir = paths.yolo_root / "labels" / split
        for stem in pd.concat([pos_s, neg_s])["stem"]:
            for ext, ddir, sdir in ((".jpg", img_dir, src_img_dir),
                                    (".txt", lbl_dir, src_lbl_dir)):
                dst, src = ddir / f"{stem}{ext}", sdir / f"{stem}{ext}"
                if not dst.exists() and src.exists():
                    try:
                        os.link(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

        print(f"[{variant}] {split}: 양성 {n_pos_eff} + 음성 {n_neg_eff} "
              f"= {n_pos_eff + n_neg_eff}장"
              + (f" (요청 {n_pos}+{n_neg}보다 가용량이 적어 축소됨)"
                 if (n_pos_eff, n_neg_eff) != (n_pos, n_neg) else ""))

    names = "\n".join(f"  {i}: {n}" for i, n in enumerate(cfg.CLASS_NAMES))
    text = (
        f"# auto-generated by porosity.data_prep.build_quick_subset (variant={variant})\n"
        f"path: {subset_root.resolve().as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        f"nc: {len(cfg.CLASS_NAMES)}\n"
        "names:\n"
        f"{names}\n"
    )
    yaml_path = paths.subset_dataset_yaml(variant)
    yaml_path.write_text(text, encoding="utf-8")
    return yaml_path


def write_dataset_yaml(paths: cfg.Paths | None = None) -> Path:
    """Ultralytics dataset.yaml 생성 (경로는 POSIX 슬래시로 기록)."""
    paths = paths or cfg.PATHS
    root = paths.yolo_root.resolve().as_posix()
    names = "\n".join(f"  {i}: {n}" for i, n in enumerate(cfg.CLASS_NAMES))
    text = (
        "# auto-generated by porosity.data_prep\n"
        f"path: {root}\n"
        "train: images/train\n"
        "val: images/val\n"
        f"nc: {len(cfg.CLASS_NAMES)}\n"
        "names:\n"
        f"{names}\n"
    )
    paths.dataset_yaml.parent.mkdir(parents=True, exist_ok=True)
    paths.dataset_yaml.write_text(text, encoding="utf-8")
    return paths.dataset_yaml


def build_all(df: pd.DataFrame | None = None,
              paths: cfg.Paths | None = None,
              data: cfg.DataConfig | None = None,
              verbose: bool = True) -> pd.DataFrame:
    """train/val 전체 빌드 + dataset.yaml + 설정 스냅샷 기록."""
    paths = paths or cfg.PATHS
    data = data or cfg.DATA
    paths.ensure()
    df = load_metadata() if df is None else df

    stats = [build_split(df, s, paths, data, verbose) for s in ("train", "val")]
    write_dataset_yaml(paths)
    (paths.yolo_root / "build_config.json").write_text(
        json.dumps(cfg.snapshot(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return pd.DataFrame(stats)


# --- 5. 검증 ------------------------------------------------------------------
def verify_dataset(paths: cfg.Paths | None = None, sample: int = 200) -> dict:
    """이미지/라벨 1:1 대응, 라벨 문법, 좌표 범위, 크기 일관성 검사."""
    paths = paths or cfg.PATHS
    out: dict = {}
    for split in ("train", "val"):
        img_dir = paths.yolo_root / "images" / split
        lbl_dir = paths.yolo_root / "labels" / split
        imgs = {p.stem for p in img_dir.glob("*.jpg")}
        lbls = {p.stem for p in lbl_dir.glob("*.txt")}

        r = {
            "n_images": len(imgs),
            "n_labels": len(lbls),
            "image_without_label": len(imgs - lbls),
            "label_without_image": len(lbls - imgs),
            "empty_labels": 0,
            "bad_lines": 0,
            "bad_coords": 0,
            "wrong_size": 0,
        }
        for stem in lbls:
            txt = (lbl_dir / f"{stem}.txt").read_text(encoding="utf-8").strip()
            if not txt:
                r["empty_labels"] += 1
                continue
            for line in txt.splitlines():
                parts = line.split()
                if len(parts) < 7 or (len(parts) - 1) % 2 != 0:
                    r["bad_lines"] += 1
                    continue
                try:
                    vals = [float(v) for v in parts[1:]]
                except ValueError:
                    r["bad_lines"] += 1
                    continue
                if any(v < -1e-6 or v > 1 + 1e-6 for v in vals):
                    r["bad_coords"] += 1

        chk = list(imgs)[:sample]
        for stem in chk:
            try:
                with Image.open(img_dir / f"{stem}.jpg") as im:
                    if im.size != (cfg.TILE_W, cfg.TILE_H):
                        r["wrong_size"] += 1
            except OSError:
                r["wrong_size"] += 1
        r["size_checked"] = len(chk)
        out[split] = r
    return out

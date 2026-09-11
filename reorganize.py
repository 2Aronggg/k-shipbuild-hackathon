import shutil
from pathlib import Path

base = Path.home() / "weldscan/raw_download/127.창원_지역_특화산업_고도화_및_디지털_전환_촉진을_위한_용접_AI_학습_데이터/3.개방데이터/1.데이터"
out = Path.home() / "weldscan/weld_db"

# (원본 폴더, split, 이미지 or 라벨) 매핑
mapping = [
    ("Training/01.원천데이터", "train", "images"),
    ("Training/02.라벨링데이터", "train", "labels"),
    ("Validation/01.원천데이터", "val", "images"),
    ("Validation/02.라벨링데이터", "val", "labels"),
]

for rel_path, split, kind in mapping:
    src_root = base / rel_path
    dst_dir = out / kind / split
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    ext = "*.jpg" if kind == "images" else "*.json"
    files = list(src_root.glob(f"**/{ext}"))
    
    for f in files:
        shutil.copy2(f, dst_dir / f.name)
    
    print(f"{rel_path} → {dst_dir}: {len(files)}개 복사 완료")
    
import json, csv
from pathlib import Path

db_root = Path.home() / "weldscan/weld_db"
rows = []
errors = []

for split in ["train", "val"]:
    label_dir = db_root / "labels" / split
    image_dir = db_root / "images" / split
    json_files = list(label_dir.glob("*.json"))
    print(f"[{split}] 라벨 {len(json_files)}개 처리 시작...")

    for i, json_path in enumerate(json_files, 1):
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

            info = data["info"]
            img = data["image_data"]
            meta = data["meta"]
            annots = data.get("annotations", [])

            filename = img["file_name"] + "." + img["format"]
            image_path = image_dir / filename
            image_exists = image_path.exists()

            if not image_exists:
                errors.append(f"이미지 없음: {filename} (라벨: {json_path.name})")

            rows.append({
                "label_id": info.get("id"),
                "filename": filename,
                "image_path": f"images/{split}/{filename}",
                "label_path": f"labels/{split}/{json_path.name}",
                "type": info.get("type"),
                "material": info.get("material"),
                "class": img.get("information"),
                "width": img.get("width"),
                "height": img.get("height"),
                "is_crowd": meta.get("is_crowd"),
                "annotation_case": ",".join(meta.get("annotation_case", [])),
                "num_annotations": len(annots),
                "split": split,
                "image_exists": image_exists,
            })
        except Exception as e:
            errors.append(f"파싱 실패: {json_path.name} - {e}")

        if i % 5000 == 0 or i == len(json_files):
            print(f"  {i}/{len(json_files)} 처리 완료")

out_path = db_root / "metadata.csv"
with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"\n총 {len(rows)}개 항목 → {out_path}")
print(f"에러/불일치 {len(errors)}건")

if errors:
    err_path = db_root / "errors.txt"
    with open(err_path, "w", encoding="utf-8") as f:
        f.write("\n".join(errors))
    print(f"에러 상세 내역 → {err_path}")

from collections import Counter
class_split_counts = Counter((r["class"], r["split"]) for r in rows)
print("\n클래스별 분포:")
for (cls, sp), cnt in sorted(class_split_counts.items()):
    print(f"  {cls} ({sp}): {cnt}장")
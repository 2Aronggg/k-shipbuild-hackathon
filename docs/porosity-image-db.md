# 용접 결함 이미지 DB 구축

**관련 파일**: `reorganize.py`, `build_metadata.py`(루트) / `weldscan_porosity/src/porosity/data_prep.py`, `config.py`

RT(방사선투과검사) 원본 이미지를 내려받아 정리하는 단계부터, YOLOv8-seg 학습에 바로 쓸 수 있는 형태로 가공하는 단계까지 두 단계로 구성됩니다.

```
AI Hub 원천/라벨링 데이터
    ↓ ① reorganize.py       원본 zip/폴더 → weld_db/images, weld_db/labels로 정리
    ↓ ② build_metadata.py   파일 단위 메타데이터 생성 → weld_db/metadata.csv
    ↓ ③ data_prep.py        metadata.csv → YOLO 학습셋(images/labels, train/val)
YOLOv8-seg 학습 입력
```

---

## 1. 원천 데이터

- 출처: [AI Hub - 창원 지역 특화산업 고도화 및 디지털 전환 촉진을 위한 용접 AI 학습 데이터](https://www.aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&dataSetSn=71761)
- 조선소·선박 제조 현장에서 수집한 방사선투과검사(RT) 이미지 + 폴리곤 라벨
- 전체 데이터셋(VT/RT, 강재/알루미늄) 중 **RT + 일반강재(ST)** 조합만 사용

| 항목 | 내용 |
|---|---|
| 데이터 유형 | JPG 이미지, JSON 폴리곤 라벨 |
| 클래스 | 정상, 균열(Crack), 기공(Porosity), 융합불량(Lack of Fusion), 슬래그혼입(Slag Inclusion) |
| 해상도 | 1280×720 픽셀 이상 (정상 원본은 평균 3165×917의 파노라마) |
| 라벨링 형식 | Polygon (결함 부위 좌표) |

| Split | 정상 | 균열 | 기공 | 융합불량 | 슬래그혼입 | 합계 |
|---|---:|---:|---:|---:|---:|---:|
| Train | 21,051 | 1,831 | 21,653 | 2,599 | 920 | 48,054 |
| Val | 2,645 | 223 | 2,692 | 329 | 110 | 5,999 |
| **총계** | **23,696** | **2,054** | **24,345** | **2,928** | **1,030** | **54,053** |

현재 학습 모델(YOLOv8-seg)은 **기공(porosity) 단일 클래스**만 다룹니다. 원본 이미지·라벨은 용량·배포 정책 때문에 저장소에 포함하지 않습니다.

## 2. 원본 정리 — `reorganize.py`, `build_metadata.py`

AI Hub에서 원천데이터(`TS_RTST_*`, `VS_RTST_*`)와 라벨링데이터(`TL_RTST_*`, `VL_RTST_*`)를 내려받은 뒤 실행합니다.

```bash
python reorganize.py       # weld_db/images, weld_db/labels 생성
python build_metadata.py   # weld_db/metadata.csv 생성
```

`metadata.csv`에는 파일 단위로 `label_id, filename, image_path, label_path, type, material, class, width, height, is_crowd, annotation_case, num_annotations, split, image_exists` 컬럼이 들어가며, 이후 모든 학습/사례 DB 빌드가 이 파일 하나를 진실 공급원으로 사용합니다.

## 3. YOLO 학습셋 빌드 — `data_prep.py`

### 왜 그냥 크롭하면 안 되는가 (데이터 누수)

기공(porosity) 이미지는 라벨링 시 전량 1280×720으로 이미 크롭되어 있는 반면, 정상 이미지의 91%는 원본 파노라마(평균 3165×917)입니다. 그대로 학습하면 모델이 결함 유무가 아니라 **"이미지 크기·종횡비"로 클래스를 외우는** 문제가 생깁니다.

**해결책**: 음성(정상) 샘플을 두 소스에서만 취해 양성/음성의 픽셀 통계를 구분 불가능하게 만듭니다.

1. 이미 1280×720인 정상 이미지 (그대로 사용)
2. 정상 파노라마(1280×720 이상)에서 **네이티브 스케일로 랜덤 크롭**한 1280×720 타일

크롭 좌표는 `label_id` 기반 해시 시드로 결정되어, 재실행해도 항상 같은 크롭이 나오도록 재현성을 보장합니다.

### 양성/음성 비율 및 라벨 규칙

| 설정 | 값 | 의미 |
|---|---|---|
| `TILE_W × TILE_H` | 1280 × 720 | 학습 타일 크기 (기공 원본 크롭 규격과 동일) |
| `positive_case` | `"porosity"` | 다중결함 이미지는 양성에서 제외 |
| `neg_ratio` | 1.0 | 양성 1장당 음성 1장 (음성 우선 네이티브 타일 → 부족분만 파노라마 크롭) |
| `max_crops_per_pano` | 2 | 파노라마 1장당 최대 크롭 수 |
| `link_mode` | `hardlink` | 이미지 배치 방식 (Windows 기본값, symlink는 관리자 권한 필요) |

정상 이미지의 라벨 JSON에는 "정상" 어노테이션이 1개 들어있지만, YOLO 포맷에서는 **빈 `.txt` = background**로 기록합니다(클래스 0으로 넣으면 학습이 붕괴).

기공 폴리곤을 하나도 추출하지 못한 이미지는 양성에서 제외합니다(라벨 없는 결함을 정답으로 학습시키지 않기 위함).

### 산출물 구조

```
work/yolo_porosity/
├── images/{train,val}/*.jpg
├── labels/{train,val}/*.txt        # YOLO-seg 폴리곤 포맷, 빈 파일 = 배경
├── manifest_{train,val}.csv        # stem, label(0/1), source(tile/crop), 추적용
├── dataset.yaml                    # Ultralytics 학습 설정
└── build_config.json               # 빌드 당시 설정 스냅샷
```

작은 규모로 빠르게 실험하거나(`--quick`) 데모용 중간 규모 세트(`--demo`)가 필요하면 `build_quick_subset()`이 본 데이터셋을 건드리지 않고 별도 폴더에 균형 샘플링된 서브셋을 hardlink로 구성합니다. (`Ultralytics`의 `fraction` 인자는 무작위가 아니라 파일명 정렬 후 앞부분만 잘라 쓰기 때문에, 클래스별로 파일명이 뭉쳐 있는 이 데이터셋에서는 직접 쓸 수 없어 우회한 방식입니다.)

### 실행

```bash
cd weldscan_porosity
python -c "from porosity import data_prep as dp; dp.build_all()"
python -c "from porosity import data_prep as dp; print(dp.verify_dataset())"
```

`verify_dataset()`은 이미지·라벨 1:1 대응, 라벨 문법, 좌표 범위(0~1), 타일 크기(1280×720) 일치 여부를 검사합니다.

## 4. 이 이미지 DB를 쓰는 다음 단계

- **YOLO 결함 탐지 모델 학습/추론**: [`docs/porosity-yolo-usage.md`](porosity-yolo-usage.md)
- **유사사례 매칭용 사례 DB 구축**(`case_db_build.py` — 동일 `metadata.csv`의 GT 라벨을 사례 DB로 변환): [`docs/porosity-similarity-mechanism.md`](porosity-similarity-mechanism.md)

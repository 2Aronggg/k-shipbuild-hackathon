# 기공(Porosity) YOLOv8-seg 결함 탐지 모듈

**담당**: 최건우 (YOLOv8-seg 결함 탐지 학습)
**상태**: 데모/발표용 학습 완료. 정확도 개선은 본선 진출 후 진행 예정.

---

## 이 모듈이 하는 일

용접부 RT(방사선투과검사) 이미지를 넣으면, **기공 결함이 있는지 자동으로 판정**하고 각 기공의 위치·크기를 알려준다.

## 코드 위치

```
weldscan_porosity/
├── src/porosity/          ← 실제 로직 (데이터 처리, 학습, 추론)
├── notebooks/              ← 학습 과정 노트북
└── train_porosity.py       ← 학습 실행 스크립트
```

## ⚠️ 가중치 파일은 여기 없음 (별도 전달)

`best.pt`(학습된 모델 가중치, ~24MB)는 용량 문제로 Git에 안 올렸다.
**담당자에게 `porosity_yolov8seg.zip` 파일을 카톡/드라이브로 직접 전달받아야 한다.**

압축 풀면 이렇게 3개 파일이 나온다 — **항상 같은 폴더에 함께 둘 것**:
```
porosity_yolov8seg/
├── best.pt              ← 실제 AI 모델
├── thresholds.json       ← 판정 기준값
└── model_config.json     ← 모델 정보 요약
```

## 사용법 (3줄)

```python
from porosity.detector import PorosityDetector

det = PorosityDetector.from_artifacts("porosity_yolov8seg 폴더 경로")
result = det.predict("이미지파일.jpg", pixel_spacing_mm=0.1)
```

`porosity` 패키지를 임포트하려면 `weldscan_porosity/src`를 파이썬 경로에 추가해야 한다:
```python
import sys
sys.path.insert(0, "weldscan_porosity/src 경로")
```

### 결과값(`result`)에서 꺼내 쓸 것

| 키 | 의미 |
|---|---|
| `result["verdict"]` | `"abnormal"`(이상) 또는 `"normal"`(정상) |
| `result["score"]` | 확신도 (0~1, 높을수록 확실) |
| `result["n_instances"]` | 검출된 기공 개수 |
| `result["instances"]` | 기공 하나하나의 좌표·크기·직경(mm) 리스트 |
| `result["total_area_ratio"]` | 이미지 대비 기공 총 면적 비율 |

`instances[i]["equivalent_diameter_mm"]`는 등급 판정 로직(KS B 0845)에서 그대로 쓸 수 있다.

## 입력 이미지 규격

- **1280×720 크기로 잘린 이미지**여야 정확하다 (학습 데이터와 동일 규격).
- 원본 RT 필름처럼 훨씬 큰 파노라마 이미지가 들어오면 `det.tile_predict()`를 대신 써야 한다 (내부적으로 타일 단위로 슬라이딩하며 추론).
- `pixel_spacing_mm`(픽셀당 실제 mm 환산 계수)은 현재 데이터에 없어서 임시로 `0.1`을 쓰고 있다. **실제 값이 확인되면 알려줄 것** — 이게 정확해야 `equivalent_diameter_mm`이 신뢰할 수 있다.

## 현재 성능 (데모 기준)

전체 val 5,350장 중 학습에 안 쓰인 held-out 데이터 기준:

| 지표 | 값 |
|---|---|
| recall (재현율) | 0.83 |
| precision (정밀도) | 0.97 |
| accuracy | 0.90 |

**해석**: 실제 기공이 있는 이미지 100장 중 83장을 잡아내고, "이상"이라고 판정한 것 중 97%가 진짜 기공이다. 오탐(가짜 경고)이 거의 없다.

## 알려진 한계 (본선 통과 후 개선 예정)

1. 학습에 전체 데이터(24,209장) 중 **일부(8,000장)만 사용**, 60에폭 대신 **25에폭**만 학습 — 시간 절약을 위한 의도적 스케일 다운. 본선 통과 후 전체 데이터로 재학습 예정.
2. 원본 정상 필름 이미지(크롭 아님) 중 일부에서 오탐률이 상대적으로 높음(약 27%) — 필름 마커/노이즈가 기공과 혼동되는 것으로 추정. 크롭된 이미지에서는 오탐률 0.3%로 매우 낮음.
3. 기공 외 다른 결함(균열/융합불량/슬래그혼입)은 이 모델이 학습하지 않음 — 다른 결함 이미지를 넣으면 "정상"으로 잘못 판정될 수 있음.

## 막히면

`porosity` 임포트 안 되거나, 결과 형식이 이상하거나, 성능 관련 질문 있으면 최건우한테 바로 연락.

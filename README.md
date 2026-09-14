# K-조선 선박 용접 데이터 및 규정 텍스트 벡터 DB

조선·선박 제조 현장의 용접 결함 분석을 위한 두 종류의 데이터를 정리한 저장소입니다.

- 이미지 데이터: 방사선투과검사(RT) 이미지와 폴리곤 라벨
- 텍스트 데이터: 한국선급(KR) 규정 기반 RAG용 하이브리드 검색 DB

## 1. 용접 이미지 데이터셋

### 출처

- [AI Hub - 창원 지역 특화산업 고도화 및 디지털 전환 촉진을 위한 용접 AI 학습 데이터](https://www.aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&dataSetSn=71761)
- 조선소 및 선박 제조 현장에서 수집한 방사선투과검사(RT) 이미지와 라벨링 데이터

전체 데이터셋(VT/RT, 강재/알루미늄) 중 **RT + 일반강재(ST)** 조합을 사용합니다.

| 항목 | 내용 |
|---|---|
| 데이터 유형 | JPG 이미지, JSON 폴리곤 라벨 |
| 클래스 | 정상, 균열(Crack), 기공(Porosity), 융합불량(Lack of Fusion), 슬래그혼입(Slag Inclusion) |
| 해상도 | 1280×720 픽셀 이상 |
| 라벨링 형식 | Polygon (결함 부위 좌표) |

| Split | 정상 | 균열 | 기공 | 융합불량 | 슬래그혼입 | 합계 |
|---|---:|---:|---:|---:|---:|---:|
| Train | 21,051 | 1,831 | 21,653 | 2,599 | 920 | 48,054 |
| Val | 2,645 | 223 | 2,692 | 329 | 110 | 5,999 |
| **총계** | **23,696** | **2,054** | **24,345** | **2,928** | **1,030** | **54,053** |

원본 이미지·라벨은 용량과 배포 정책 때문에 저장소에 포함하지 않습니다. AI Hub에서 원천데이터(`TS_RTST_*`, `VS_RTST_*`)와 라벨링데이터(`TL_RTST_*`, `VL_RTST_*`)를 내려받은 뒤 다음 스크립트를 실행합니다.

```bash
python reorganize.py       # weld_db/images, weld_db/labels 생성
python build_metadata.py   # weld_db/metadata.csv 생성
```

## 2. 규정 텍스트 벡터 DB

### 목적

`kr_reg_vectordb/`는 용접 결함 판독 결과와 보고서에 규정 근거를 붙이기 위한 RAG 검색용 데이터베이스입니다. 규정 텍스트를 조항 단위로 나누고, 각 청크에 조항·페이지·출처 메타데이터를 함께 저장했습니다.

### 어떤 데이터인가

기본 인덱스에는 [한국선급 선급 및 강선규칙 제2편 재료 및 용접 2026](https://www.krs.co.kr/KRRules/KRRules2026/data/data_part/korean/2편_2026.pdf)의 다음 범위가 들어 있습니다.

| 구분 | 포함 범위 | 청크 수 |
|---|---|---:|
| KR 규칙 | 제2편 제2장 | 151 |
| KR 적용지침 | 제2편 제2장 | 28 |
| KR 적용지침 | 부록 2-7 선체 용접이음부 비파괴검사 기준 | 35 |
| KR 적용지침 | 부록 2-12 향상된 비파괴검사 | 24 |
| 구조화 표 | 부록 2-7 표 12~16 전사본 | 6 |
| **합계** |  | **244** |

KS B 0845, KS D 0272, IACS Rec.20은 `sources.yaml`에 출처와 라이선스만 기록하고 현재는 `skip: true`로 제외했습니다. KS 원문을 구매·확보한 경우에만 로컬에 추가하고 설정을 변경해야 합니다.

### 어떻게 구축했는가

```text
규정 PDF
  → PyMuPDF 페이지별 텍스트 추출
  → 반복 머리글·꼬리글 제거 및 PDF 줄바꿈 복원
  → 편 > 장 > 절 > 조 > 항 계층 파싱
  → 조항 단위 청킹, 긴 조항은 항/호/목 경계에서 분할
  → breadcrumb·페이지·인용 메타데이터 추가
  → BM25 문자 2/3-gram + dense 임베딩 FAISS 인덱스 생성
```

고정 길이로 문장을 자르지 않고 조항 경계를 우선합니다. 기본 청크 상한은 약 700 토큰이며, 분할 시 직전 항을 짧게 오버랩합니다. 검색 점수는 dense 0.6, BM25 0.4를 사용하고, `RT`, `porosity`, `crack`, `repair`, `acceptance` 등의 토픽 태그와 문서 유형 필터를 지원합니다.

### 디렉터리와 산출물

```text
kr_reg_vectordb/
├── build_vector_db.py       PDF → 청킹 → 인덱싱 파이프라인
├── retrieve.py              하이브리드 검색 및 LLM 컨텍스트 포맷
├── verify.py                통계·조항 커버리지·검색 스모크 테스트
├── sources.yaml             문서 출처, 판본, 적용일, 라이선스 설정
├── tables/
│   └── kr_appx2-7_rt_tables.json  RT 판정표 구조화 데이터
├── out/
│   ├── chunks.jsonl         244개 청크와 인용 메타데이터
│   ├── dense.faiss          사전 생성 dense 인덱스
│   ├── bm25.pkl             BM25 인덱스
│   └── manifest.json        빌드 시각·모델·차원·청크 수
├── 구축보고서.md             구축 결과와 검증 기록
└── README.md                상세 설계 문서
```

원문 PDF는 공개 저장소에 재배포하지 않습니다. 재빌드가 필요하면 `sources.yaml`의 URL에서 허용된 원문을 `kr_reg_vectordb/raw/2편_2026.pdf`로 내려받아 사용하세요. 원문 및 파생 텍스트의 재배포 여부는 각 발행기관의 라이선스를 확인해야 합니다.

### 검색·검증 실행

```bash
cd kr_reg_vectordb
python -m venv .venv
source .venv/bin/activate
pip install pymupdf rank-bm25 pyyaml numpy sentence-transformers faiss-cpu

python verify.py out
python retrieve.py out "기공 결함점수 판정기준"
```

임베딩 모델을 다시 받아 인덱스를 재생성하려면 다음과 같이 실행합니다. 최초 실행 시 모델 다운로드가 필요합니다.

```bash
python build_vector_db.py --src sources.yaml --out out \
  --model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

`retrieve.py`에서 반환하는 각 결과에는 `citation`, `page_start`, `page_end`, `source_url`가 포함되어 보고서의 근거 인용에 사용할 수 있습니다.

## 3. WeldScan 품질 관제 대시보드

`weldscan_dashboard_1.html`은 용접 비파괴검사(NDT) 결과와 한국선급(KR) 규정 판정의 일관성을 한 화면에서 확인하는 정적 관리자 대시보드입니다. 별도의 빌드 도구나 백엔드 없이 브라우저에서 바로 열 수 있습니다.

### 실행

```bash
open weldscan_dashboard_1.html
```

또는 파일을 브라우저 창으로 직접 드래그해도 됩니다. 화면은 다음 기능을 제공합니다.

- 90일 판정 필름과 목표 지표 추적
- 규정 마진별 등급 분포 및 검사자 판정 경계 비교
- 결함 유형별 AI 모델 지원 범위와 전제 조건 공시
- 부위·결함·연차별 불일치율 및 지식 격차 탐색
- AI 보고서 검토 결과와 규정 조항 인용 커버리지 확인
- 에스컬레이션 대기 건과 사유별 부하 분석
- 모재 두께를 입력해 KR 표 15·16의 허용 한계를 확인하는 계산기

### 데이터와 해석상 주의사항

대시보드는 `kr_reg_vectordb/tables/kr_appx2-7_rt_tables.json`의 규정 판정표와 `kr_reg_vectordb/out/`의 조항 메타데이터를 근거로 사용합니다. 판정 이력·보고서 검토·에스컬레이션 데이터는 화면 동작을 위한 합성 데이터이며, 규정 판정표·조항·모델 성능 지표는 실데이터 기반입니다. 현재 학습 모델은 기공 단일 클래스이고, 픽셀-실치수 환산값과 KS B 0845 원문은 확정되지 않았으므로 화면의 전제 조건을 함께 확인해야 합니다.

기획안과 구현 사이의 변경 사항, 데이터 한계, 미구현 항목은 [`design-decisions.md`](design-decisions.md)에 기록했습니다.

## 라이선스 및 주의사항

이 저장소의 이미지 데이터는 AI Hub 원천 데이터의 배포 조건을 따릅니다. 규정 데이터는 한국선급 및 표준 발행기관의 저작권·이용 조건을 따르며, 판정 결과를 실제 선급 제출이나 안전 의사결정에 사용하기 전에는 최신 원문과 공식 기준을 다시 확인해야 합니다.

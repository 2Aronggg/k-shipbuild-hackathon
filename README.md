# WeldScan AI

**용접부 RT(방사선투과검사) 이미지에서 결함을 탐지하고, 과거 유사사례와 한국선급(KR) 규정을 근거로 검사 보고서를 자동 생성하는 조선업 품질검사 보조 시스템**

🔗 **배포**: [k-shipbuild-hackathon.streamlit.app](https://k-shipbuild-hackathon.streamlit.app/)
📄 **발표자료(PPT)**: _추가 예정_

---

## 대회 개요

- **2026 K-조선 해커톤** — HD한국조선해양·한화오션·삼성중공업 공동주관, 조선업 AX(AI 전환) 솔루션 주제
- 평가 핵심 항목: 창의성 30점, 실현가능성 30점
- 제출 마감 9월 21일 / 본선 11월 9일 (서울 양재 엘타워)

## 팀 구성

| 이름 | 역할 |
|---|---|
| 영진 | 기획 / 발표 |
| 필호 | 백엔드 (FastAPI, RAG 규정 검색) |
| **아형** | **AI 모델링** (수학·빅데이터사이언스 복수전공) |
| 건우 | 프론트엔드 (React) / YOLOv8-seg 학습 |

## 왜 WeldScan AI인가

기존 연구는 대부분 결함 **탐지**에서 끝나지만, WeldScan AI는 탐지 결과에 **규정 근거를 붙인 자연어 보고서 생성**까지 확장합니다. "NDT 검사원 대체"가 아니라 "보조" 포지셔닝으로, RT(방사선 투과) 이미지 범위에 한정해 규제 현실에 맞춘 실현가능성을 확보했습니다.

## 시스템 파이프라인

```
RT 이미지 입력
    ↓ ① YOLOv8-seg 결함 탐지        → 기공 위치·크기·개수
    ↓ ② 유사사례 매칭                → 과거 사례 DB(26,299건) 중 유사 top-5 + 위험도
    ↓ ③ 규정 벡터DB 검색 (RAG)       → KR 선급 기준 조항 근거 (244청크)
    ↓ ④ LLM 보고서 생성              → 판정 근거 + 적용 조항이 포함된 자연어 보고서
    ↓ ⑤ 관제 대시보드                → 검사자 판독 → 책임검사원 확정 → 관리자 규정 일치율 모니터링
```

- 모델: AI Hub 용접 데이터셋(RT+일반강재, 54,053장)으로 파인튜닝한 YOLOv8-seg (현재 기공 단일 클래스)
- RAG 지식베이스: 한국선급 선급 및 강선규칙 제2편(재료 및 용접) 2026년판 기반
- LLM API: Claude API(Anthropic) 메인, GPT-4o 백업

## 문서

| 구성 요소 | 문서 |
|---|---|
| 1. 전체 시스템 개요 | (이 문서) |
| 2. 규정 DB 구축 (RAG용 텍스트 벡터 DB) | [`kr_reg_vectordb/README.md`](kr_reg_vectordb/README.md) |
| 3. 이미지 DB 구축 (RT 원본 → YOLO 학습셋) | [`docs/porosity-image-db.md`](docs/porosity-image-db.md) |
| 4. YOLOv8-seg 결함 탐지 | [`docs/porosity-yolo-usage.md`](docs/porosity-yolo-usage.md) |
| 5. 유사사례 매칭 (판단 메커니즘) | [`docs/porosity-similarity-mechanism.md`](docs/porosity-similarity-mechanism.md) |
| 관제 대시보드 (관리자·검사자 화면) | [`weldscan-dashboard/README.md`](weldscan-dashboard/README.md) |

각 문서는 데이터 출처, 처리 파이프라인, 설계 이유(왜 이렇게 했는가), 알려진 한계까지 함께 기록되어 있습니다.

## 관제 대시보드

[`weldscan-dashboard/`](weldscan-dashboard/)는 용접 NDT 판정과 KR 규정 판정의 일관성을 한 화면에서 확인하는 관리자 대시보드와, 검사자·책임검사원용 판독 화면으로 구성됩니다. 로컬 실행 방법과 화면 구성은 해당 README를 참고하세요. 배포된 버전은 상단 링크로 바로 확인할 수 있습니다.

## 라이선스 및 주의사항

이 저장소의 이미지 데이터는 AI Hub 원천 데이터의 배포 조건을 따릅니다. 규정 데이터는 한국선급 및 표준 발행기관의 저작권·이용 조건을 따르며, 판정 결과를 실제 선급 제출이나 안전 의사결정에 사용하기 전에는 최신 원문과 공식 기준을 다시 확인해야 합니다.

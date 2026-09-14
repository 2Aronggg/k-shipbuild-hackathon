# WeldScan 품질 관제 대시보드

이 디렉터리는 용접 비파괴검사(NDT) 결과와 한국선급(KR) 규정 판정의 일관성을 확인하는 정적 관리자 대시보드입니다.

## 현재 포함된 파일

```text
weldscan_dashboard/
├── README.md
├── weldscan_dashboard.html
└── docs/
    └── design-decisions.md
```

`weldscan_dashboard.html`은 별도 빌드 과정 없이 브라우저에서 바로 열 수 있습니다.

```bash
open weldscan_dashboard.html
```

## 요청 구조와의 매핑

현재 작업 폴더와 Git 브랜치에서 확인된 Claude 산출물 중 대시보드에 직접 대응하는 파일만 배치했습니다.

| 요청 파일 | 상태 |
|---|---|
| `weldscan_dashboard.html` | 포함 — 기존 `weldscan_dashboard_1.html`을 이름 변경 |
| `docs/design-decisions.md` | 포함 — 기존 설계 결정 문서를 이동 |
| `connect_yolo.py` | 미확인 — 작업 폴더와 원격 브랜치에 없음 |
| `gen2.py` | 미확인 — 작업 폴더와 원격 브랜치에 없음 |
| `clauses.json` | 미확인 — 작업 폴더와 원격 브랜치에 없음 |
| `data2.json` | 미확인 — 작업 폴더와 원격 브랜치에 없음 |
| `real_labels.json` | 미확인 — 작업 폴더와 원격 브랜치에 없음 |

누락된 파일은 내용이 확인되지 않은 상태에서 기존 규정 DB 파일로 대체하지 않았습니다. 원본 산출물을 추가하면 이 디렉터리에 파일을 넣고 대시보드의 데이터 로딩 경로를 함께 검증해야 합니다.

## 데이터 주의사항

대시보드 내부의 판정 이력·보고서 검토·에스컬레이션 데이터는 화면 동작을 위한 합성 데이터입니다. 규정 판정표·조항·모델 성능 지표의 근거와 구현상의 한계는 [`docs/design-decisions.md`](docs/design-decisions.md)를 참조하세요.

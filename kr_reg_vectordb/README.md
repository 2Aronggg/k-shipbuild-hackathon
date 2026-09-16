# 규정 텍스트 벡터 DB (RAG용) — 설계·구축 문서

역할: 텍스트 벡터 DB 구축 (파이프라인 ⑥ 결과 확인 → ⑧ 상급자 전송 시 규정 근거 인용, 판독 보고서의 "적용 조항" 생성)
확인일: 2026-09-09

---

## 1. 소스와 최신 판 확인 결과

| doc_id | 문서 | 최신 판 | 시행·발행일 | 입수 경로 | 라이선스 |
|---|---|---|---|---|---|
| KR_RULES_2026_PART2 | 한국선급 선급 및 강선규칙 **제2편 재료 및 용접** | **2026년판** (2025년판을 대체) | 2026-07-01 이후 건조계약·승인신청분 적용 | https://www.krs.co.kr/KRRules/KRRules2026/data/data_part/korean/2편_2026.pdf | KR 공개 PDF |
| KR_GUIDANCE_2026_PART2 | 같은 PDF 뒷부분의 **적용지침** 2편 (2장 + 부록 2-7 선체 용접이음부 비파괴검사 기준 + 부록 2-12) | 2026 | 상동 | 상동 | 상동 |
| KS_B_0845_2021 | **KS B 0845 강 용접 이음부의 방사선투과검사** | **2021-03-25 개정판** (팀 노트의 "KS B 0845"는 2015 확인판을 가리킬 가능성 → 2021판으로 교체) | 2021-03-25 | KSSN 구매 https://www.kssn.net/search/stddetail.do?itemNo=K001010132099 (PDF 약 2.5만원) | 저작권 표준. 구매본 내부 사용만 가능, 원문 재배포 금지 |
| KS_D_0272_2005 | KS D 0272 용접부 RT 시험방법 및 판정기준 | 2005 (확인 상태 재확인 필요) | 2005-12-15 | KSSN | 상동 |
| IACS_REC_20 | IACS Rec. No.20 Non-destructive Testing of Ship Hull Steel Welds | 확인 필요 | — | iacs.org.uk | 공개 |

팀 노트에 있던 2024 링크(`KRRules2024/.../2편_2024.pdf`)는 두 판 전입니다. 2026 KR-Rules 페이지(https://www.krs.co.kr/KRRules/KRRules2026/KRRulesK.html)에서 2편 2026이 배포 중이고, 문서 첫 장에 "2026년 7월 1일 이후 적용"과 2025년판 대비 개정 조항(2장 4절 404·405 등)이 명시돼 있습니다.

**KS B 0845는 웹에 공개된 전문이 없습니다.** 벡터 DB에 넣으려면 팀에서 1부 구매해 `raw/KS_B_0845_2021.pdf`로 두고 `sources.yaml`의 `skip: false`로 바꿔야 합니다. 그 전까지 KS 관련 청크는 비어 있습니다.

### 파이프라인에서 실제로 쓰이는 범위

기공 결함 기준으로 판정·보고서에 인용될 규정은 다음 순서입니다.

1. **KS B 0845 (2021)** — 결함 종별(1종 둥근 블로홀, 2종 가늘고 긴 슬래그·용입불량·융합불량, 3종 균열류, 4종 텅스텐 개재물)과 시험시야·결함점수에 따른 **1~4급 등급분류표**. 룰엔진 `regulations.py`의 판정 근거가 여기서 나와야 합니다.
2. **KR 2편 2장 3절 309(용접부의 품질)·310(용접부의 보수)** — 선급 관점의 합부·보수 요건. 2편 2장 4절 404·405는 용접절차 인정시험의 RT·굽힘 판정.
3. **KR 적용지침 2편 2장** — NDT 검사 범위·방법·판정 요건 (IACS Rec.20 기반).

1편 재료(압연강재 화학성분 등)는 판정에 쓰이지 않으므로 기본 설정은 **2장 용접만** 인덱싱합니다(`chapters: ["2"]`). 필요하면 1장도 추가.

---

## 2. 청킹 방식

규정 문서는 `편 > 장 > 절 > 조(NNN.) > 항(N.) > 호((N)) > 목((가))` 계층입니다. 고정 길이 슬라이딩 윈도는 조항 경계를 잘라서 인용이 틀어지므로 **구조 기반 청킹**을 씁니다.

| 단계 | 처리 |
|---|---|
| 페이지 추출 | PyMuPDF로 페이지별 텍스트 (페이지 번호 = 인용 메타) |
| 머리글 제거 | `2 편 재료 및 용접`, `2 장 용접 2 편 2 장`, `선급 및 강선규칙 2026 126` 같은 반복 머리글·꼬리글을 정규식으로 삭제 |
| 목차 제거 | `차 례` 이후 점선(`·····`) 행은 건너뛰고, 본문 `제 N 장`이 다시 나오면 해제 |
| 구조 파싱 | `제 N 편/장/절`, `NNN. 제목 (개정연도) 【지침 참조】` 패턴으로 조(article) 노드 생성. 같은 PDF 안에서 `적용지침` 차례를 만나면 `doc_type=guidance`로 전환 |
| 기본 단위 | **조(article) 1개 = 청크 1개** |
| 긴 조 분할 | 조 본문을 항(`1.`, `2.`) 경계에서 그리디 패킹, 청크당 약 700 토큰 상한, **직전 항 1개 오버랩** |
| 문맥 접두 | 모든 청크 앞에 breadcrumb `[KR 2편 2026 > 2편 재료 및 용접 > 2장 용접 > 3절 용접시공 및 검사 > 310. 용접부의 보수]`를 붙임 → 임베딩이 "어느 규정의 어느 조항인지"를 함께 담음 |
| 토픽 태그 | 키워드 규칙으로 `RT / UT / MT_PT / porosity / crack / lack_of_fusion / slag / repair / acceptance / welding_procedure / welder / consumable` 자동 부여 → 검색 시 감점 필터 |

700 토큰은 다국어 임베딩 모델의 입력 한도보다 훨씬 작지만, LLM 프롬프트에 근거 5개를 넣었을 때 3,500 토큰 안에 들어오도록 잡은 값입니다. 표(화학성분표 등)는 PDF 텍스트 추출에서 셀 순서가 깨지므로 표가 많은 1장은 제외하는 것이 낫고, KS B 0845의 등급분류표는 **표를 수동으로 JSON으로 옮겨 별도 청크(`doc_type=ks_table`)로 넣는 것**을 권장합니다.

---

## 3. 데이터 형태 (chunks.jsonl 1행)

```json
{
  "chunk_id": "1bc9b34b49c64cf4",
  "doc_id": "KR_RULES_2026_PART2",
  "doc_type": "rule",
  "title": "선급 및 강선규칙 제2편 재료 및 용접",
  "publisher": "한국선급(KR)",
  "edition": "2026",
  "effective_date": "2026-07-01",
  "source_url": "https://www.krs.co.kr/KRRules/KRRules2026/data/data_part/korean/2편_2026.pdf",
  "license": "KR 공개 배포 PDF",
  "part": "2", "chapter": "2", "section": "3", "article": "310",
  "article_title": "용접부의 보수",
  "citation": "KR 2편 2편 2장 310.",
  "breadcrumb": "KR 2편 2026 > 2편 재료 및 용접 > 2장 용접 > 3절 용접시공 및 검사 > 310. 용접부의 보수",
  "page_start": 126, "page_end": 126,
  "split_index": 0, "split_total": 1,
  "n_chars": 169, "approx_tokens": 118,
  "topics": ["MT_PT", "repair", "acceptance"],
  "text": "[KR 2편 2026 > … > 310. 용접부의 보수]\n1. …\n(1) …\n2. …"
}
```

- `text`만 임베딩합니다. 나머지는 필터·인용용 메타.
- `citation`은 보고서에 그대로 찍는 문자열, `source_url`+`page_start`는 관리자 대시보드에서 원문으로 점프하는 링크.
- 산출물: `chunks.jsonl`(원본 청크), `dense.faiss`(다국어 MiniLM 384차원, 코사인), `bm25.pkl`(문자 2/3-gram BM25Plus), `manifest.json`(빌드 정보·모델·문서 목록).

---

## 4. 구축 절차

```bash
pip install pymupdf rank_bm25 faiss-cpu sentence-transformers pyyaml numpy
# 1) 청킹만 확인
python build_vector_db.py --src sources.yaml --out out --dry-run
# 2) 임베딩 포함 (다국어 MiniLM 모델 다운로드, CPU도 가능)
python build_vector_db.py --src sources.yaml --out out
# 3) 검색 테스트
python retrieve.py out "기공 직경 3mm 초과 등급"
```

RAG 파이프라인(@필호)에서는 `retrieve.Retriever("out").search(query, k=5, topics=[...], doc_types=[...])` → `format_context(hits)`를 프롬프트에 넣으면 됩니다. 검색 점수는 dense 0.6 + BM25 0.4. 조항 번호("310조", "KS B 0845 4급")처럼 정확 일치가 중요한 질의는 BM25가 받쳐 줍니다.

---

## 5. 반드시 고칠 것 (룰엔진과의 정합)

`regulations.py`의 `"basis": "KS B 0845 3.2조"`, `"3.3조"` 같은 조항 번호는 KS B 0845 원문 구조와 맞지 않을 가능성이 큽니다. KS B 0845는 결함을 **종별(1~4종)** 로 나누고, **시험시야 안의 결함점수와 결함 길이**로 **1~4급**을 매기는 구조라서 "균열은 무조건 4급", "기공은 직경 1.5 / 3 mm로 1~3급" 같은 단순 문턱값과 다릅니다. 구매본을 받은 뒤 등급분류표를 JSON으로 옮기고 룰엔진 문턱값을 표 기준으로 다시 짜야 합니다. 벡터 DB의 `citation`이 룰엔진 `basis`와 같은 문자열 형식을 쓰도록 맞춰 두면 보고서에서 두 출처가 충돌하지 않습니다.

---

## 6. 갱신 정책

- KR 규칙은 매년 7월 1일 신판. `sources.yaml`의 `KRRules{YEAR}` 경로만 바꾸고 재빌드. `manifest.json`의 `edition`으로 어느 판이 인덱싱됐는지 추적.
- 유효 회보(개정 통합본 `Circular (K) Total_2026.pdf`)도 같은 페이지에 있으므로, 연중 개정을 반영하려면 소스로 추가.
- 청크 ID는 `doc_id + 장 + 조 + 분할번호 + 본문 앞 64자` 해시라 개정된 조항만 ID가 바뀝니다. 판정 이력 DB에 `chunk_id`를 저장해 두면 "어느 판 어느 조항으로 판정했는지"가 남습니다.

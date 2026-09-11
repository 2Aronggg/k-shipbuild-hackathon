#!/usr/bin/env python3
"""verify.py — 벡터 DB 검증용. python verify.py out [원본PDF]
1) 통계  2) 조항 커버리지  3) 무작위 청크 5개와 원본 페이지 텍스트 대조  4) 검색 스모크 테스트"""
import json, sys, random, collections, statistics, re
out = sys.argv[1] if len(sys.argv) > 1 else "out"
pdf = sys.argv[2] if len(sys.argv) > 2 else None
cs = [json.loads(l) for l in open(f"{out}/chunks.jsonl", encoding="utf8")]
print(f"# 청크 {len(cs)}개"); print(json.load(open(f"{out}/manifest.json", encoding="utf8"))["docs"])
t = [c["approx_tokens"] for c in cs]
print(f"토큰(추정) min {min(t)} / 중앙값 {statistics.median(t)} / max {max(t)} / 800 초과 {sum(x>800 for x in t)}개")
print("\n# 문서·장별 청크 수"); [print(f"  {k[0]:<28}{k[1]:<10}{v}") for k, v in sorted(collections.Counter((c['doc_id'], c['chapter']) for c in cs).items())]
print("\n# 토픽 분포"); print(dict(collections.Counter(tp for c in cs for tp in c["topics"])))
print("\n# 조항 목록 (doc_type/chapter/article: 제목, 청크 수)")
arts = collections.OrderedDict()
for c in cs: arts.setdefault((c["doc_type"], c["chapter"], c["article"], c["article_title"]), 0); arts[(c["doc_type"], c["chapter"], c["article"], c["article_title"])] += 1
for k, v in arts.items(): print(f"  {k[0]:<9}{k[1]:<10}{k[2]:<5}{k[3][:30]:<32}x{v}")
print("\n# 무작위 청크 5개 (page 대조용)")
random.seed(0)
for c in random.sample(cs, 5):
    print(f"\n--- {c['chunk_id']} | {c['citation']} | p.{c['page_start']}-{c['page_end']} | {c['topics']}")
    print(c["text"][:400].replace("\n", " ⏎ "))
    if pdf:
        import pymupdf
        doc = pymupdf.open(pdf)
        pg = "".join(doc[p - 1].get_text() for p in range(c["page_start"], c["page_end"] + 1))
        probe = re.sub(r"\s", "", c["text"].split("\n", 1)[1][:30])
        print(f"  원본 p.{c['page_start']}-{c['page_end']}에서 본문 첫 15자 발견:", probe[:15] in re.sub(r"\s", "", pg))
print("\n# 검색 스모크")
from retrieve import Retriever
r = Retriever(out)
for q in ["기공 결함점수 판정기준", "균열은 허용되는가", "용접부 보수 방법", "IQI 투과도계 감도", "재촬영 조건"]:
    h = r.search(q, k=3); print(f"  Q: {q}\n     → " + " | ".join(f"{x['citation']} {x['article_title'][:12]}" for x in h))

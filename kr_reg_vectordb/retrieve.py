#!/usr/bin/env python3
"""
retrieve.py — 하이브리드 검색 (bge-m3 dense + BM25) + 메타데이터 필터 + 인용 포맷

  from retrieve import Retriever
  r = Retriever("./out")
  hits = r.search("기공 직경 3mm 초과 시 등급", k=5, topics=["porosity","acceptance"], doc_types=["ks","rule"])
  print(r.format_context(hits))    # LLM 프롬프트에 그대로 삽입

검색 점수 = 0.6 * dense(cosine) + 0.4 * bm25(min-max 정규화). 가중치는 --alpha로 조정.
"""
from __future__ import annotations
import json, os, pickle, re
from typing import List, Optional
import numpy as np

def char_ngrams(s: str, n=(2, 3)):
    s = re.sub(r"\s+", " ", s)
    return [s[i:i+k] for k in n for i in range(len(s) - k + 1)]

class Retriever:
    def __init__(self, path: str, model_name: Optional[str] = None, alpha: float = 0.6):
        self.chunks = [json.loads(l) for l in open(os.path.join(path, "chunks.jsonl"), encoding="utf8")]
        with open(os.path.join(path, "bm25.pkl"), "rb") as f:
            self.bm25 = pickle.load(f)
        self.alpha = alpha
        self.index = self.model = None
        fp = os.path.join(path, "dense.faiss")
        if os.path.exists(fp):
            import faiss
            from sentence_transformers import SentenceTransformer
            if model_name is None:
                manifest_path = os.path.join(path, "manifest.json")
                try:
                    with open(manifest_path, encoding="utf8") as f:
                        model_name = json.load(f).get("embedding_model")
                except (FileNotFoundError, json.JSONDecodeError):
                    model_name = None
            model_name = model_name or "BAAI/bge-m3"
            self.index = faiss.read_index(fp)
            self.model = SentenceTransformer(model_name)

    def search(self, query: str, k: int = 5, topics: Optional[List[str]] = None,
               doc_types: Optional[List[str]] = None, doc_ids: Optional[List[str]] = None):
        n = len(self.chunks)
        bm = np.asarray(self.bm25.get_scores(char_ngrams(query)), dtype="float32")
        bm = (bm - bm.min()) / (bm.max() - bm.min() + 1e-9)
        if self.index is not None:
            q = self.model.encode([query], normalize_embeddings=True).astype("float32")
            D, I = self.index.search(q, n)
            dense = np.zeros(n, dtype="float32"); dense[I[0]] = D[0]
            score = self.alpha * dense + (1 - self.alpha) * bm
        else:
            score = bm
        # 메타 필터 (필터는 소거가 아니라 감점 → 후보가 없을 때도 결과가 나오도록)
        for i, c in enumerate(self.chunks):
            if topics and not set(topics) & set(c["topics"]): score[i] *= 0.5
            if doc_types and c["doc_type"] not in doc_types: score[i] *= 0.3
            if doc_ids and c["doc_id"] not in doc_ids: score[i] *= 0.3
        order = np.argsort(-score)[:k]
        return [dict(self.chunks[i], score=float(score[i])) for i in order]

    @staticmethod
    def format_context(hits: List[dict]) -> str:
        """LLM에 넣을 근거 블록. 출처·조항·페이지를 항상 붙인다."""
        out = []
        for h in hits:
            out.append(f"<source id=\"{h['chunk_id']}\" cite=\"{h['citation']}\" "
                       f"edition=\"{h['edition']}\" pages=\"{h['page_start']}-{h['page_end']}\" "
                       f"url=\"{h['source_url']}\">\n{h['text']}\n</source>")
        return "\n\n".join(out)

if __name__ == "__main__":
    import sys
    r = Retriever(sys.argv[1] if len(sys.argv) > 1 else "./out")
    q = sys.argv[2] if len(sys.argv) > 2 else "용접부 결함 보수"
    for h in r.search(q, k=5):
        print(f"{h['score']:.3f}  {h['citation']}  {h['article_title']}  p.{h['page_start']}  {h['topics']}")

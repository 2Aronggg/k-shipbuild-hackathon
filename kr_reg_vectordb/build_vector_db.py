#!/usr/bin/env python3
"""
build_vector_db.py — 용접 결함 판정 RAG용 규정 벡터 DB 구축

입력  : 규정 PDF (한국선급 선급 및 강선규칙 2편 2026, KS B 0845:2021 등) 또는 텍스트 파일
처리  : PDF → 페이지 텍스트 → 머리글/꼬리글 제거 → 편/장/절/조/항/호 구조 파싱
        → 조(article) 단위 청크, 긴 조는 항(1., 2.) 경계에서 분할 → 부모 경로(breadcrumb)를 청크 앞에 삽입
        → 다국어 dense 임베딩(FAISS) + BM25(형태소 없이 문자 n-gram) 하이브리드
출력  : out/chunks.jsonl, out/dense.faiss, out/bm25.pkl, out/manifest.json

사용  :
  python build_vector_db.py --src sources.yaml --out ./out            # 전체 구축
  python build_vector_db.py --src sources.yaml --out ./out --dry-run  # 청킹만(임베딩 생략)
  python build_vector_db.py --text-file sample.txt --doc-id demo --dry-run

sources.yaml 예시는 README 참조.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, pickle, datetime, urllib.request
from dataclasses import dataclass, asdict, field
from typing import List, Optional

# ----------------------------------------------------------------------------
# 1. 문서 로드
# ----------------------------------------------------------------------------
def download(url: str, dest: str) -> str:
    if os.path.exists(dest):
        return dest
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest

def pdf_pages(path: str) -> List[str]:
    import pymupdf
    doc = pymupdf.open(path)
    return [p.get_text("text") for p in doc]

# KR 규칙 PDF(PyMuPDF 추출)의 머리글/꼬리글 패턴 — 페이지 상단 8줄 안에서만 제거
HEADER_PATTERNS = [
    r"^\s*\d\s*편\S*\s*$",                       # "2 편재료및용접"
    r"^\s*\d\s*장\S*\s*$",                       # "2 장용접", "1 장재료"
    r"^\s*\d\s*편\s*\d\s*장\s*$",               # "2 편2 장"
    r"^\s*\d\s*편\s*부록\s*\d-\d+\s*$",         # "2 편부록2-7"
    r"^\s*부록\d-\d+\s*\S*\s*$",                     # "부록2-7 선체용접이음부의비파괴검사기준" (공백 없음 = 머리글)
    r"^\s*선급\s*및\s*강선규칙\s*(적용지침)?\s*\d{4}\s*$",
    r"^\s*\d{1,3}\s*$",                            # 페이지 번호
    r"^\s*-\s*[ivx]+\s*-\s*$",
]
_hdr = [re.compile(p) for p in HEADER_PATTERNS]

def clean_page(text: str):
    """머리글 제거 + 줄바꿈 복원. 반환: (logical_lines, is_guidance_page)"""
    raw = text.splitlines()
    is_guid = any("적용지침" in ln.replace(" ", "") and "선급및강선규칙" in ln.replace(" ", "") for ln in raw[:8])
    body = []
    for i, ln in enumerate(raw):
        if i < 8 and any(h.match(ln) for h in _hdr):
            continue
        if not ln.strip():
            continue
        body.append(ln)
    # PDF 줄바꿈 복원: 새 항목 마커로 시작하면 새 줄, 앞 줄이 문장 끝이면 공백, 아니면 단어 중간이므로 그대로 붙임
    NEW = re.compile(r"^\s*(\(\d+\)|\([가-힣a-z]\)|\d{1,3}\.\s|[①-⑳]|표\s*\d|그림\s*\d|\(비고\)|제\s*\d+\s*[장절]|부록\s+\d-\d+)")
    TITLE = re.compile(r"^\s*\d{1,3}\.\s+\S[^.]{0,40}$")
    lines = []
    for ln in body:
        # 제목과 본문이 한 물리행에 있는 경우: "312. 제목 (2021) 본문…" → 두 줄로
        m = re.match(r"^(\s*\d{3}\.\s+\S.{0,30}?\s*\(\d{4}\))\s+(\S.{30,})$", ln)
        if m:
            lines.append(m.group(1)); ln = m.group(2)
        if not lines or NEW.match(ln):
            lines.append(ln); continue
        prev = lines[-1]
        if TITLE.match(prev):                      # 조/부록항목 제목 줄에는 본문을 붙이지 않음
            lines.append(ln); continue
        if prev.rstrip().endswith((".", "】", ")", ":")):
            lines[-1] = prev.rstrip() + " " + ln.lstrip()
        else:
            lines[-1] = prev.rstrip(" ") + ("" if not prev.endswith(" ") else " ") + ln.lstrip()
    return lines, is_guid

# ----------------------------------------------------------------------------
# 2. 구조 파싱  (편 > 장 > 절 > 조(NNN.) > 항(N.) > 호((N)) > 목((가)))
# ----------------------------------------------------------------------------
RE_PART    = re.compile(r"^\s*제\s*(\d+)\s*편\s+(.+?)\s*$")
RE_CHAPTER = re.compile(r"^\s*제\s*(\d+)\s*장\s+(\S.{0,20}?)\s*$")
RE_SECTION = re.compile(r"^\s*제\s*(\d+)\s*절\s+(\S.{0,30}?)\s*$")
RE_ARTICLE = re.compile(r"^\s*(\d{3})\.\s+(\S.{0,40}?)(?:\s*\((\d{4})\))*\s*(?:【(?:지침|규칙)\s*참조】)?\s*$")
RE_APPX    = re.compile(r"^\s*부록\s+(\d-\d+)\s+(\S.+?)\s*$")
RE_APPX_ITEM = re.compile(r"^\s*(\d{1,2})\.\s+(\S[^.]{0,38}?)(?:\s*\((\d{4})\))*\s*$")   # "1. 적용", "2. 검사자 요건 (2021)"
RE_PARA    = re.compile(r"^\s*(\d{1,2})\.\s+(?!\d{3}\.)(\S.*)$")
RE_TOC_DOTS = re.compile(r"·{4,}|…{2,}")

@dataclass
class Node:
    doc_id: str
    doc_type: str            # rule | guidance | ks
    part: str = ""
    part_title: str = ""
    chapter: str = ""
    chapter_title: str = ""
    section: str = ""
    section_title: str = ""
    article: str = ""
    article_title: str = ""
    page_start: int = 0
    page_end: int = 0
    lines: List[str] = field(default_factory=list)

def parse_structure(pages: List[str], doc_id: str, doc_type_default: str = "rule",
                    part: str = "", part_title: str = "") -> List[Node]:
    """페이지 텍스트 목록을 조(article)/부록 항목 노드 목록으로 변환.
    같은 PDF 안에서 머리글이 '적용지침'으로 바뀌면 doc_type=guidance, 부록은 chapter='부록 2-N'."""
    nodes: List[Node] = []
    cur: Optional[Node] = None
    ctx = dict(doc_type=doc_type_default, part=part, part_title=part_title,
               chapter="", chapter_title="", section="", section_title="")
    in_toc = False; in_appx = False
    def close(pno):
        nonlocal cur
        if cur:
            cur.page_end = pno; nodes.append(cur); cur = None
    for pno, raw in enumerate(pages, start=1):
        lines, is_guid = clean_page(raw)
        if is_guid and ctx["doc_type"] != "guidance":
            close(pno - 1); ctx.update(doc_type="guidance", chapter="", chapter_title="", section="", section_title="")
        for ln in lines:
            if "차   례" in ln or ln.strip() in ("차 례", "차례"):
                in_toc = True; continue
            if in_toc:
                if RE_TOC_DOTS.search(ln) or ln.strip().startswith("-"):
                    continue
                in_toc = False
            m = RE_APPX.match(ln)
            if m and "·" not in ln:
                close(pno); in_appx = True
                ctx.update(chapter="부록 " + m.group(1), chapter_title=m.group(2), section="", section_title="")
                continue
            m = RE_CHAPTER.match(ln)
            if m and not in_appx:
                close(pno); ctx.update(chapter=m.group(1), chapter_title=m.group(2), section="", section_title="")
                continue
            m = RE_SECTION.match(ln)
            if m and not in_appx:
                close(pno); ctx.update(section=m.group(1), section_title=m.group(2))
                continue
            m = RE_ARTICLE.match(ln) if not in_appx else RE_APPX_ITEM.match(ln)
            if m and not (in_appx and m.group(2).rstrip().endswith("다")):
                if not cur or m.group(1) != cur.article or ctx["chapter"] != cur.chapter:
                    close(pno)
                    cur = Node(doc_id=doc_id, doc_type=ctx["doc_type"], part=ctx["part"], part_title=ctx["part_title"],
                               chapter=ctx["chapter"], chapter_title=ctx["chapter_title"],
                               section=ctx["section"], section_title=ctx["section_title"],
                               article=m.group(1), article_title=m.group(2).strip(), page_start=pno, page_end=pno)
                    continue
            if cur:
                cur.lines.append(ln)
    close(len(pages))
    return nodes

# ----------------------------------------------------------------------------
# 3. 청킹
# ----------------------------------------------------------------------------
def approx_tokens(s: str) -> int:
    # 한국어 토크나이저의 보수 추정값. 실제 모델 토크나이저로 교정 가능.
    return int(len(s) * 0.7)

LEVELS = [re.compile(r"(?=(?:^|\s)\d{1,2}\.\s)"),        # 1. 항
          re.compile(r"(?=\(\d{1,2}\)\s)"),                   # (1) 호
          re.compile(r"(?=\([가-힣]\)\s)"),                    # (가) 목
          re.compile(r"(?=\([a-z]\)\s)"),                      # (a)
          re.compile(r"(?<=다\.)\s")]                          # 문장
def split_paragraphs(lines: List[str], max_tokens: int = 700) -> List[str]:
    """항(1.) 경계로 묶고, 상한을 넘는 덩어리는 호((1)) → 목((가)) → (a) → 문장 순으로 더 잘게 나눈다."""
    paras, buf = [], []
    for ln in lines:
        if RE_PARA.match(ln) and buf:
            paras.append(" ".join(buf)); buf = []
        buf.append(ln.strip())
    if buf:
        paras.append(" ".join(buf))
    def refine(p: str, level: int) -> List[str]:
        if approx_tokens(p) <= max_tokens or level >= len(LEVELS):
            return [p]
        parts = [x.strip() for x in LEVELS[level].split(p) if x.strip()]
        if len(parts) <= 1:
            return refine(p, level + 1)
        out = []
        for x in parts:
            out += refine(x, level + 1)
        return out
    out = []
    for p in paras:
        out += refine(p, 0)
    return out

TOPIC_RULES = {
    "RT": ["방사선투과", "방사선 투과", "투과사진", "투과도계", "IQI", "필름", "농도"],
    "UT": ["초음파탐상", "초음파 탐상"],
    "MT_PT": ["자분탐상", "액체침투", "침투탐상"],
    "porosity": ["기공", "블로홀", "블로우홀"],
    "crack": ["균열", "터짐", "갈라짐"],
    "lack_of_fusion": ["융합불량", "융합 불량", "용입불량", "용입 불량"],
    "slag": ["슬래그"],
    "repair": ["보수", "재용접", "제거"],
    "acceptance": ["합격", "불합격", "허용", "판정", "등급"],
    "welding_procedure": ["용접절차", "WPS", "인정시험"],
    "welder": ["기량자격", "용접사"],
    "consumable": ["용접용재료", "용접봉", "와이어"],
}
def tag_topics(text: str) -> List[str]:
    return [k for k, kws in TOPIC_RULES.items() if any(w in text for w in kws)]

def make_chunks(nodes: List[Node], meta: dict, max_tokens: int = 700, overlap_paras: int = 1) -> List[dict]:
    chunks = []
    for n in nodes:
        breadcrumb = " > ".join(x for x in [
            f"{meta.get('title','')} {meta.get('edition','')}".strip(),
            f"{n.part}편 {n.part_title}".strip() if n.part else "",
            (f"{n.chapter} {n.chapter_title}" if n.chapter.startswith("부록") else f"{n.chapter}장 {n.chapter_title}").strip() if n.chapter else "",
            f"{n.section}절 {n.section_title}".strip() if n.section else "",
            f"{n.article}. {n.article_title}".strip(),
        ] if x)
        paras = split_paragraphs(n.lines, max_tokens)
        if not paras:
            continue
        # 항 단위 그리디 패킹 + 1항 오버랩
        groups, cur, cur_tok = [], [], 0
        for p in paras:
            t = approx_tokens(p)
            if cur and cur_tok + t > max_tokens:
                groups.append(cur)
                cur = [x for x in cur[-overlap_paras:] if approx_tokens(x) <= 150] if overlap_paras else []
                cur_tok = sum(approx_tokens(x) for x in cur)
            cur.append(p); cur_tok += t
        if cur:
            groups.append(cur)
        for gi, g in enumerate(groups):
            body = "\n".join(g)
            text = f"[{breadcrumb}]\n{body}"
            cid = hashlib.sha1(f"{n.doc_id}|{n.chapter}|{n.article}|{gi}|{body[:64]}".encode()).hexdigest()[:16]
            chunks.append({
                "chunk_id": cid,
                "doc_id": n.doc_id,
                "doc_type": n.doc_type,
                "title": meta.get("title"),
                "publisher": meta.get("publisher"),
                "edition": meta.get("edition"),
                "effective_date": meta.get("effective_date"),
                "source_url": meta.get("source_url"),
                "license": meta.get("license"),
                "part": n.part, "chapter": n.chapter, "section": n.section, "article": n.article,
                "article_title": n.article_title,
                "citation": re.sub(r"\s+", " ", " ".join([meta.get("short", ""), f"{n.part}편" if n.part else "",
                             "지침" if n.doc_type == "guidance" else "",
                             n.chapter if n.chapter.startswith("부록") else f"{n.chapter}장",
                             f"{n.article}."])).strip(),
                "breadcrumb": breadcrumb,
                "page_start": n.page_start, "page_end": n.page_end,
                "split_index": gi, "split_total": len(groups),
                "n_chars": len(body), "approx_tokens": approx_tokens(body),
                "topics": tag_topics(body),
                "text": text,
            })
    return chunks

# ----------------------------------------------------------------------------
# 4. 인덱싱 (dense + BM25 문자 n-gram)
# ----------------------------------------------------------------------------
def char_ngrams(s: str, n=(2, 3)) -> List[str]:
    s = re.sub(r"\s+", " ", s)
    toks = []
    for k in n:
        toks += [s[i:i+k] for i in range(len(s) - k + 1)]
    return toks

def build_indexes(chunks: List[dict], out: str,
                  model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                  dry_run=False):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "chunks.jsonl"), "w", encoding="utf8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    # BM25 (형태소 분석기 없이 동작하도록 문자 2/3-gram)
    from rank_bm25 import BM25Plus
    bm25 = BM25Plus([char_ngrams(c["text"]) for c in chunks])
    with open(os.path.join(out, "bm25.pkl"), "wb") as f:
        pickle.dump(bm25, f)
    dim = None
    if not dry_run:
        from sentence_transformers import SentenceTransformer
        import numpy as np, faiss
        model = SentenceTransformer(model_name)
        emb = model.encode([c["text"] for c in chunks], batch_size=16, normalize_embeddings=True,
                           show_progress_bar=True)
        emb = np.asarray(emb, dtype="float32"); dim = emb.shape[1]
        index = faiss.IndexFlatIP(dim); index.add(emb)
        faiss.write_index(index, os.path.join(out, "dense.faiss"))
    manifest = {
        "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "embedding_model": None if dry_run else model_name, "dim": dim,
        "n_chunks": len(chunks),
        "docs": sorted({(c["doc_id"], c["edition"] or "") for c in chunks}),
        "chunking": {"unit": "article(조)", "max_tokens": 700, "overlap": "1 paragraph(항)",
                     "breadcrumb_prefix": True},
        "bm25": "char 2/3-gram, rank_bm25 BM25Plus",
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest

# ----------------------------------------------------------------------------
# 5. 진입점
# ----------------------------------------------------------------------------
def load_sources(path: str) -> List[dict]:
    import yaml
    with open(path, encoding="utf8") as f:
        return yaml.safe_load(f)["sources"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", help="sources.yaml")
    ap.add_argument("--text-file", help="테스트용 텍스트 파일 (페이지 구분: \\f)")
    ap.add_argument("--doc-id", default="demo")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    all_chunks = []
    src_base = os.path.dirname(os.path.abspath(a.src)) if a.src else os.getcwd()

    def source_path(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return value if os.path.isabs(value) else os.path.join(src_base, value)

    if a.text_file:
        pages = open(a.text_file, encoding="utf8").read().split("\f")
        nodes = parse_structure(pages, a.doc_id, part="2", part_title="재료 및 용접")
        all_chunks += make_chunks(nodes, {"title": "DEMO", "short": "DEMO", "edition": "2026"}, a.max_tokens)
    else:
        for s in load_sources(a.src):
            if s.get("skip"):
                print(f"[skip] {s['doc_id']}: {s.get('note','')}"); continue
            path = source_path(s.get("path"))
            if path and not os.path.exists(path):
                if not s.get("url"):
                    raise FileNotFoundError(f"소스 파일이 없습니다: {path}")
                path = download(s["url"], path)
            elif not path:
                path = download(s["url"], os.path.join(src_base, "raw", s["doc_id"] + ".pdf"))
            pages = pdf_pages(path)
            nodes = parse_structure(pages, s["doc_id"], s.get("doc_type", "rule"),
                                    part=s.get("part", ""), part_title=s.get("part_title", ""))
            if s.get("chapters"):        # 예: ["2", "부록 2-7"] → 2장 용접 + 부록 2-7만 포함
                nodes = [n for n in nodes if n.chapter in s["chapters"]]
            if s.get("doc_types"):       # 같은 PDF의 규칙/지침 분리
                nodes = [n for n in nodes if n.doc_type in s["doc_types"]]
            for n in nodes:              # 지침 노드는 별도 doc_id/short 로
                if n.doc_type == "guidance" and s.get("guidance_doc_id"):
                    n.doc_id = s["guidance_doc_id"]
            ch = make_chunks(nodes, s, a.max_tokens)
            print(f"[ok] {s['doc_id']}: {len(nodes)} articles → {len(ch)} chunks")
            all_chunks += ch
    # 수동 전사한 표(JSON) → 표 하나당 청크 하나 (doc_type=kr_table). 룰엔진과 RAG가 같은 표를 본다
    for s in (load_sources(a.src) if a.src else []):
        if s.get("tables_json"):
            tables_path = source_path(s["tables_json"])
            tj = json.load(open(tables_path, encoding="utf8"))
            for t in tj["tables"]:
                lines = [f"[{s.get('title','')} {s.get('edition','')} > {tj['source']['citation_base']} > {t['table_id']} {t['title']}]"]
                for r in t["rows"]:
                    lines.append("; ".join(f"{k}: {v}" for k, v in r.items() if k != "pipeline_class"))
                for nt in t.get("notes", []):
                    lines.append("비고: " + nt)
                body = "\n".join(lines[1:])
                all_chunks.append({
                    "chunk_id": hashlib.sha1((t["citation"] + body[:64]).encode()).hexdigest()[:16],
                    "doc_id": tj["source"]["doc_id"], "doc_type": "kr_table",
                    "title": s.get("title"), "publisher": s.get("publisher"), "edition": tj["source"]["edition"],
                    "effective_date": s.get("effective_date"), "source_url": s.get("source_url"), "license": s.get("license"),
                    "part": "2", "chapter": "부록 2-7", "section": "", "article": "7", "article_title": t["title"],
                    "citation": t["citation"], "breadcrumb": lines[0].strip("[]"),
                    "page_start": t["page"], "page_end": t["page"], "split_index": 0, "split_total": 1,
                    "n_chars": len(body), "approx_tokens": approx_tokens(body), "topics": tag_topics(body),
                    "table_json": t, "text": "\n".join(lines),
                })
    m = build_indexes(all_chunks, a.out, a.model, a.dry_run)
    print(json.dumps(m, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

# app/database/bm25_index.py
from __future__ import annotations
import os, re, pickle
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from rank_bm25 import BM25Okapi
except Exception:  # soft dependency
    BM25Okapi = None

_TOKEN = re.compile(r"[A-Za-z0-9#\-/]+")

def _tok(s: str) -> List[str]:
    return [t.lower() for t in _TOKEN.findall(s or "")]

class BM25Index:
    """
    Super-lightweight BM25 index stored as a pickle beside your Chroma dir.
    If rank_bm25 isn't installed, all methods no-op safely.
    """
    def __init__(self, persist_dir: str):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.persist_dir / "bm25_index.pkl"
        self.docs: List[str] = []
        self.meta: List[Dict[str, Any]] = []
        self.bm: Optional[BM25Okapi] = None
        self._load()

    def _load(self):
        if not BM25Okapi:
            return
        if self.path.exists():
            try:
                data = pickle.loads(self.path.read_bytes())
                self.docs = data.get("docs", [])
                self.meta = data.get("meta", [])
                if self.docs:
                    self.bm = BM25Okapi([_tok(d) for d in self.docs])
            except Exception:
                self.docs, self.meta, self.bm = [], [], None

    def _save(self):
        if not BM25Okapi:
            return
        try:
            self.path.write_bytes(pickle.dumps({"docs": self.docs, "meta": self.meta}))
        except Exception:
            pass

    def add(self, texts: List[str], metas: List[Dict[str, Any]]):
        if not BM25Okapi or not texts:
            return
        self.docs.extend(texts)
        self.meta.extend(metas)
        self.bm = BM25Okapi([_tok(d) for d in self.docs])
        self._save()

    def search(self, query: str, k: int = 8) -> List[Dict[str, Any]]:
        if not BM25Okapi or not self.bm or not self.docs:
            return []
        scores = self.bm.get_scores(_tok(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        out = []
        for i in order:
            md = dict(self.meta[i])
            out.append({
                "id": md.get("id", f"bm25-{i}"),
                "score": float(scores[i]),
                "payload": {
                    "text": self.docs[i],
                    "doc_id": md.get("doc_id", ""),
                    "filename": md.get("filename", ""),
                    "page": md.get("page", 0),
                    "chunk_index": md.get("chunk_index", 0),
                    "is_diagram": md.get("is_diagram", False),
                    "section": md.get("section", ""),
                    "modality": md.get("modality", "text"),
                },
            })
        return out

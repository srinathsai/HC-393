# app/services/embedding_batcher.py
from __future__ import annotations
import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import Iterable, List, Optional

import httpx

from app.config import get_settings

# Simple, fast text->sha1 key
def _key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

class _SqliteCache:
    """Tiny persistent cache: sha1(text) -> embedding (JSON)."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, timeout=30)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS emb_cache (k TEXT PRIMARY KEY, v BLOB)"
        )
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")

    def get_many(self, keys: List[str]) -> List[Optional[bytes]]:
        out = [None] * len(keys)
        if not keys:
            return out
        qmarks = ",".join("?" for _ in keys)
        cur = self.conn.execute(f"SELECT k, v FROM emb_cache WHERE k IN ({qmarks})", keys)
        found = {k: v for (k, v) in cur.fetchall()}
        for i, k in enumerate(keys):
            out[i] = found.get(k)
        return out

    def put_many(self, items: List[tuple[str, bytes]]):
        if not items:
            return
        self.conn.executemany("INSERT OR REPLACE INTO emb_cache (k, v) VALUES (?,?)", items)
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


class EmbeddingBatcher:
    """
    Batch+cache OpenAI embeddings. Synchronous, simple, safe.

    Usage:
      batcher = EmbeddingBatcher()
      vecs = batcher.embed_texts(texts)  # -> List[List[float]]
    """
    def __init__(self, batch_size: int = 64, timeout_s: int = 60):
        self.settings = get_settings()
        self.model = self.settings.openai_embedding_model  # e.g., text-embedding-3-large
        self.api_key = self.settings.openai_api_key
        self.batch_size = max(1, int(batch_size))
        self.timeout_s = timeout_s

        # Cache location beside Chroma dir (or default ./app/chroma_data)
        from pathlib import Path as _Path
        chroma_dir = os.getenv("CHROMA_DIR") or str((_Path(__file__).resolve().parents[1] / "chroma_data").resolve())
        self.cache = _SqliteCache(str(_Path(chroma_dir) / "emb_cache.sqlite"))

        # One sync client reused across calls
        self.client = httpx.Client(timeout=self.timeout_s, headers={
            "Authorization": f"Bearer {self.api_key}"
        })

    def close(self):
        self.cache.close()
        try:
            self.client.close()
        except Exception:
            pass

    def _api_embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Single HTTP call for many inputs
        resp = self.client.post(
            "https://api.openai.com/v1/embeddings",
            json={
                "input": texts,
                "model": self.model,
            },
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        # Preserve order as returned (OpenAI keeps input order)
        return [row["embedding"] for row in data]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Returns one embedding per input, preserving order.
        Uses persistent cache; only misses are sent to the API in batches.
        """
        if not texts:
            return []

        keys = [_key(t) for t in texts]
        cached = self.cache.get_many(keys)
        out: List[Optional[List[float]]] = [None] * len(texts)

        # Fill cache hits
        misses_idx: List[int] = []
        for i, blob in enumerate(cached):
            if blob is None:
                misses_idx.append(i)
            else:
                # Stored as bytes of JSON float list; decode to list[float]
                out[i] = httpx.Response(200, content=blob).json()  # cheap JSON decode

        # Short-circuit if all hits
        if not misses_idx:
            return out  # type: ignore

        # Prepare miss texts
        miss_texts = [texts[i] for i in misses_idx]

        # Batch call the API, retrying a bit on transient errors
        inserted: List[tuple[str, bytes]] = []
        pos = 0
        while pos < len(miss_texts):
            batch = miss_texts[pos : pos + self.batch_size]
            try:
                vecs = self._api_embed_batch(batch)
            except httpx.HTTPError as e:
                # Simple backoff & retry once
                time.sleep(2.0)
                try:
                    vecs = self._api_embed_batch(batch)
                except Exception as e2:
                    # As a last resort, set empty vectors so pipeline doesn't break
                    vecs = [[0.0] * 3072 for _ in batch]  # dim for text-embedding-3-large

            # Stitch back in correct positions & prepare cache insert
            for j, vec in enumerate(vecs):
                i_global = misses_idx[pos + j]
                out[i_global] = vec
                k = keys[i_global]
                inserted.append((k, httpx.Response(200, json=vec).content))

            pos += self.batch_size

        # Persist new embeddings
        self.cache.put_many(inserted)

        # All filled
        return out  # type: ignore

# app/workers/diagram_ingestor.py
from __future__ import annotations
import base64
import io
import os
from pathlib import Path
from typing import List, Dict, Any

from app.database.vector_store import VectorStore
from app.services.image_indexer import ImageEmbedder

try:
    from PIL import Image
except Exception:
    Image = None


def _b64_to_image(b64: str):
    if not Image:
        return None
    raw = base64.b64decode(b64)
    return Image.open(io.BytesIO(raw)).convert("RGB")


def ingest_diagram_images(pages: List[Dict[str, Any]], doc_id: str, filename: str) -> int:
    """
    Build CLIP embeddings for diagram/page images and upsert to a separate collection.
    Safe no-op if CLIP or PIL isn't installed or if no page images exist.
    """
    # Soft-dep guards
    clip = ImageEmbedder()
    if not clip.ok or not Image:
        return 0

    # Collect images to embed
    items = []  # (meta_dict, PIL.Image)
    for page in pages:
        b64 = page.get("image_base64")
        if not b64:
            continue
        img = _b64_to_image(b64)
        if img is None:
            continue

        page_no = int(page.get("page", 0))
        # carry any section label your pipeline may have set (optional)
        section = ""
        if "section" in page:
            section = str(page["section"])
        # Some flows store page headers in annotations; optional
        elif "annotations" in page and page["annotations"]:
            # try a minimal heuristic
            first = str(page["annotations"][0])
            section = first[:64].upper()

        items.append((
            {
                "id": f"{doc_id}_page_{page_no}_image",
                "payload": {
                    "doc_id": str(doc_id),
                    "filename": str(filename),
                    "page": page_no,
                    "chunk_index": 0,
                    "is_diagram": True,
                    "modality": "image",
                    "section": section,
                    "text": f"IMAGE PAGE {page_no} — {section}" if section else f"IMAGE PAGE {page_no}",
                },
            },
            img
        ))

    if not items:
        return 0

    # Save to temp PNGs in-memory to feed the CLIP preprocessor
    # (ImageEmbedder takes PIL.Image internally, so we can pass the images directly)
    # Embed images
    # Create dummy paths to keep a consistent key set (not written to disk)
    # But image_embedder expects PIL; we'll adapt to accept PIL directly.
    # We expose a tiny shim here:
    from typing import Iterable, Dict, List
    import numpy as np

    # Slight adaptation: reuse the ImageEmbedder's preprocessing by saving temporaries as needed.
    # For simplicity (and to avoid disk IO), use the internal preprocessing directly:

    # Monkey patch: add a method that takes PILs if not present
    if not hasattr(clip, "embed_pils"):
        def _embed_pils(self, pil_images: Iterable[Image.Image]) -> List[List[float]]:
            import torch
            vecs = []
            with torch.no_grad():
                for im in pil_images:
                    ten = self.preprocess(im).unsqueeze(0).to(self.device)
                    feat = self.model.encode_image(ten)
                    feat = feat / feat.norm(dim=-1, keepdim=True)
                    vecs.append(feat[0].detach().cpu().numpy().astype(np.float32).tolist())
            return vecs
        clip.embed_pils = _embed_pils.__get__(clip, ImageEmbedder)

    emb_list = clip.embed_pils([img for _, img in items])

    # Upsert to separate collection
    images_vs = VectorStore(collection_name="construction_images")
    to_upsert = []
    for (meta, _), vec in zip(items, emb_list):
        meta_copy = dict(meta)
        meta_copy["vector"] = vec
        to_upsert.append(meta_copy)

    images_vs.upsert_vectors(to_upsert, batch_size=64)
    return len(to_upsert)

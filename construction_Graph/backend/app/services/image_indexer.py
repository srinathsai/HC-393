# app/services/image_indexer.py
from __future__ import annotations
from typing import Iterable, Dict, List, Optional
from pathlib import Path

import numpy as np

# Soft dependency
try:
    import open_clip, torch
    from PIL import Image
except Exception:
    open_clip = None
    torch = None
    Image = None

class ImageEmbedder:
    """CLIP embeddings for diagrams. If not available, methods return {}."""
    def __init__(self, device: Optional[str] = None):
        self.ok = open_clip is not None and torch is not None and Image is not None
        if not self.ok:
            return
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        self.tokenizer = open_clip.get_tokenizer("ViT-B-32")
        self.model = self.model.to(self.device).eval()

    def embed_images(self, paths: Iterable[str]) -> Dict[str, List[float]]:
        if not self.ok:
            return {}
        out: Dict[str, List[float]] = {}
        with torch.no_grad():
            for p in paths:
                img = Image.open(p).convert("RGB")
                ten = self.preprocess(img).unsqueeze(0).to(self.device)
                feat = self.model.encode_image(ten)
                feat = feat / feat.norm(dim=-1, keepdim=True)
                out[str(p)] = feat[0].cpu().numpy().astype(np.float32).tolist()
        return out

    def embed_text(self, queries: Iterable[str]) -> Dict[str, List[float]]:
        if not self.ok:
            return {}
        out: Dict[str, List[float]] = {}
        with torch.no_grad():
            for q in queries:
                tok = self.tokenizer([q])
                tok = {k: v.to(self.device) for k, v in tok.items()}
                feat = self.model.encode_text(**tok)
                feat = feat / feat.norm(dim=-1, keepdim=True)
                out[q] = feat[0].cpu().numpy().astype(np.float32).tolist()
        return out

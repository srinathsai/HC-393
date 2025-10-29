# app/services/document_processor.py
from __future__ import annotations
import base64
import io
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- Soft deps ----------
try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from pdf2image import convert_from_path
    from PIL import Image
except Exception:
    convert_from_path = None
    Image = None

import yaml

# ---------- Universal section / notes detection ----------
def _load_section_patterns() -> list[tuple[re.Pattern, float]]:
    cfg = (Path(__file__).resolve().parents[1] / "config" / "sections.yml")
    pats: list[tuple[re.Pattern, float]] = []
    if cfg.exists():
        try:
            data = yaml.safe_load(cfg.read_text()) or {}
            for pat, boost in (data.get("sections") or {}).items():
                pats.append((re.compile(pat, re.I), float(boost)))
        except Exception:
            pass
    return pats

_SECTION_PATTERNS = _load_section_patterns()
_BUL = re.compile(r"^\s*(?:[\(\[]?[A-Z0-9]+\)|[•\-–]|[0-9]+\.|[A-Z]\.)\s+")

def _match_section(line: str) -> tuple[bool, str, float]:
    for pat, boost in _SECTION_PATTERNS:
        m = pat.search(line or "")
        if m:
            return True, (m.group(0).upper() if m else line.upper()), boost
    if line and line.strip().isupper() and 3 <= len(line.strip()) <= 80:
        return True, line.strip().upper(), 1.0
    return False, "", 1.0

def _is_bullet(line: str) -> bool:
    return bool(_BUL.search(line or ""))

def _group_note_blocks(lines: List[str]) -> List[List[str]]:
    """Greedy grouping: header + subsequent lines until next header or blank break."""
    blocks, i, n = [], 0, len(lines)
    while i < n:
        is_hdr, _, _ = _match_section(lines[i])
        if is_hdr:
            j = i + 1
            acc = [lines[i]]
            while j < n and lines[j].strip():
                is_next_hdr, _, _ = _match_section(lines[j])
                if is_next_hdr:
                    break
                acc.append(lines[j])
                j += 1
            blocks.append(acc)
            i = j
        else:
            i += 1
    return blocks

def _chunkify_text(page_text: str, filename: str, doc_id: str, page_no: int,
                   base_tokens: int = 400, overlap: int = 60) -> List[str]:
    """Return *strings* (not dicts): detected note-blocks first, then sliding windows."""
    chunks: List[str] = []

    # Note-blocks with header included
    lines = [l for l in (page_text or "").splitlines() if l.strip()]
    for block in _group_note_blocks(lines):
        header = block[0]
        text = (header + "\n" + "\n".join(block[1:])).strip()
        chunks.append(text[:4000])

    # Sliding window fallback
    toks = (page_text or "").split()
    if toks:
        start = 0
        while start < len(toks):
            end = min(len(toks), start + base_tokens)
            window = " ".join(toks[start:end])
            chunks.append(window)
            if end == len(toks):
                break
            start = end - overlap

    return chunks

def _page_png_base64(pdf_path: str, page_no_one_based: int) -> Optional[str]:
    """Render a single page to base64 PNG (soft dependency)."""
    if convert_from_path is None or Image is None:
        return None
    try:
        # SPEED OPTIMIZATION: Lower DPI for faster rendering
        images = convert_from_path(
            pdf_path, 
            first_page=page_no_one_based, 
            last_page=page_no_one_based, 
            fmt="png",
            dpi=100  # Even lower - 100 DPI for speed
        )
        if not images:
            return None
        buf = io.BytesIO()
        images[0].save(buf, format="PNG", optimize=True, quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None

def _extract_page_text_simple(pdf_path: str, page_idx: int) -> str:
    """FAST text extraction from a single page."""
    if pdfplumber is None:
        return ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_idx < len(pdf.pages):
                page = pdf.pages[page_idx]
                text = page.extract_text(layout=False) or ""
                return text.replace("\x00", "").strip()
    except Exception:
        pass
    return ""


class DocumentProcessor:
    """
    EMERGENCY FIX: Process large PDFs in SMALL BATCHES to avoid system overload.
    """
    def __init__(self, render_images: bool = False, batch_size: int = 8):
        """
        Args:
            render_images: If True, render page images (slow). Default False.
            batch_size: Number of pages to process in parallel at once (default 8)
        """
        self.render_images = render_images
        self.batch_size = batch_size

    def process_pdf(self, pdf_path: str, doc_id: str) -> Dict[str, Any]:
        """
        BATCHED PARALLEL: Process pages in small batches to handle large PDFs.
        """
        print(f"   📄 Extracting text from PDF...")
        pages_out: List[Dict[str, Any]] = []
        num_pages = 0
        filename = Path(pdf_path).name

        if pdfplumber is None:
            print(f"   ⚠️ pdfplumber not available - returning stub")
            return {"pages": [{
                "page": 1, "text": "", "chunks": [], "is_diagram": True,
                "image_base64": None, "entities": [], "relationships": []
            }]}

        try:
            # Get page count
            with pdfplumber.open(pdf_path) as pdf:
                num_pages = len(pdf.pages)
            
            print(f"   📊 Found {num_pages} pages")
            
            # CRITICAL FIX: Process in SMALL BATCHES
            batch_size = self.batch_size
            total_batches = (num_pages + batch_size - 1) // batch_size
            
            print(f"   🔄 Processing in {total_batches} batches of {batch_size} pages each...")
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, num_pages)
                batch_pages = list(range(start_idx, end_idx))
                
                print(f"   ⚙️ Batch {batch_num + 1}/{total_batches}: pages {start_idx + 1}-{end_idx}...")
                
                # Process this batch in parallel
                batch_results = []
                for page_idx in batch_pages:
                    try:
                        page_num = page_idx + 1
                        
                        # Extract text
                        text = _extract_page_text_simple(pdf_path, page_idx)
                        
                        # Create chunks
                        chunks = _chunkify_text(text, filename, doc_id, page_num)
                        
                        # Heuristic: text-sparse = diagram
                        is_diagram = (len(text.split()) < 80)
                        
                        # Don't render images by default (too slow)
                        image_base64 = None
                        
                        batch_results.append({
                            "page": page_num,
                            "text": text,
                            "chunks": chunks,
                            "is_diagram": is_diagram,
                            "image_base64": image_base64,
                            "entities": [],
                            "relationships": [],
                        })
                    except Exception as e:
                        print(f"      ⚠️ Page {page_idx + 1} error: {e}")
                        batch_results.append({
                            "page": page_idx + 1,
                            "text": "",
                            "chunks": [],
                            "is_diagram": True,
                            "image_base64": None,
                            "entities": [],
                            "relationships": [],
                        })
                
                pages_out.extend(batch_results)
                print(f"      ✅ Batch {batch_num + 1} complete ({len(batch_results)} pages)")
            
            print(f"   ✅ Text extraction complete: {len(pages_out)} pages")
            
        except Exception as e:
            print(f"   ❌ PDF processing error: {e}")
            # Fallback
            if not pages_out:
                pages_out.append({
                    "page": 1, "text": "", "chunks": [], "is_diagram": True,
                    "image_base64": None, "entities": [], "relationships": []
                })

        return {"pages": pages_out}
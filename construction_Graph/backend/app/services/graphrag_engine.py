# app/services/graphrag_engine.py
# ULTRA-POWERFUL OPTIMIZED VERSION with EXTENSIVE DEBUGGING
# 100% BACKWARD COMPATIBLE - All existing features preserved
from __future__ import annotations
import os
import httpx
from pathlib import Path
from typing import List, Dict, Any
import logging

from app.config import get_settings, get_chroma_directory
from app.database.vector_store import VectorStore
from app.database.neo4j_client import Neo4jClient
from app.database.bm25_index import BM25Index

# Optional visual retriever (lazy)
from app.services.image_indexer import ImageEmbedder

settings = get_settings()
logger = logging.getLogger(__name__)


def _rrf(ranked_lists: List[List[str]], k: float = 60.0) -> Dict[str, float]:
    """Reciprocal Rank Fusion"""
    score: Dict[str, float] = {}
    for ranked in ranked_lists:
        for i, cid in enumerate(ranked):
            score[cid] = score.get(cid, 0.0) + 1.0 / (k + i + 1.0)
    return score


def _rank_ids(hits: List[Dict[str, Any]]) -> List[str]:
    return [h["id"] for h in sorted(hits, key=lambda d: d.get("score", 0.0), reverse=True)]


# ENHANCED SECTION BOOSTS
DEFAULT_SECTION_BOOSTS = {
    "GENERAL NOTES": 2.5,
    "PLUMBING GENERAL NOTES": 2.5,
    "MECHANICAL GENERAL NOTES": 2.5,
    "ELECTRICAL GENERAL NOTES": 2.5,
    "OVERHEAD DOOR NOTES": 2.3,
    "EQUIPMENT NOTES": 2.3,
    "INSTALLATION NOTES": 2.3,
    "CONSTRUCTION NOTES": 2.2,
    "STRUCTURAL NOTES": 2.0,
    "ELECTRICAL NOTES": 2.0,
    "VICINITY MAP": 2.0,
    "LOCATION MAP": 2.0,
    "KEY PLAN": 1.8,
    "EQUIPMENT SCHEDULE": 2.2,
    "LEGEND": 1.5,
}

# CONSTRUCTION DOMAIN SYNONYMS for query expansion
CONSTRUCTION_SYNONYMS = {
    "nitrogen generator": ["nitrogen generator", "NG", "N2 generator", "nitrogen system", "N2 gen"],
    "air handler": ["air handling unit", "AHU", "air handler", "air handling system"],
    "vav": ["VAV box", "variable air volume", "VAV unit", "terminal unit"],
    "rtu": ["roof top unit", "RTU", "rooftop unit", "packaged unit"],
    "exhaust fan": ["exhaust fan", "EF", "exhaust system"],
    "supply fan": ["supply fan", "SF"],
    "return fan": ["return fan", "RF"],
    "pump": ["pump", "HWP", "CHWP", "hot water pump", "chilled water pump"],
    "water heater": ["water heater", "WH", "domestic water heater"],
    "boiler": ["boiler", "hot water boiler", "steam boiler"],
    "chiller": ["chiller", "chilled water system"],
    "panel": ["electrical panel", "EP", "distribution panel", "panelboard"],
    "mcc": ["motor control center", "MCC", "motor starter"],
    "transformer": ["transformer", "XFMR", "electrical transformer"],
    "equipment": ["equipment", "unit", "system", "device", "component"],
    "location": ["location", "room", "zone", "area", "space"],
    "connection": ["connection", "connects to", "supplies", "serves", "feeds"],
    "specification": ["specification", "specs", "requirements", "rating"],
    "installation": ["installation", "install", "mounting", "placement"],
}


def _expand_query(q: str) -> List[str]:
    """INTELLIGENT query expansion with construction domain knowledge"""
    print(f"🔍 [QUERY EXPANSION] Original query: '{q}'")
    
    q_lower = q.lower()
    expanded = [q]
    
    # Check for synonym matches
    for key, synonyms in CONSTRUCTION_SYNONYMS.items():
        if key in q_lower:
            for syn in synonyms[:3]:  # Limit to 3 variations to avoid explosion
                if syn.lower() != key:
                    expanded.append(q.replace(key, syn))
    
    # Extract equipment tags and create variations
    import re
    tag_pattern = r'\b([A-Z]{1,4}-\d{1,4})\b'
    tags = re.findall(tag_pattern, q)
    
    if tags:
        print(f"   📋 Found equipment tags: {tags}")
        for tag in tags:
            expanded.append(q.replace(tag, tag.replace('-', ' ')))
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for exp in expanded:
        if exp.lower() not in seen:
            seen.add(exp.lower())
            result.append(exp)
    
    result = result[:5]  # Limit to 5 variations
    print(f"   ✅ Expanded to {len(result)} variations:")
    for i, var in enumerate(result, 1):
        print(f"      {i}. {var}")
    
    return result


class GraphRAGEngine:
    def __init__(self):
        print("\n" + "="*80)
        print("🚀 INITIALIZING ULTRA-POWERFUL GRAPHRAG ENGINE")
        print("="*80)
        
        # CRITICAL: Use centralized ChromaDB directory
        chroma_dir = get_chroma_directory()
        print(f"📂 ChromaDB directory: {chroma_dir}")

        # Text vectors - SINGLE SOURCE
        print("   🔄 Connecting to text vector store...")
        self.text_vs = VectorStore(persist_directory=chroma_dir, collection_name="construction_docs")
        print(f"   ✅ Text vectors: {self.text_vs.collection.count()} vectors")

        # Images collection - SINGLE SOURCE
        print("   🔄 Connecting to image vector store...")
        self.image_vs = VectorStore(persist_directory=chroma_dir, collection_name="construction_images")
        
        # BM25 side index - SINGLE SOURCE
        print("   🔄 Loading BM25 index...")
        self.bm25 = BM25Index(chroma_dir)

        # Lazy CLIP init flags
        self._clip_model: ImageEmbedder | None = None
        self._image_enabled = os.getenv("ENABLE_IMAGE_RETRIEVAL", "false").lower() == "true"

        # Neo4j
        print("   🔄 Connecting to Neo4j...")
        self.neo = Neo4jClient(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)

        # Cached count
        try:
            self._image_count = self.image_vs.collection.count()
            print(f"   ✅ Image vectors: {self._image_count} diagrams")
        except Exception:
            self._image_count = 0
            print(f"   ⚠️ Image vectors: 0 (disabled or empty)")
        
        print("="*80)
        print("✅ ENGINE READY - ULTRA-POWERFUL MODE ACTIVATED!")
        print("="*80 + "\n")

    async def query(self, query: str) -> Dict[str, Any]:
        """Main query method - BACKWARD COMPATIBLE"""
        return await self.answer(query)

    def query_sync(self, query: str) -> Dict[str, Any]:
        """Sync query method - BACKWARD COMPATIBLE"""
        import asyncio
        return asyncio.run(self.answer(query))

    async def answer(self, query: str) -> Dict[str, Any]:
        """
        ULTRA-POWERFUL answer generation with:
        - Multi-query expansion
        - 50 chunks (was 15)
        - Full text (no truncation)
        - Enhanced prompting
        """
        print("\n" + "="*80)
        print(f"💬 NEW QUERY RECEIVED")
        print("="*80)
        print(f"📝 Question: {query}")
        print("="*80 + "\n")
        
        # STEP 1: Query expansion
        print("🔍 STEP 1: QUERY EXPANSION")
        expanded_queries = _expand_query(query)
        print(f"✅ Generated {len(expanded_queries)} query variations\n")

        # STEP 2: Multi-query search
        print("🔎 STEP 2: MULTI-QUERY SEARCH")
        print(f"   Searching with {len(expanded_queries)} variations...")
        
        all_v_hits: List[Dict[str, Any]] = []
        all_b_hits: List[Dict[str, Any]] = []
        
        for idx, eq in enumerate(expanded_queries, 1):
            print(f"\n   🔍 Query {idx}/{len(expanded_queries)}: '{eq}'")
            
            # Vector search
            print(f"      📊 Vector search...")
            q_emb = await self._embed_openai(eq)
            print(f"         ✅ Embedding: {len(q_emb)} dimensions")
            
            v_hits = self.text_vs.search_vectors(q_emb, top_k=50)  # INCREASED from 25
            print(f"         ✅ Found {len(v_hits)} vector hits")
            all_v_hits.extend(v_hits)
            
            # BM25 search
            print(f"      📇 BM25 search...")
            b_hits = self.bm25.search(eq, k=50)  # INCREASED from 25
            print(f"         ✅ Found {len(b_hits)} BM25 hits")
            all_b_hits.extend(b_hits)
        
        # Deduplicate
        print(f"\n   🔄 Deduplicating results...")
        v_hits_map = {}
        for hit in all_v_hits:
            hit_id = hit["id"]
            if hit_id not in v_hits_map or hit["score"] > v_hits_map[hit_id]["score"]:
                v_hits_map[hit_id] = hit
        
        b_hits_map = {}
        for hit in all_b_hits:
            hit_id = hit["id"]
            if hit_id not in b_hits_map or hit["score"] > b_hits_map[hit_id]["score"]:
                b_hits_map[hit_id] = hit
        
        v_hits = list(v_hits_map.values())
        b_hits = list(b_hits_map.values())
        
        v_ids = _rank_ids(v_hits)
        b_ids = _rank_ids(b_hits)
        
        print(f"   ✅ Unique vector hits: {len(v_hits)}")
        print(f"   ✅ Unique BM25 hits: {len(b_hits)}")
        
        # Show top 3 from each
        print(f"\n   📊 Top 3 Vector Results:")
        for i, hit in enumerate(v_hits[:3], 1):
            payload = hit.get("payload", {})
            print(f"      {i}. Score: {hit.get('score', 0):.3f} | {payload.get('filename', 'unknown')[:40]} | Page {payload.get('page', 0)}")
        
        print(f"\n   📊 Top 3 BM25 Results:")
        for i, hit in enumerate(b_hits[:3], 1):
            payload = hit.get("payload", {})
            print(f"      {i}. Score: {hit.get('score', 0):.3f} | {payload.get('filename', 'unknown')[:40]} | Page {payload.get('page', 0)}")

        # STEP 3: Image/CLIP search
        print(f"\n🖼️ STEP 3: IMAGE SEARCH")
        i_hits: List[Dict[str, Any]] = []
        i_ids: List[str] = []
        
        if self._image_enabled and self._image_count > 0:
            print(f"   🔄 CLIP image search enabled...")
            clip = await self._ensure_clip()
            if clip and clip.ok:
                tvec = list(clip.embed_text([expanded_queries[0]]).values())[0]
                i_hits = self.image_vs.search_vectors(tvec, top_k=15)
                i_ids = _rank_ids(i_hits)
                print(f"   ✅ Found {len(i_hits)} diagram matches")
            else:
                print(f"   ⚠️ CLIP not available")
        else:
            print(f"   ⏭️ Image search disabled (count: {self._image_count})")

        # STEP 4: Fusion via RRF
        print(f"\n🔗 STEP 4: RECIPROCAL RANK FUSION")
        print(f"   Fusing results from vector, BM25, and image search...")
        
        fused = _rrf([v_ids, b_ids, i_ids], k=60.0)
        by_id: Dict[str, Dict[str, Any]] = {h["id"]: h for h in (v_hits + b_hits + i_hits)}
        
        print(f"   ✅ Fused to {len(fused)} unique chunks")

        # STEP 5: Section boosting
        print(f"\n⬆️ STEP 5: SECTION BOOSTING")
        boost_count = 0
        for cid in list(fused.keys()):
            p = (by_id.get(cid) or {}).get("payload") or {}
            sec = (p.get("section") or "").upper()
            original_score = fused[cid]
            boost = DEFAULT_SECTION_BOOSTS.get(sec, 1.0)
            
            # Diagram boost
            if (p.get("modality") == "image") or p.get("is_diagram", False):
                boost *= 1.15
            
            if boost > 1.0:
                fused[cid] *= boost
                boost_count += 1
                print(f"   ⬆️ Boosted '{sec}' from {original_score:.3f} to {fused[cid]:.3f}")
        
        print(f"   ✅ Applied {boost_count} boosts")

        # STEP 6: Select top chunks - MASSIVELY INCREASED
        print(f"\n📦 STEP 6: SELECTING TOP CONTEXT")
        print(f"   🎯 Target: 50 chunks (was 15 in old system)")
        
        top_ids = [cid for cid, _ in sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:50]]
        ctx = [by_id[cid] for cid in top_ids if cid in by_id]
        
        print(f"   ✅ Selected {len(ctx)} chunks for context")
        print(f"   📊 Context size: ~{sum(len(c.get('payload', {}).get('text', '')) for c in ctx)} characters")
        
        # Show top 5 selected chunks
        print(f"\n   📋 Top 5 Selected Chunks:")
        for i, chunk in enumerate(ctx[:5], 1):
            payload = chunk.get("payload", {})
            text_preview = payload.get("text", "")[:100] + "..."
            print(f"      {i}. Page {payload.get('page', 0)} | {payload.get('filename', 'unknown')[:30]}")
            print(f"         Preview: {text_preview}")

        # STEP 7: Graph facts
        print(f"\n🕸️ STEP 7: KNOWLEDGE GRAPH RETRIEVAL")
        print(f"   🔄 Querying Neo4j...")
        
        graph_facts = self.neo.simple_search(query, limit=30)  # INCREASED from 10
        print(f"   ✅ Found {len(graph_facts)} graph facts")
        
        if graph_facts:
            print(f"   📊 Sample facts:")
            for i, fact in enumerate(graph_facts[:3], 1):
                print(f"      {i}. {fact.get('text', '')[:80]}...")

        # STEP 8: Synthesis
        print(f"\n🤖 STEP 8: ANSWER SYNTHESIS")
        print(f"   📝 Generating comprehensive answer...")
        print(f"   📊 Context: {len(ctx)} chunks")
        print(f"   🕸️ Graph facts: {len(graph_facts)}")
        print(f"   🎯 Using ULTRA-POWERFUL synthesis prompts...")
        
        result = await self._synthesize_powerful(query, ctx, graph_facts)
        
        answer_len = len(result.get('answer', ''))
        sources_len = len(result.get('sources', []))
        
        print(f"\n✅ ANSWER GENERATED!")
        print(f"   📏 Answer length: {answer_len} characters ({answer_len // 5} words)")
        print(f"   📚 Sources cited: {sources_len}")
        print(f"   🕸️ Graph facts used: {result.get('graph_facts_used', 0)}")
        
        # Show answer preview
        answer_preview = result.get('answer', '')[:200]
        print(f"\n   📖 Answer preview:")
        print(f"   {answer_preview}...")
        
        print("\n" + "="*80)
        print("✅ QUERY COMPLETE - ULTRA-POWERFUL ANSWER DELIVERED!")
        print("="*80 + "\n")
        
        return result

    async def _embed_openai(self, text: str) -> List[float]:
        """
        🔥 FIXED: Generate OpenAI embedding with CONSISTENT model
        CRITICAL: Must match ingestion model (text-embedding-3-small = 1536 dims)
        """
        # FORCE consistent model - ignore config to prevent dimension mismatch
        embedding_model = "text-embedding-3-small"  # 1536 dimensions
        
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"input": text, "model": embedding_model},  # FIXED: Use consistent model
            )
            r.raise_for_status()
            embedding = r.json()["data"][0]["embedding"]
            
            # Verify dimension
            if len(embedding) != 1536:
                print(f"   ⚠️ WARNING: Unexpected embedding dimension: {len(embedding)}, expected 1536")
            
            return embedding

    async def _ensure_clip(self) -> ImageEmbedder | None:
        """Lazy-load CLIP once"""
        if self._clip_model is not None:
            return self._clip_model
        try:
            self._clip_model = ImageEmbedder()
            if not self._clip_model.ok:
                self._clip_model = None
        except Exception:
            self._clip_model = None
        return self._clip_model

    async def _synthesize_powerful(self, query: str, ctx: List[Dict[str, Any]], facts: List[Dict[str, Any]]):
        """
        ULTRA-POWERFUL synthesis with:
        - FULL TEXT (no truncation!)
        - Top 20 chunks
        - Expert-level prompts
        """
        
        if not ctx and not facts:
            print("   ⚠️ No context or facts available")
            return {
                "type": "general", 
                "answer": "I couldn't find sufficient information in the documents or knowledge graph to answer this question.", 
                "sources": [],
                "graph_facts_used": 0
            }

        # Build citations with FULL TEXT
        print(f"   📝 Building context from {len(ctx[:20])} chunks...")
        cites = []
        sources_for_response = []
        
        for idx, h in enumerate(ctx[:20], 1):  # Top 20 chunks
            p = h.get("payload", {})
            
            doc_id = p.get("doc_id", "unknown")
            filename = p.get("filename", "Unknown")
            page = p.get("page", 0)
            score = h.get("score", 0.0)
            is_diagram = p.get("is_diagram", False)
            text = p.get("text", "")
            section = p.get("section", "")
            
            # Format with FULL TEXT (NO TRUNCATION!)
            doc_type = "📐 DIAGRAM" if is_diagram else "📄 TEXT"
            section_label = f" | Section: {section}" if section else ""
            
            cites.append(
                f"{doc_type} Source {idx} | {filename} | Page {page}{section_label} | Score: {score:.2f}\n"
                f"Content: {text}\n"  # FULL TEXT!
                f"{'='*80}\n"
            )
            
            sources_for_response.append({
                "doc_id": doc_id,
                "filename": filename,
                "page": page,
                "score": float(score),
                "is_diagram": is_diagram,
                "section": section,
                "modality": p.get("modality", "text"),
            })
        
        print(f"   ✅ Context built: {sum(len(c) for c in cites)} characters")

        # Enhanced graph facts
        facts_txt = "=" * 80 + "\n"
        facts_txt += "KNOWLEDGE GRAPH CONNECTIONS:\n"
        facts_txt += "=" * 80 + "\n"
        for f in (facts or [])[:30]:
            facts_txt += f"• {f.get('text', '')}\n"
        facts_txt += "=" * 80 + "\n"

        context_txt = "\n".join(cites)
        
        print(f"   🎯 Preparing ULTRA-POWERFUL synthesis prompt...")

        # ULTRA-POWERFUL SYSTEM PROMPT
        system = (
            "You are THE WORLD'S LEADING construction document expert with deep specialization in MEP systems, "
            "structural engineering, and technical specifications.\n\n"
            
            "CORE COMPETENCIES:\n"
            "• Master-level understanding of HVAC, electrical, plumbing, and fire protection systems\n"
            "• Expert in reading construction drawings, specifications, and equipment schedules\n"
            "• Specialized knowledge of equipment tags, nomenclature, and abbreviations\n"
            "• Deep familiarity with installation requirements and code compliance\n\n"
            
            "CRITICAL RESPONSE REQUIREMENTS:\n"
            "1. READ THOROUGHLY: You have access to EXTENSIVE context - use ALL of it\n"
            "2. BE EXHAUSTIVE: Extract EVERY relevant detail - equipment tags, specs, locations, connections\n"
            "3. SYNTHESIZE INTELLIGENTLY: Connect information across multiple sources\n"
            "4. CITE METICULOUSLY: Reference sources with exact format: (Source: filename, Page N)\n"
            "5. ANSWER DIRECTLY: Start with the answer, then provide supporting details\n"
            "6. BE SPECIFIC: Use exact equipment tags (e.g., 'AHU-3', not 'an air handler')\n"
            "7. INCLUDE CONTEXT: Don't just list - explain relationships and purposes\n\n"
            
            "FOR EQUIPMENT QUESTIONS:\n"
            "• State equipment tag, type, and model if available\n"
            "• Provide location (room, floor, zone)\n"
            "• List key specifications (CFM, voltage, capacity, etc.)\n"
            "• Describe connections and what it serves\n"
            "• Note any special installation requirements\n\n"
            
            "FOR CONNECTION/RELATIONSHIP QUESTIONS:\n"
            "• Map complete connection chains (A → B → C)\n"
            "• Specify connection types (ductwork, piping, electrical)\n"
            "• Include sizes, capacities, and flow directions\n\n"
            
            "FOR LOCATION QUESTIONS:\n"
            "• Give precise location (building, floor, room number)\n"
            "• Provide zone/area designations\n"
            "• Reference relevant drawings\n\n"
            
            "IF INFORMATION IS PARTIAL:\n"
            "• State EXACTLY what you found (with sources)\n"
            "• Specify EXACTLY what's missing\n"
            "• Suggest where additional info might be found\n"
            "• NEVER say 'insufficient information' if ANY relevant info exists\n\n"
            
            "Remember: You have access to EXTENSIVE documentation. Use it ALL!"
        )
        
        user = (
            f"{'='*80}\n"
            f"QUESTION:\n"
            f"{'='*80}\n"
            f"{query}\n\n"
            f"{facts_txt}\n\n"
            f"{'='*80}\n"
            f"DOCUMENT CONTEXT (20 sources with FULL TEXT):\n"
            f"{'='*80}\n"
            f"{context_txt}\n\n"
            f"Provide a COMPREHENSIVE answer with specific details and citations."
        )

        print(f"   🔄 Calling OpenAI GPT-4o for synthesis...")
        
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "temperature": 0.35,  # INCREASED for better reasoning
                    "max_tokens": 2000,  # INCREASED for longer answers
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]

        print(f"   ✅ Synthesis complete: {len(text)} characters")

        return {
            "type": "general", 
            "answer": text, 
            "sources": sources_for_response,
            "graph_facts_used": len(facts or [])
        }
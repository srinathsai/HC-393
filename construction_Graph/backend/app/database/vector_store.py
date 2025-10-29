from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any
import logging

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    UNIFIED ChromaDB client - ensures single instance across all services.
    """
    
    def __init__(self, persist_directory: str | None = None, collection_name: str = "construction_docs"):
        """
        Initialize ChromaDB with centralized configuration.
        
        Args:
            persist_directory: Optional override. If None, uses centralized config.
            collection_name: Name of the collection to use.
        """
        # CRITICAL: Use centralized config if no directory specified
        if persist_directory is None:
            from app.config import get_chroma_directory
            persist_directory = get_chroma_directory()
        
        # Ensure directory is absolute path
        self.persist_directory = str(Path(persist_directory).resolve())
        
        # Create directory if doesn't exist
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client (persistent)
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    persist_directory=self.persist_directory,
                    is_persistent=True,
                ),
            )
        except TypeError:
            # Fallback for older ChromaDB versions
            self.client = chromadb.PersistentClient(path=self.persist_directory)

        self.collection_name = collection_name

        # Get or create collection (cosine distance)
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(
                f"✓ Connected to existing collection '{collection_name}' at {self.persist_directory}"
            )
        except Exception:
            self.collection = self.client.get_or_create_collection(
                name=collection_name, metadata={"hnsw:space": "cosine"}
            )
            logger.info(
                f"✓ Created new collection '{collection_name}' at {self.persist_directory}"
            )

        # Log startup status
        try:
            count = self.collection.count()
            logger.info(f"[vector_store] dir={self.persist_directory} count={count}")
        except Exception as e:
            logger.warning(f"[vector_store] count check failed: {e}")

    # ------------------------ Write ------------------------

    def upsert_vectors(self, chunks: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """
        Upsert vectors with metadata to ChromaDB.
        
        chunks: [{ id, vector (list[float]), payload{doc_id, filename, page, chunk_index, text, is_diagram} }]
        """
        if not chunks:
            logger.warning("No chunks to upsert")
            return 0

        total = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            ids, embeddings, documents, metadatas = [], [], [], []

            for c in batch:
                try:
                    cid = str(c.get("id") or "")
                    vec = c.get("vector") or []
                    meta = c.get("payload") or {}
                    
                    if not cid or not vec:
                        continue
                    
                    ids.append(cid)
                    embeddings.append(vec)
                    documents.append(str(meta.get("text", ""))[:2000])
                    
                    # CRITICAL: Extract metadata properly
                    metadatas.append(
                        {
                            "doc_id": str(meta.get("doc_id", "")),
                            "filename": str(meta.get("filename", "")),
                            "page": int(meta.get("page", 0)),
                            "chunk_index": int(meta.get("chunk_index", 0)),
                            "is_diagram": bool(meta.get("is_diagram", False)),
                        }
                    )
                except Exception as e:
                    logger.error(f"Prep error for id={c.get('id')}: {e}")

            if ids:
                try:
                    self.collection.upsert(
                        ids=ids,
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                    )
                    total += len(ids)
                    logger.info(f"✓ Upserted {len(ids)} vectors (batch {i//batch_size+1})")
                except Exception as e:
                    logger.error(f"Upsert batch failed: {e}")

        # Force persist (for older ChromaDB versions)
        try:
            self.client.persist()
            logger.info(f"✓ Persisted to {self.persist_directory}")
        except Exception:
            pass

        return total

    def search_vectors(
        self, query_vector: List[float], top_k: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Search vectors and return results with metadata.
        """
        try:
            results = self.collection.query(query_embeddings=[query_vector], n_results=top_k)
            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0] if results.get("distances") else []
            
            scores = [float(d) for d in distances] if distances else [0.0] * len(ids)

            out = []
            for i, cid in enumerate(ids):
                md = metas[i] if i < len(metas) else {}
                out.append(
                    {
                        "id": cid,
                        "score": scores[i] if i < len(scores) else 0.0,
                        "payload": {
                            "text": docs[i] if i < len(docs) else "",
                            "doc_id": md.get("doc_id", ""),
                            "filename": md.get("filename", ""),
                            "page": md.get("page", 0),
                            "chunk_index": md.get("chunk_index", 0),
                            "is_diagram": md.get("is_diagram", False),
                        },
                    }
                )
            return out

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            return {
                "total_vectors": self.collection.count(),
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {
                "total_vectors": 0,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
            }

    def delete_document(self, doc_id: str) -> bool:
        """Delete all vectors for a document"""
        try:
            results = self.collection.get(where={"doc_id": doc_id})
            if results and results.get("ids"):
                self.collection.delete(ids=results["ids"])
                logger.info(f"✅ Deleted {len(results['ids'])} vectors for doc_id={doc_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return False
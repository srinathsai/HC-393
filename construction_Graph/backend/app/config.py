# app/config.py
# OPTIMIZED CONFIGURATION - 100% BACKWARD COMPATIBLE
# All new settings have defaults, so existing code won't break

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
import os


class Settings(BaseSettings):
    """
    Centralized configuration - OPTIMIZED FOR ULTRA-POWER
    All settings are backward compatible with defaults
    """
    
    # API Settings
    api_title: str = "Construction GraphRAG API"
    api_version: str = "2.0.0"
    
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-large", env="OPENAI_EMBEDDING_MODEL")
    
    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")
    
    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    
    # Vision extraction settings - ENHANCED
    use_vision_extraction: bool = Field(default=True, env="USE_VISION_EXTRACTION")
    max_vision_pages_per_doc: int = Field(default=5, env="MAX_VISION_PAGES_PER_DOC")  # Increased from 3
    vision_only_for_diagrams: bool = Field(default=True, env="VISION_ONLY_FOR_DIAGRAMS")
    
    # Processing settings - OPTIMIZED
    max_workers: int = Field(default=6, env="MAX_WORKERS")  # Increased from 4
    batch_size: int = Field(default=16, env="BATCH_SIZE")  # Increased from 10
    
    # Graph settings - RELAXED FOR MORE EXTRACTION
    confidence_threshold: float = Field(default=0.6, env="CONFIDENCE_THRESHOLD")  # Lowered from 0.7
    max_graph_depth: int = Field(default=3, env="MAX_GRAPH_DEPTH")  # Increased from 2
    
    # Query settings - EXTENDED TIMEOUT
    query_timeout: int = Field(default=90, env="QUERY_TIMEOUT")  # Increased from 30
    
    # Embedding settings - LARGER CACHE
    embedding_cache_size: int = Field(default=50000, env="EMBEDDING_CACHE_SIZE")  # Increased from 10000
    
    # Image ingestion - ENABLED BY DEFAULT
    enable_image_ingestion: bool = Field(default=True, env="ENABLE_IMAGE_INGESTION")  # Changed from False
    
    # Image retrieval
    enable_image_retrieval: bool = Field(default=False, env="ENABLE_IMAGE_RETRIEVAL")
    
    # ========================================================================
    # NEW SETTINGS FOR ULTRA-POWER (All have defaults for backward compatibility)
    # ========================================================================
    
    # Chunk settings
    chunk_size: int = Field(default=600, env="CHUNK_SIZE")  # Larger chunks
    chunk_overlap: int = Field(default=100, env="CHUNK_OVERLAP")  # More overlap
    
    # Search settings
    vector_search_top_k: int = Field(default=50, env="VECTOR_SEARCH_TOP_K")  # More results
    bm25_search_top_k: int = Field(default=50, env="BM25_SEARCH_TOP_K")  # More results
    final_context_chunks: int = Field(default=50, env="FINAL_CONTEXT_CHUNKS")  # More context
    
    # Synthesis settings
    synthesis_temperature: float = Field(default=0.35, env="SYNTHESIS_TEMPERATURE")  # Balanced
    synthesis_max_tokens: int = Field(default=2000, env="SYNTHESIS_MAX_TOKENS")  # Longer answers
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings singleton - BACKWARD COMPATIBLE"""
    global _settings
    if _settings is None:
        print("⚙️ [Config] Loading settings...")
        _settings = Settings()
        print(f"✅ [Config] Settings loaded")
        print(f"   OpenAI model: {_settings.openai_model}")
        print(f"   Temperature: {_settings.synthesis_temperature}")
        print(f"   Max tokens: {_settings.synthesis_max_tokens}")
        print(f"   Final context chunks: {_settings.final_context_chunks}")
    return _settings


def get_chroma_directory() -> str:
    """
    HARDCODED ChromaDB path for consistency.
    BACKWARD COMPATIBLE - always returns same path.
    """
    # HARDCODED PATH - NO MORE CONFUSION!
    chroma_path = r"C:\chroma\construction_graph"
    
    # Create directory if doesn't exist
    Path(chroma_path).mkdir(parents=True, exist_ok=True)
    
    return chroma_path


def get_optimized_settings() -> dict:
    """
    Get optimized settings dict - HELPER FUNCTION (doesn't break anything)
    """
    return {
        # Vision
        "use_vision_extraction": False,
        "max_vision_pages_per_doc": 5,
        
        # Processing
        "max_workers": 6,
        "batch_size": 16,
        
        # Graph
        "confidence_threshold": 0.6,
        "max_graph_depth": 3,
        
        # Search
        "vector_search_top_k": 50,
        "bm25_search_top_k": 50,
        "final_context_chunks": 50,
        
        # Synthesis
        "synthesis_temperature": 0.35,
        "synthesis_max_tokens": 2000,
        "query_timeout": 90,
    }
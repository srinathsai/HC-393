from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class DocumentUploadResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    message: str


class QueryRequest(BaseModel):
    question: str
    max_results: int = 10
    filters: Optional[Dict[str, Any]] = None


class Source(BaseModel):
    doc_id: str
    page: int
    bbox: Optional[List[float]] = None
    text: str


class QueryResponse(BaseModel):
    answer: str
    query_type: str
    execution_time_ms: float
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    sources: List[Source] = []


class PerformanceMetrics(BaseModel):
    total_documents: int
    total_nodes: int
    total_relationships: int
    avg_query_time_ms: float
    ingestion_rate_docs_per_min: float
    accuracy_score: float


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MultipleUploadResponse(BaseModel):
    total_files: int
    successful: int
    failed: int
    job_ids: List[str]
    details: List[Dict[str, str]]
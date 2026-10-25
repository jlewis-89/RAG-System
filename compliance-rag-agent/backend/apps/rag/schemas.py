"""
Pydantic v2 Schemas for Engineering Compliance RAG System.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ComplianceVerdict(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class CitationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    standard_code: str = Field(..., description="Standard identifier e.g. ISO-9001, ASME-VIII")
    clause: str = Field(default="N/A", description="Specific clause, section, or paragraph")
    source: str = Field(..., description="Document source title or file name")
    snippet: str = Field(..., description="Text excerpt used as compliance evidence")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Normalized similarity or relevance score")


class RAGQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=3, max_length=2000, description="Compliance query or engineering requirement to audit")
    standard_codes: Optional[List[str]] = Field(default=None, description="Optional filter by standard codes (e.g. ['ISO-9001', 'ASME-VIII'])")
    top_k: int = Field(default=4, ge=1, le=20, description="Number of evidence chunks to retrieve from ChromaDB")
    strict_mode: bool = Field(default=True, description="Strict compliance verification requiring explicit clause citations")


class RAGQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: str
    verdict: ComplianceVerdict
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    summary: str
    detailed_findings: str
    citations: List[CitationItem] = Field(default_factory=list)
    audit_id: Optional[int] = None
    latency_ms: float
    timestamp: str


class DocumentIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=2, max_length=255)
    standard_code: str = Field(..., min_length=2, max_length=64)
    content: str = Field(..., min_length=10, description="Full text or section content of the engineering standard")
    source_identifier: str = Field(default="manual_entry", max_length=255)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentIngestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    title: str
    standard_code: str
    total_chunks: int
    status: str
    message: str


class StandardCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=3, max_length=255)
    authority: str = Field(default="ISO", max_length=128)
    version: Optional[str] = Field(default=None, max_length=32)
    description: Optional[str] = Field(default="")


class HealthCheckResponse(BaseModel):
    status: str
    chroma_status: str
    chroma_collection: str
    chroma_items_count: int
    database_status: str
    version: str

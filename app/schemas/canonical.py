"""Canonical document, chunk, evidence, and search schemas for RFP Intelligence Platform."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TableBlock(BaseModel):
    """Structured representation of an extracted table."""

    table_id: str
    page_number: int
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    raw_markdown: str = ""


class DocumentPage(BaseModel):
    """Canonical representation of a single document page."""

    page_number: int
    text: str = ""
    tables: List[TableBlock] = Field(default_factory=list)
    is_suspicious_or_empty: bool = False
    page_warnings: List[str] = Field(default_factory=list)
    extraction_method: str = "text"  # "text" or "ocr"
    ocr_confidence: Optional[float] = None


class DocumentMetadata(BaseModel):
    """Metadata attached to an ingested document."""

    bid_id: str
    file_name: str
    doc_type: str  # rfp, addendum, specs, affidavit, bid_page, other
    addendum_number: Optional[int] = None
    document_date: Optional[str] = None
    source_path: str
    file_size_bytes: Optional[int] = None
    file_hash: Optional[str] = None
    title: Optional[str] = None
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Canonical representation of an ingested document."""

    metadata: DocumentMetadata
    pages: List[DocumentPage] = Field(default_factory=list)
    raw_text_length: int = 0
    page_count: int = 0


class ClassificationResult(BaseModel):
    """Result of classifying a document."""

    doc_type: str
    confidence: float
    reason: str
    addendum_number: Optional[int] = None
    document_date: Optional[str] = None


class IngestionError(BaseModel):
    """Error encountered during ingestion of a document or page."""

    file_path: str
    page_number: Optional[int] = None
    error_type: str
    message: str


class IngestionWarning(BaseModel):
    """Warning encountered during ingestion of a document or page."""

    file_path: str
    page_number: Optional[int] = None
    warning_type: str
    message: str


class IngestionResult(BaseModel):
    """Complete result of ingesting a bid folder."""

    bid_id: str
    documents: List[Document] = Field(default_factory=list)
    warnings: List[IngestionWarning] = Field(default_factory=list)
    errors: List[IngestionError] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


# ==========================================
# PHASE 2 SCHEMAS: CITATION, EVIDENCE, CHUNK
# ==========================================


class Citation(BaseModel):
    """Source provenance citation pointing to an exact document location."""

    file_name: str
    page_number: int
    chunk_id: str
    text: str = ""
    bid_id: str = ""
    section: Optional[str] = None
    document_type: Optional[str] = None
    addendum_number: Optional[int] = None

    @property
    def file(self) -> str:
        return self.file_name

    @property
    def page(self) -> int:
        return self.page_number


class Evidence(BaseModel):
    """Concrete source passage supporting an extracted fact or answer."""

    bid_id: str
    file_name: str
    page_number: int
    chunk_id: str
    text: str
    document_type: str
    section: Optional[str] = None
    addendum_number: Optional[int] = None
    document_date: Optional[str] = None
    chunk_type: Optional[str] = "text"
    score: Optional[float] = None
    rank: Optional[int] = None
    retrieval_source: Optional[str] = None

    @property
    def file(self) -> str:
        return self.file_name

    @property
    def page(self) -> int:
        return self.page_number

    def to_citation(self) -> Citation:
        """Convert evidence into a concrete Citation instance."""
        return Citation(
            bid_id=self.bid_id,
            file_name=self.file_name,
            page_number=self.page_number,
            chunk_id=self.chunk_id,
            text=self.text[:300] if self.text else "",
            section=self.section,
            document_type=self.document_type,
            addendum_number=self.addendum_number,
        )


class Chunk(BaseModel):
    """Retrieval-ready content chunk with complete provenance and metadata."""

    chunk_id: str
    bid_id: str
    file_name: str
    document_type: str
    page_number: int
    section: Optional[str] = None
    addendum_number: Optional[int] = None
    text: str
    chunk_type: str = "text"  # text, table, mixed
    token_count: int = 0
    source_order: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_evidence(
        self,
        score: Optional[float] = None,
        rank: Optional[int] = None,
        retrieval_source: Optional[str] = None,
    ) -> Evidence:
        """Convert chunk into a concrete Evidence instance."""
        return Evidence(
            bid_id=self.bid_id,
            file_name=self.file_name,
            page_number=self.page_number,
            chunk_id=self.chunk_id,
            text=self.text,
            document_type=self.document_type,
            section=self.section,
            addendum_number=self.addendum_number,
            document_date=self.metadata.get("document_date"),
            chunk_type=self.chunk_type,
            score=score,
            rank=rank,
            retrieval_source=retrieval_source,
        )

    def to_citation(self) -> Citation:
        """Convert chunk into a concise Citation instance."""
        return Citation(
            bid_id=self.bid_id,
            file_name=self.file_name,
            page_number=self.page_number,
            chunk_id=self.chunk_id,
            text=self.text[:300] if self.text else "",
            section=self.section,
            document_type=self.document_type,
            addendum_number=self.addendum_number,
        )


class FieldResult(BaseModel):
    """Extracted field value backed by source citations and confidence."""

    value: Optional[Any] = None
    sources: List[Citation] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: Optional[str] = "Not found in documents."
    reason: Optional[str] = None



# ==========================================
# PHASE 4 SCHEMAS: SEARCH & HYBRID RETRIEVAL
# ==========================================


class SearchFilters(BaseModel):
    """Metadata filters for dense, BM25, and hybrid search."""

    bid_id: Optional[str] = None
    document_type: Optional[str] = None
    addendum_number: Optional[int] = None
    file_name: Optional[str] = None


class SearchResult(BaseModel):
    """Ranked search candidate returned by retrieval, with optional reranking annotations."""

    rank: int
    chunk_id: str
    text: str
    score: float
    retrieval_source: str  # dense, bm25, hybrid, hybrid+rerank
    evidence: Evidence
    rerank_score: Optional[float] = None
    previous_score: Optional[float] = None
    rerank_rank: Optional[int] = None



class SearchResponse(BaseModel):
    """Complete structured response from the search engine."""

    query: str
    total_results: int
    results: List[SearchResult] = Field(default_factory=list)
    retrieval_metadata: Dict[str, Any] = Field(default_factory=dict)

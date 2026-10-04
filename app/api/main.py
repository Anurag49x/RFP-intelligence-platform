"""FastAPI application initialization and routes for RFP Intelligence Platform."""

from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import get_settings
from app.extraction.schemas import BidOutput
from app.graph.runner import RFPExtractionPipeline
from app.indexing.service import IndexingReport, IndexingService
from app.qa.engine import QAEngine
from app.qa.models import AskRequest, AskResponse
from app.retrieval.hybrid import HybridSearchEngine
from app.schemas.canonical import SearchFilters, SearchResponse

settings = get_settings()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="RFP Intelligence Platform",
    description="RAG Search Engine & Multi-Agent System for Procurement & RFPs",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IndexRequest(BaseModel):
    """Request model for document indexing endpoint."""

    folder_path: str
    bid_id: Optional[str] = None


class ExtractRequest(BaseModel):
    """Request model for structured bid extraction endpoint."""

    bid_id: str



class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    query: str
    top_k: int = 5
    filters: Optional[SearchFilters] = None
    use_reranker: bool = True
    dense_top_k: Optional[int] = None
    bm25_top_k: Optional[int] = None


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint to verify service and configuration status."""
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "version": "0.1.0",
    }


@app.post("/index", response_model=IndexingReport, tags=["Indexing"])
async def index_documents(request: IndexRequest):
    """Index an RFP/bid folder through the full ingestion -> chunking -> vector & BM25 pipeline."""
    try:
        service = IndexingService()
        report = service.index_folder(folder_path=request.folder_path, bid_id=request.bid_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_post(request: SearchRequest):
    """Search indexed documents using hybrid Dense + BM25 + Reciprocal Rank Fusion + Jina Reranking."""
    try:
        engine = HybridSearchEngine()
        response = engine.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            use_reranker=request.use_reranker,
            dense_top_k=request.dense_top_k,
            bm25_top_k=request.bm25_top_k,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/search", response_model=SearchResponse, tags=["Search"])
async def search_get(
    q: str = Query(..., description="Search query string"),
    bid_id: Optional[str] = Query(None, description="Filter by bid ID"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    addendum_number: Optional[int] = Query(None, description="Filter by addendum number"),
    file_name: Optional[str] = Query(None, description="Filter by file name"),
    top_k: int = Query(5, ge=1, le=50, description="Max results to return"),
    use_reranker: bool = Query(True, description="Enable Jina listwise reranker"),
):
    """GET endpoint for hybrid search with query parameters."""
    try:
        filters = SearchFilters(
            bid_id=bid_id,
            document_type=doc_type,
            addendum_number=addendum_number,
            file_name=file_name,
        )
        engine = HybridSearchEngine()
        response = engine.search(
            query=q,
            top_k=top_k,
            filters=filters,
            use_reranker=use_reranker,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/extract", response_model=BidOutput, tags=["Extraction"])
async def extract_bid(request: ExtractRequest):
    """Extract 20 canonical structured fields for a bid using LangGraph multi-agent workflow."""
    try:
        pipeline = RFPExtractionPipeline()
        output = pipeline.extract_bid(bid_id=request.bid_id)
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.post("/ask", response_model=AskResponse, tags=["Q&A"])
async def ask_question(request: AskRequest):
    """Answer natural language procurement questions with verifiable citations and evidence support."""
    try:
        engine = QAEngine()
        response = engine.answer_question(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {str(e)}")




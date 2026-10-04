"""Hybrid Search Engine combining dense semantic search, BM25 lexical search, RRF, and Jina Reranking."""

import time
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.jina import JinaEmbeddingProvider
from app.lexical.bm25 import BM25Index
from app.logging import logger
from app.rerankers.base import RerankerProvider
from app.rerankers.jina import JinaRerankerProvider
from app.retrieval.rrf import reciprocal_rank_fusion
from app.schemas.canonical import SearchFilters, SearchResponse, SearchResult
from app.vectorstore.base import VectorStore
from app.vectorstore.qdrant import QdrantVectorStore


class HybridSearchEngine:
    """Production hybrid retrieval engine unifying Dense, BM25, Reciprocal Rank Fusion, and Reranking."""

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
        bm25_index: Optional[BM25Index] = None,
        reranker: Optional[RerankerProvider] = None,
        collection_name: str = "rfp_chunks",
    ):
        settings = get_settings()
        self.embedding_provider = embedding_provider or JinaEmbeddingProvider()
        self.vector_store = vector_store or QdrantVectorStore()
        self.bm25_index = bm25_index or BM25Index()
        self.reranker = reranker or JinaRerankerProvider()
        self.collection_name = collection_name
        self.default_dense_top_k = settings.dense_top_k
        self.default_bm25_top_k = settings.bm25_top_k
        self.default_rerank_top_k = settings.rerank_top_k

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[SearchFilters] = None,
        use_reranker: bool = True,
        dense_top_k: Optional[int] = None,
        bm25_top_k: Optional[int] = None,
        rrf_k: int = 60,
    ) -> SearchResponse:
        """Perform hybrid search with candidate generation and optional listwise reranking."""
        clean_query = query.strip()
        if not clean_query:
            return SearchResponse(query="", total_results=0, results=[], retrieval_metadata={})

        dense_k = dense_top_k or self.default_dense_top_k
        bm25_k = bm25_top_k or self.default_bm25_top_k

        start_time = time.time()
        dense_results: List[SearchResult] = []
        dense_latency_ms = 0.0

        # 1. Dense Semantic Retrieval Branch
        dense_start = time.time()
        try:
            query_vector = self.embedding_provider.embed_query(clean_query)
            dense_results = self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                top_k=dense_k,
                filters=filters,
            )
            dense_latency_ms = (time.time() - dense_start) * 1000.0
            logger.info(f"Dense search found {len(dense_results)} candidates in {dense_latency_ms:.1f}ms")
        except Exception as e:
            logger.warning(f"Dense retrieval branch error: {str(e)}. Continuing with BM25 fallback.")
            dense_latency_ms = (time.time() - dense_start) * 1000.0

        # 2. BM25 Lexical Retrieval Branch
        bm25_start = time.time()
        bm25_results: List[SearchResult] = []
        try:
            bm25_results = self.bm25_index.search(
                query=clean_query,
                top_k=bm25_k,
                filters=filters,
            )
            bm25_latency_ms = (time.time() - bm25_start) * 1000.0
            logger.info(f"BM25 search found {len(bm25_results)} candidates in {bm25_latency_ms:.1f}ms")
        except Exception as e:
            logger.warning(f"BM25 retrieval branch error: {str(e)}")
            bm25_latency_ms = (time.time() - bm25_start) * 1000.0

        # 3. Reciprocal Rank Fusion (Candidate Pool Generation)
        rrf_start = time.time()
        candidate_lists = []
        if dense_results:
            candidate_lists.append(dense_results)
        if bm25_results:
            candidate_lists.append(bm25_results)

        candidate_pool_size = max(dense_k, bm25_k, top_k * 4)
        rrf_candidates = reciprocal_rank_fusion(
            ranked_lists=candidate_lists,
            rrf_k=rrf_k,
            top_k=candidate_pool_size,
        )
        rrf_latency_ms = (time.time() - rrf_start) * 1000.0

        # 4. Second-Stage Reranking (Phase 5)
        rerank_start = time.time()
        rerank_latency_ms = 0.0
        reranking_status = "disabled"
        final_results: List[SearchResult] = []

        if use_reranker and self.reranker and rrf_candidates:
            try:
                final_results = self.reranker.rerank(
                    query=clean_query,
                    candidates=rrf_candidates,
                    top_k=top_k,
                )
                rerank_latency_ms = (time.time() - rerank_start) * 1000.0
                reranking_status = "success"
                logger.info(
                    f"Reranking completed successfully in {rerank_latency_ms:.1f}ms, returning {len(final_results)} items"
                )
            except Exception as e:
                rerank_latency_ms = (time.time() - rerank_start) * 1000.0
                reranking_status = "failed"
                logger.warning(
                    f"Reranking failed ({str(e)}). Falling back to top {top_k} RRF hybrid candidates."
                )
                final_results = rrf_candidates[:top_k]
        else:
            if not use_reranker:
                reranking_status = "disabled"
            elif not rrf_candidates:
                reranking_status = "skipped"
            final_results = rrf_candidates[:top_k]

        total_latency_ms = (time.time() - start_time) * 1000.0

        metadata: Dict[str, Any] = {
            "dense_candidates_count": len(dense_results),
            "bm25_candidates_count": len(bm25_results),
            "rrf_candidates_count": len(rrf_candidates),
            "final_results_count": len(final_results),
            "reranking_status": reranking_status,
            "reranker_model": self.reranker.model_name if (use_reranker and self.reranker) else None,
            "dense_latency_ms": round(dense_latency_ms, 2),
            "bm25_latency_ms": round(bm25_latency_ms, 2),
            "rrf_latency_ms": round(rrf_latency_ms, 2),
            "rerank_latency_ms": round(rerank_latency_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "applied_filters": filters.model_dump(exclude_none=True) if filters else {},
        }

        logger.info(
            f"Search complete for query='{clean_query[:50]}' -> {len(final_results)} results "
            f"in {total_latency_ms:.1f}ms (dense={len(dense_results)}, bm25={len(bm25_results)}, rerank={reranking_status})"
        )

        return SearchResponse(
            query=clean_query,
            total_results=len(final_results),
            results=final_results,
            retrieval_metadata=metadata,
        )

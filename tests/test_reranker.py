"""Tests for Phase 5: Jina Reranking Provider and HybridSearchEngine Integration."""

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.embeddings.base import EmbeddingProvider
from app.lexical.bm25 import BM25Index
from app.rerankers.base import RerankerProvider
from app.rerankers.jina import JinaRerankerProvider
from app.retrieval.hybrid import HybridSearchEngine
from app.schemas.canonical import Chunk, Evidence, SearchFilters, SearchResult
from app.vectorstore.qdrant import QdrantVectorStore


class MockRerankerProvider(RerankerProvider):
    """Deterministic mock reranker provider reversing or scoring candidates for testing."""

    def __init__(self, model_name: str = "mock-reranker-v3.5"):
        self._model_name = model_name
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return self._model_name

    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 5,
    ) -> List[SearchResult]:
        self.call_count += 1
        if not candidates or not query.strip():
            return []

        # Deduplicate candidates by chunk_id
        seen = set()
        deduped = []
        for c in candidates:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                deduped.append(c)

        # Reverse order to simulate a meaningful reranking shift
        reversed_candidates = list(reversed(deduped))[:top_k]
        results = []
        for new_rank, orig in enumerate(reversed_candidates, start=1):
            score = 0.99 - (new_rank * 0.1)
            ev = orig.evidence
            updated_ev = Evidence(
                bid_id=ev.bid_id,
                file_name=ev.file_name,
                page_number=ev.page_number,
                chunk_id=ev.chunk_id,
                text=ev.text,
                document_type=ev.document_type,
                section=ev.section,
                addendum_number=ev.addendum_number,
                document_date=ev.document_date,
                chunk_type=ev.chunk_type,
                score=score,
                rank=new_rank,
                retrieval_source=f"{ev.retrieval_source or orig.retrieval_source}+rerank",
            )
            results.append(
                SearchResult(
                    rank=new_rank,
                    chunk_id=orig.chunk_id,
                    text=orig.text,
                    score=score,
                    retrieval_source="hybrid+rerank",
                    evidence=updated_ev,
                    rerank_score=score,
                    previous_score=orig.score,
                    rerank_rank=new_rank,
                )
            )
        return results


def _make_candidate(chunk_id: str, text: str, score: float, rank: int) -> SearchResult:
    ev = Evidence(
        bid_id="Bid1",
        file_name="rfp.pdf",
        page_number=rank,
        chunk_id=chunk_id,
        text=text,
        document_type="rfp",
        section=f"Section {rank}",
        score=score,
        rank=rank,
        retrieval_source="hybrid",
    )
    return SearchResult(
        rank=rank,
        chunk_id=chunk_id,
        text=text,
        score=score,
        retrieval_source="hybrid",
        evidence=ev,
    )


def test_jina_reranker_top_k_and_empty():
    """Verify empty query or candidates returns empty list."""
    provider = JinaRerankerProvider(api_key="test-key")
    assert provider.rerank(query="", candidates=[_make_candidate("c1", "t1", 0.9, 1)]) == []
    assert provider.rerank(query="dell", candidates=[]) == []


def test_jina_reranker_deduplication_and_provenance():
    """Verify duplicates are deduped by chunk_id and provenance is mapped properly."""
    provider = JinaRerankerProvider(api_key="test-key")
    c1 = _make_candidate("chk_1", "Text about Dell 5550", 0.03, 1)
    c2 = _make_candidate("chk_2", "Text about Lenovo", 0.02, 2)
    c1_dup = _make_candidate("chk_1", "Duplicate Text", 0.01, 3)

    mock_api_response = [
        {"index": 0, "document": {"text": "Text about Dell 5550"}, "relevance_score": 0.95},
        {"index": 1, "document": {"text": "Text about Lenovo"}, "relevance_score": 0.40},
    ]

    with patch.object(provider, "_call_api", return_value=mock_api_response) as mock_call:
        results = provider.rerank("Dell laptop", [c1, c2, c1_dup], top_k=5)

        # Should only pass 2 unique documents to API
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args
        assert kwargs["documents"] == ["Text about Dell 5550", "Text about Lenovo"]
        assert kwargs["top_n"] == 2

        assert len(results) == 2
        assert results[0].chunk_id == "chk_1"
        assert results[0].score == 0.95
        assert results[0].rerank_score == 0.95
        assert results[0].previous_score == 0.03
        assert results[0].evidence.chunk_id == "chk_1"
        assert "rerank" in results[0].evidence.retrieval_source


def test_jina_reranker_retries_on_transient_error():
    """Verify exponential backoff retries on 429 / 503 HTTP responses."""
    provider = JinaRerankerProvider(api_key="test-key", max_retries=3, initial_backoff=0.01)

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.text = "Rate limit reached"

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "results": [{"index": 0, "relevance_score": 0.88}]
    }

    with patch("httpx.Client.post", side_effect=[mock_resp_429, mock_resp_200]) as mock_post:
        results = provider.rerank("query", [_make_candidate("chk_1", "text", 0.5, 1)])
        assert len(results) == 1
        assert results[0].rerank_score == 0.88
        assert mock_post.call_count == 2


def test_jina_reranker_missing_key_raises():
    """Verify missing API key raises ValueError."""
    provider = JinaRerankerProvider(api_key="")
    with pytest.raises(ValueError, match="Jina API key is not configured"):
        provider._call_api("query", ["doc1"], 1)


def test_hybrid_search_engine_reranker_fallback():
    """Verify HybridSearchEngine falls back gracefully to RRF if reranker fails."""
    c1 = _make_candidate("chk_1", "Text 1", 0.03, 1)
    c2 = _make_candidate("chk_2", "Text 2", 0.02, 2)

    bm25_mock = MagicMock()
    bm25_mock.search.return_value = [c1, c2]

    failing_reranker = MagicMock()
    failing_reranker.rerank.side_effect = RuntimeError("API unavailable")

    engine = HybridSearchEngine(
        embedding_provider=MagicMock(),
        vector_store=MagicMock(),
        bm25_index=bm25_mock,
        reranker=failing_reranker,
    )
    # dense fails -> BM25 returns [c1, c2] -> RRF fuses -> reranker throws error -> fallback to RRF
    engine.vector_store.search.side_effect = Exception("Dense offline")

    response = engine.search("test query", top_k=2, use_reranker=True)
    assert response.total_results == 2
    assert response.retrieval_metadata["reranking_status"] == "failed"
    assert response.results[0].chunk_id == "chk_1"


def test_hybrid_search_engine_use_reranker_disabled():
    """Verify disabling reranker bypasses reranking completely."""
    c1 = _make_candidate("chk_1", "Text 1", 0.03, 1)
    mock_reranker = MockRerankerProvider()

    bm25_mock = MagicMock()
    bm25_mock.search.return_value = [c1]

    engine = HybridSearchEngine(
        embedding_provider=MagicMock(),
        vector_store=MagicMock(),
        bm25_index=bm25_mock,
        reranker=mock_reranker,
    )
    engine.vector_store.search.side_effect = Exception("Dense offline")

    response = engine.search("test query", top_k=1, use_reranker=False)
    assert response.total_results == 1
    assert response.retrieval_metadata["reranking_status"] == "disabled"
    assert mock_reranker.call_count == 0


def test_hybrid_search_engine_end_to_end_reranking():
    """Verify HybridSearchEngine re-orders RRF candidates with reranker score."""
    c1 = _make_candidate("chk_1", "Generic info", 0.03, 1)
    c2 = _make_candidate("chk_2", "Exact Dell Latitude 5550 specs", 0.02, 2)
    mock_reranker = MockRerankerProvider()

    bm25_mock = MagicMock()
    bm25_mock.search.return_value = [c1, c2]

    engine = HybridSearchEngine(
        embedding_provider=MagicMock(),
        vector_store=MagicMock(),
        bm25_index=bm25_mock,
        reranker=mock_reranker,
    )
    engine.vector_store.search.side_effect = Exception("Dense offline")

    response = engine.search("Dell Latitude 5550", top_k=2, use_reranker=True)
    assert response.total_results == 2
    assert response.retrieval_metadata["reranking_status"] == "success"
    # Mock reranker reversed order so chk_2 is rank 1
    assert response.results[0].chunk_id == "chk_2"
    assert response.results[0].rank == 1
    assert abs(response.results[0].previous_score - (1.0 / 62.0)) < 1e-6  # RRF score preserved
    assert response.results[0].rerank_score > 0.8

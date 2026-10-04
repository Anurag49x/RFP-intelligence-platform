"""Tests for Phase 3: Embedding Provider, SQLite Cache, Qdrant Vector Store, and Indexing Service."""

import hashlib
from pathlib import Path
from typing import List
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.embeddings.base import EmbeddingProvider
from app.embeddings.cache import EmbeddingCache
from app.indexing.service import IndexingService
from app.schemas.canonical import Chunk
from app.vectorstore.qdrant import QdrantVectorStore


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock embedding provider producing fixed-dimension pseudo-vectors."""

    def __init__(self, dimension: int = 16, model_name: str = "mock-jina-v3"):
        self._dimension = dimension
        self._model_name = model_name
        self.call_count = 0

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _text_to_vec(self, text: str) -> List[float]:
        # Hash text to create deterministic unit vector
        h = hashlib.md5(text.encode("utf-8")).digest()
        vec = [float(b) / 255.0 for b in h[: self._dimension]]
        if len(vec) < self._dimension:
            vec.extend([0.0] * (self._dimension - len(vec)))
        # Normalize
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self.call_count += len(texts)
        return [self._text_to_vec(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._text_to_vec(text)


def test_embedding_cache_hit_and_miss(tmp_path: Path):
    """Verify SQLite cache stores and retrieves vectors with hit/miss tracking."""
    cache = EmbeddingCache(db_path=tmp_path / "test_embeddings.db")
    assert cache.count() == 0

    key1 = cache.compute_cache_key("model-a", "Proposal Submission Deadline")
    assert cache.get(key1) is None

    # Save to cache
    vec1 = [0.1, 0.2, 0.3, 0.4]
    cache.set_batch([(key1, "model-a", "chk_1", vec1)])

    assert cache.count() == 1
    cached_vec = cache.get(key1)
    assert cached_vec == vec1

    # Batch lookup
    batch_map = cache.get_batch([key1, "nonexistent_key"])
    assert key1 in batch_map
    assert batch_map[key1] == vec1
    assert "nonexistent_key" not in batch_map


def test_embedding_cache_invalidation_on_model_or_text_change(tmp_path: Path):
    """Verify modifying model or text alters the cache key."""
    cache = EmbeddingCache(db_path=tmp_path / "test_embeddings.db")
    key_model_a = cache.compute_cache_key("model-a", "Dell Latitude 5550")
    key_model_b = cache.compute_cache_key("model-b", "Dell Latitude 5550")
    key_text_diff = cache.compute_cache_key("model-a", "Dell Latitude 7440")

    assert key_model_a != key_model_b
    assert key_model_a != key_text_diff


def test_qdrant_deterministic_point_ids_and_upsert():
    """Verify Qdrant point IDs are deterministic and re-indexing updates in-place."""
    store = QdrantVectorStore(local_path=":memory:")
    col_name = "test_rfp_col"
    dimension = 4

    chunks = [
        Chunk(
            chunk_id="chk_Bid1_p1_0001_abc123",
            bid_id="Bid1",
            file_name="rfp.pdf",
            document_type="rfp",
            page_number=1,
            text="General scope of work",
            token_count=5,
            source_order=1,
        ),
        Chunk(
            chunk_id="chk_Bid1_p2_0002_def456",
            bid_id="Bid1",
            file_name="rfp.pdf",
            document_type="rfp",
            page_number=2,
            text="Technical specification table",
            chunk_type="table",
            token_count=6,
            source_order=2,
        ),
    ]
    vectors = [
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
    ]

    # First indexing run
    count1 = store.upsert_chunks(col_name, chunks, vectors)
    assert count1 == 2
    assert store.count(col_name) == 2

    # Second indexing run with identical chunk IDs (must not create duplicate points)
    count2 = store.upsert_chunks(col_name, chunks, vectors)
    assert count2 == 2
    assert store.count(col_name) == 2


def test_indexing_service_with_caching(bid2_path: Path, tmp_path: Path):
    """Verify end-to-end indexing pipeline with mock embeddings and cache verification."""
    if not bid2_path.exists():
        pytest.skip("Bid2 path not available")

    mock_provider = MockEmbeddingProvider(dimension=16)
    cache = EmbeddingCache(db_path=tmp_path / "embed_cache.db")
    store = QdrantVectorStore(local_path=str(tmp_path / "qdrant_store"))
    from app.indexing.registry import DocumentRegistry
    registry = DocumentRegistry(db_path=tmp_path / "test_reg.db")

    service = IndexingService(
        registry=registry,
        embedding_provider=mock_provider,
        embedding_cache=cache,
        vector_store=store,
        collection_name="test_indexing_bid2",
        bm25_corpus_path=tmp_path / "bm25.jsonl",
    )

    # First Indexing Run: all chunks are cache misses
    report1 = service.index_folder(bid2_path)
    assert report1.status == "success"
    assert report1.chunks_created > 0
    assert report1.embeddings_requested == report1.chunks_created
    assert report1.embeddings_cached == 0
    assert mock_provider.call_count == report1.chunks_created

    # Second Indexing Run: all files are unchanged (0 new API calls, skipped)
    report2 = service.index_folder(bid2_path)
    assert report2.status == "success"
    assert report2.files_unchanged == report1.files_new
    assert report2.embeddings_requested == 0
    # Call count should not have increased
    assert mock_provider.call_count == report1.chunks_created


from unittest.mock import MagicMock, patch


def test_api_index_endpoint(bid2_path: Path, test_client: TestClient):
    """Verify POST /index API endpoint executes cleanly."""
    if not bid2_path.exists():
        pytest.skip("Bid2 path not available")

    mock_report = MagicMock()
    mock_report.model_dump.return_value = {
        "status": "success",
        "bid_id": "Bid2",
        "folder_path": str(bid2_path),
        "documents_discovered": 5,
        "documents_ingested": 5,
        "chunks_created": 20,
        "embeddings_cached": 0,
        "embeddings_requested": 20,
        "vectors_upserted": 20,
        "bm25_indexed_chunks": 20,
        "elapsed_seconds": 1.23,
        "errors": [],
    }

    with patch("app.api.main.IndexingService") as MockServiceCls:
        mock_instance = MockServiceCls.return_value
        mock_instance.index_folder.return_value = mock_report.model_dump.return_value

        payload = {
            "folder_path": str(bid2_path),
            "bid_id": "Bid2",
        }
        response = test_client.post("/index", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["bid_id"] == "Bid2"
        assert data["chunks_created"] > 0


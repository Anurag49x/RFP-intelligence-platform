"""Tests for Phase 7: Incremental Indexing, Registry, Change Detection, and Stale Data Removal."""

import hashlib
from pathlib import Path
import shutil
from typing import List
import pytest

from app.embeddings.base import EmbeddingProvider
from app.embeddings.cache import EmbeddingCache
from app.indexing.hashing import compute_file_hash
from app.indexing.manager import IndexManager
from app.indexing.registry import DocumentRecord, DocumentRegistry
from app.lexical.bm25 import BM25Index
from app.retrieval.hybrid import HybridSearchEngine
from app.schemas.canonical import Chunk, SearchFilters
from app.vectorstore.qdrant import QdrantVectorStore


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock embedding provider producing 16-dim vectors."""

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
        h = hashlib.md5(text.encode("utf-8")).digest()
        vec = [float(b) / 255.0 for b in h[: self._dimension]]
        if len(vec) < self._dimension:
            vec.extend([0.0] * (self._dimension - len(vec)))
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self.call_count += len(texts)
        return [self._text_to_vec(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._text_to_vec(text)


def _create_sample_html(file_path: Path, title: str, body_text: str):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>{title}</title></head>
    <body>
        <h1>{title}</h1>
        <p>{body_text}</p>
    </body>
    </html>
    """
    file_path.write_text(html_content, encoding="utf-8")


def test_registry_persistence(tmp_path: Path):
    """Verify DocumentRegistry inserts, updates, queries, and deletes records."""
    db_file = tmp_path / "test_reg.db"
    registry = DocumentRegistry(db_path=db_file)

    rec = DocumentRecord(
        file_path=str(tmp_path / "doc1.pdf"),
        file_name="doc1.pdf",
        bid_id="BidX",
        file_hash="hash123",
        file_size=1024,
        modified_time=12345.67,
        document_type="rfp",
        chunk_ids=["chk_1", "chk_2"],
        embedding_model="mock-jina-v3",
    )

    registry.upsert_record(rec)
    fetched = registry.get_record(str(tmp_path / "doc1.pdf"))
    assert fetched is not None
    assert fetched.file_name == "doc1.pdf"
    assert fetched.file_hash == "hash123"
    assert fetched.chunk_ids == ["chk_1", "chk_2"]

    # Test update
    rec.file_hash = "hash456"
    registry.upsert_record(rec)
    updated = registry.get_record(str(tmp_path / "doc1.pdf"))
    assert updated.file_hash == "hash456"

    # Test delete
    registry.delete_record(str(tmp_path / "doc1.pdf"))
    assert registry.get_record(str(tmp_path / "doc1.pdf")) is None


def test_incremental_indexing_workflow_step_by_step(tmp_path: Path):
    """Execute the full 5-step incremental lifecycle: new, unchanged, modified, unseen, deleted."""
    # Environment directories
    bid_dir = tmp_path / "BidTest"
    bid_dir.mkdir(parents=True, exist_ok=True)
    doc_a = bid_dir / "notice.html"
    doc_b = bid_dir / "specs.html"

    _create_sample_html(doc_a, "Notice A", "The submission deadline is October 30 2026.")
    _create_sample_html(doc_b, "Specs B", "The hardware model is Latitude 5550 with 16GB RAM.")

    reg_db = tmp_path / "reg.db"
    cache_db = tmp_path / "cache.db"
    qdrant_dir = tmp_path / "qdrant"
    bm25_file = tmp_path / "bm25.jsonl"

    provider = MockEmbeddingProvider()
    cache = EmbeddingCache(db_path=cache_db)
    store = QdrantVectorStore(local_path=str(qdrant_dir))
    registry = DocumentRegistry(db_path=reg_db)
    bm25 = BM25Index(chunks=[])

    manager = IndexManager(
        registry=registry,
        embedding_provider=provider,
        embedding_cache=cache,
        vector_store=store,
        bm25_index=bm25,
        collection_name="test_inc_col",
        bm25_corpus_path=bm25_file,
    )

    # STEP 1: Initial index (2 new files)
    report1 = manager.sync_folder(bid_dir, bid_id="BidTest")
    assert report1.status == "success"
    assert report1.files_new == 2
    assert report1.files_unchanged == 0
    assert report1.files_modified == 0
    assert report1.files_deleted == 0
    assert report1.chunks_added == 2
    assert report1.embeddings_created == 2
    assert provider.call_count == 2
    assert store.count("test_inc_col") == 2

    # STEP 2: Re-index unchanged corpus (0 new, 2 unchanged)
    report2 = manager.sync_folder(bid_dir, bid_id="BidTest")
    assert report2.status == "success"
    assert report2.files_new == 0
    assert report2.files_unchanged == 2
    assert report2.files_modified == 0
    assert report2.files_deleted == 0
    assert report2.chunks_added == 0
    assert report2.embeddings_created == 0
    # No new embedding API calls
    assert provider.call_count == 2
    assert store.count("test_inc_col") == 2

    # STEP 3: Modify doc_a (modify deadline)
    _create_sample_html(doc_a, "Notice A", "The submission deadline is November 15 2026.")
    report3 = manager.sync_folder(bid_dir, bid_id="BidTest")
    assert report3.status == "success"
    assert report3.files_modified == 1
    assert report3.files_unchanged == 1
    assert report3.chunks_removed == 1  # Old chunk purged
    assert report3.chunks_added == 1    # New chunk added
    assert store.count("test_inc_col") == 2
    assert provider.call_count == 3     # 1 new embedding for modified text

    # STEP 4: Add Unseen Bid3 (no code changes)
    bid3_dir = tmp_path / "Bid3"
    bid3_dir.mkdir(parents=True, exist_ok=True)
    doc_c = bid3_dir / "unseen_bid.html"
    _create_sample_html(doc_c, "Unseen Bid3", "Dallas ISD proposal for student tablets.")

    report4 = manager.sync_folder(bid3_dir, bid_id="Bid3")
    assert report4.status == "success"
    assert report4.files_new == 1
    assert report4.bid_id == "Bid3"
    assert store.count("test_inc_col") == 3

    # STEP 5: Delete doc_b from BidTest
    doc_b.unlink()
    report5 = manager.sync_folder(bid_dir, bid_id="BidTest")
    assert report5.status == "success"
    assert report5.files_deleted == 1
    assert report5.chunks_removed == 1
    assert store.count("test_inc_col") == 2


def test_stale_data_is_purged_and_unsearchable(tmp_path: Path):
    """Verify modifying a document removes old stale facts and only returns updated facts."""
    bid_dir = tmp_path / "BidStaleTest"
    bid_dir.mkdir(parents=True, exist_ok=True)
    doc = bid_dir / "procurement.html"

    _create_sample_html(doc, "Procurement Doc", "Proposal submission deadline: 30 October 2026.")

    provider = MockEmbeddingProvider()
    cache = EmbeddingCache(db_path=tmp_path / "cache.db")
    store = QdrantVectorStore(local_path=str(tmp_path / "qdrant"))
    registry = DocumentRegistry(db_path=tmp_path / "reg.db")
    bm25 = BM25Index(chunks=[])

    manager = IndexManager(
        registry=registry,
        embedding_provider=provider,
        embedding_cache=cache,
        vector_store=store,
        bm25_index=bm25,
        collection_name="stale_test_col",
        bm25_corpus_path=tmp_path / "bm25.jsonl",
    )

    # 1. Index initial version
    manager.sync_folder(bid_dir, bid_id="BidStaleTest")

    engine = HybridSearchEngine(
        embedding_provider=provider,
        vector_store=store,
        bm25_index=manager.bm25_index,
        collection_name="stale_test_col",
    )

    res1 = engine.search("30 October 2026", top_k=5, use_reranker=False)
    assert len(res1.results) > 0
    assert "30 October 2026" in res1.results[0].text

    # 2. Modify document to new deadline
    _create_sample_html(doc, "Procurement Doc", "Proposal submission deadline: 15 November 2026.")
    manager.sync_folder(bid_dir, bid_id="BidStaleTest")

    # 3. Search for OLD deadline -> Must NOT return old passage
    res_old = engine.search("30 October 2026", top_k=5, use_reranker=False)
    for r in res_old.results:
        assert "30 October 2026" not in r.text

    # 4. Search for NEW deadline -> Must find updated passage
    res_new = engine.search("15 November 2026", top_k=5, use_reranker=False)
    assert len(res_new.results) > 0
    assert "15 November 2026" in res_new.results[0].text


def test_chunking_version_and_model_invalidation(tmp_path: Path):
    """Verify changing chunking version or embedding model flags files as modified for re-indexing."""
    bid_dir = tmp_path / "BidVer"
    bid_dir.mkdir(parents=True, exist_ok=True)
    doc = bid_dir / "item.html"
    _create_sample_html(doc, "Item", "Item specification details.")

    shared_store = QdrantVectorStore(local_path=str(tmp_path / "qdrant"))
    shared_reg = DocumentRegistry(db_path=tmp_path / "reg.db")
    shared_cache = EmbeddingCache(db_path=tmp_path / "cache.db")

    provider_v1 = MockEmbeddingProvider(model_name="mock-model-v1")
    manager_v1 = IndexManager(
        registry=shared_reg,
        embedding_provider=provider_v1,
        embedding_cache=shared_cache,
        vector_store=shared_store,
        bm25_index=BM25Index(chunks=[]),
        bm25_corpus_path=tmp_path / "bm25.jsonl",
    )

    # Initial indexing with model-v1
    rep1 = manager_v1.sync_folder(bid_dir, bid_id="BidVer")
    assert rep1.files_new == 1

    # Index again with a different model -> triggers re-indexing of modified files
    provider_v2 = MockEmbeddingProvider(model_name="mock-model-v2")
    manager_v2 = IndexManager(
        registry=shared_reg,
        embedding_provider=provider_v2,
        embedding_cache=shared_cache,
        vector_store=shared_store,
        bm25_index=BM25Index(chunks=[]),
        bm25_corpus_path=tmp_path / "bm25.jsonl",
    )

    rep2 = manager_v2.sync_folder(bid_dir, bid_id="BidVer")
    assert rep2.files_modified == 1
    assert rep2.files_unchanged == 0


def test_compute_file_hash(tmp_path: Path):
    """Verify compute_file_hash is deterministic and changes on content modification."""
    f = tmp_path / "test.txt"
    f.write_text("Hello World", encoding="utf-8")
    h1 = compute_file_hash(f)
    assert len(h1) == 64

    # Identical content -> identical hash
    h2 = compute_file_hash(f)
    assert h1 == h2

    # Modified content -> different hash
    f.write_text("Hello World Modified", encoding="utf-8")
    h3 = compute_file_hash(f)
    assert h1 != h3


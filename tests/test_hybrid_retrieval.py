"""Tests for Phase 4: BM25 Lexical Search, Reciprocal Rank Fusion, and Hybrid Retrieval."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.chunking.storage import load_chunks
from app.lexical.bm25 import BM25Index
from app.retrieval.hybrid import HybridSearchEngine
from app.retrieval.rrf import reciprocal_rank_fusion
from app.schemas.canonical import Chunk, Evidence, SearchFilters, SearchResult
from tests.test_indexing_and_qdrant import MockEmbeddingProvider
from app.vectorstore.qdrant import QdrantVectorStore


def test_bm25_exact_identifier_search():
    """Verify BM25 retrieves exact procurement identifiers intact."""
    chunks = [
        Chunk(
            chunk_id="chk_1",
            bid_id="Bid1",
            file_name="rfp.pdf",
            document_type="rfp",
            page_number=1,
            text="Solicitation Number JA-207652 Student and Staff Computing Devices",
            token_count=10,
            source_order=1,
        ),
        Chunk(
            chunk_id="chk_2",
            bid_id="Bid2",
            file_name="porfp.pdf",
            document_type="rfp",
            page_number=1,
            text="PORFP Number: #E20P4600040 eMMA Project Number: BPM044557",
            token_count=10,
            source_order=2,
        ),
        Chunk(
            chunk_id="chk_3",
            bid_id="Bid2",
            file_name="specs.pdf",
            document_type="specs",
            page_number=2,
            text="Thunderbolt 4 Dock Model WD22TB4 with 180W power adapter",
            token_count=10,
            source_order=3,
        ),
    ]

    index = BM25Index(chunks=chunks)

    # 1. Exact query: JA-207652
    res_ja = index.search("JA-207652", top_k=1)
    assert len(res_ja) == 1
    assert res_ja[0].chunk_id == "chk_1"
    assert "JA-207652" in res_ja[0].text

    # 2. Exact query: E20P4600040
    res_porfp = index.search("E20P4600040", top_k=1)
    assert len(res_porfp) == 1
    assert res_porfp[0].chunk_id == "chk_2"

    # 3. Exact query: WD22TB4
    res_dock = index.search("WD22TB4", top_k=1)
    assert len(res_dock) == 1
    assert res_dock[0].chunk_id == "chk_3"

    # 4. Case normalization: e20p4600040
    res_case = index.search("e20p4600040", top_k=1)
    assert len(res_case) == 1
    assert res_case[0].chunk_id == "chk_2"


def test_bm25_metadata_filtering():
    """Verify BM25 filtering by bid_id, document_type, and addendum_number."""
    chunks = [
        Chunk(
            chunk_id="chk_bid1_rfp",
            bid_id="Bid1",
            file_name="rfp.pdf",
            document_type="rfp",
            page_number=1,
            text="Submission deadline is October 15, 2026",
            token_count=6,
            source_order=1,
        ),
        Chunk(
            chunk_id="chk_bid1_addendum2",
            bid_id="Bid1",
            file_name="addendum2.pdf",
            document_type="addendum",
            addendum_number=2,
            page_number=1,
            text="Submission deadline is extended to November 20, 2026",
            token_count=8,
            source_order=2,
        ),
        Chunk(
            chunk_id="chk_bid2_specs",
            bid_id="Bid2",
            file_name="specs.pdf",
            document_type="specs",
            page_number=1,
            text="Dell Latitude 5550 specification deadline",
            token_count=6,
            source_order=3,
        ),
    ]

    index = BM25Index(chunks=chunks)

    # Filter by bid_id="Bid1" and document_type="addendum"
    filters = SearchFilters(bid_id="Bid1", document_type="addendum")
    results = index.search("deadline", top_k=5, filters=filters)

    assert len(results) == 1
    assert results[0].chunk_id == "chk_bid1_addendum2"
    assert results[0].evidence.document_type == "addendum"


def test_reciprocal_rank_fusion():
    """Verify RRF formula fuses and merges duplicate chunk IDs accurately."""
    ev_a = Evidence(bid_id="Bid1", file_name="f.pdf", page_number=1, chunk_id="chk_A", text="Text A", document_type="rfp")
    ev_b = Evidence(bid_id="Bid1", file_name="f.pdf", page_number=2, chunk_id="chk_B", text="Text B", document_type="rfp")
    ev_c = Evidence(bid_id="Bid1", file_name="f.pdf", page_number=3, chunk_id="chk_C", text="Text C", document_type="rfp")

    dense_list = [
        SearchResult(rank=1, chunk_id="chk_A", text="Text A", score=0.95, retrieval_source="dense", evidence=ev_a),
        SearchResult(rank=2, chunk_id="chk_B", text="Text B", score=0.85, retrieval_source="dense", evidence=ev_b),
    ]

    bm25_list = [
        SearchResult(rank=1, chunk_id="chk_B", text="Text B", score=12.5, retrieval_source="bm25", evidence=ev_b),
        SearchResult(rank=2, chunk_id="chk_C", text="Text C", score=9.2, retrieval_source="bm25", evidence=ev_c),
    ]

    fused = reciprocal_rank_fusion([dense_list, bm25_list], rrf_k=60, top_k=3)

    assert len(fused) == 3
    # chk_B appeared in both (dense rank 2, bm25 rank 1), score = 1/62 + 1/61 ~ 0.0325
    # chk_A appeared in dense (rank 1), score = 1/61 ~ 0.01639
    # chk_C appeared in bm25 (rank 2), score = 1/62 ~ 0.01612
    assert fused[0].chunk_id == "chk_B"
    assert fused[0].retrieval_source == "hybrid"
    assert "bm25" in fused[0].evidence.retrieval_source and "dense" in fused[0].evidence.retrieval_source
    assert fused[1].chunk_id == "chk_A"
    assert fused[2].chunk_id == "chk_C"


def test_hybrid_search_engine_end_to_end(tmp_path: Path):
    """Verify HybridSearchEngine integrates dense, BM25, and RRF seamlessly."""
    mock_provider = MockEmbeddingProvider(dimension=16)
    vector_store = QdrantVectorStore(local_path=str(tmp_path / "qdrant_hybrid"))
    col_name = "test_hybrid_col"

    chunks = [
        Chunk(
            chunk_id="chk_dell_model",
            bid_id="Bid2",
            file_name="specs.pdf",
            document_type="specs",
            page_number=1,
            section="Laptop Model",
            text="The specified laptop model is Dell Latitude 5550 with Intel Core i7.",
            token_count=13,
            source_order=1,
        ),
        Chunk(
            chunk_id="chk_dell_warranty",
            bid_id="Bid2",
            file_name="porfp.pdf",
            document_type="rfp",
            page_number=2,
            section="Warranty Coverage",
            text="Dell laptops must include 3-year extended on-site hardware warranty.",
            token_count=11,
            source_order=2,
        ),
    ]

    # Index into both stores
    vectors = mock_provider.embed_documents([c.text for c in chunks])
    vector_store.upsert_chunks(col_name, chunks, vectors)
    bm25 = BM25Index(chunks=chunks)

    engine = HybridSearchEngine(
        embedding_provider=mock_provider,
        vector_store=vector_store,
        bm25_index=bm25,
        collection_name=col_name,
    )

    # Execute search
    response = engine.search(query="Dell Latitude 5550", top_k=2)
    assert response.total_results > 0
    assert response.results[0].chunk_id == "chk_dell_model"
    assert response.results[0].evidence.bid_id == "Bid2"
    assert response.results[0].evidence.file_name == "specs.pdf"
    assert response.results[0].evidence.page_number == 1
    assert response.results[0].evidence.section == "Laptop Model"


def test_search_api_endpoint(test_client: TestClient):
    """Verify GET and POST /search API endpoints."""
    # POST /search
    post_resp = test_client.post("/search", json={"query": "deadline", "top_k": 3})
    assert post_resp.status_code == 200
    post_data = post_resp.json()
    assert "results" in post_data
    assert "retrieval_metadata" in post_data

    # GET /search
    get_resp = test_client.get("/search?q=deadline&top_k=2")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert "results" in get_data

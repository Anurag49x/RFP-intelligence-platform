"""Tests for Phase 2: Chunking, Deterministic IDs, and Canonical Evidence Model."""

from pathlib import Path
import pytest

from app.chunking.chunker import DocumentChunker
from app.chunking.ids import generate_chunk_id
from app.chunking.storage import load_chunks, save_chunks
from app.chunking.table_chunker import TableChunker
from app.chunking.text_chunker import TextChunker
from app.chunking.tokenizer import count_tokens
from app.ingestion.service import IngestionService
from app.schemas.canonical import (
    Chunk,
    Citation,
    Document,
    DocumentMetadata,
    DocumentPage,
    Evidence,
    TableBlock,
)


def test_deterministic_chunk_ids():
    """Verify that chunk IDs are stable across identical inputs."""
    id1 = generate_chunk_id(
        bid_id="Bid1",
        file_name="test.pdf",
        page_number=2,
        source_order=1,
        text="Sample text content for chunking",
        section="Scope of Work",
    )
    id2 = generate_chunk_id(
        bid_id="Bid1",
        file_name="test.pdf",
        page_number=2,
        source_order=1,
        text="Sample text content for chunking",
        section="Scope of Work",
    )
    assert id1 == id2
    assert id1.startswith("chk_Bid1_p2_0001_")


def test_chunk_ids_uniqueness_on_different_content():
    """Verify distinct content produces different chunk IDs."""
    id1 = generate_chunk_id("Bid1", "test.pdf", 1, 1, "Text block A")
    id2 = generate_chunk_id("Bid1", "test.pdf", 1, 2, "Text block B")
    assert id1 != id2


def test_table_chunker_atomic_and_large_split():
    """Verify small tables stay atomic and large tables repeat headers when split."""
    chunker = TableChunker(max_tokens=60)
    
    # Small table
    small_table = TableBlock(
        table_id="t1",
        page_number=1,
        headers=["Product", "Qty"],
        rows=[["Dell Latitude 5550", "10"], ["Dock WD22TB4", "10"]],
        raw_markdown="| Product | Qty |\n| --- | --- |\n| Dell Latitude 5550 | 10 |\n| Dock WD22TB4 | 10 |",
    )
    small_chunks = chunker.chunk_table(
        table=small_table,
        bid_id="Bid2",
        file_name="specs.pdf",
        document_type="specs",
        addendum_number=None,
        section="Hardware",
        start_source_order=1,
    )
    assert len(small_chunks) == 1
    assert small_chunks[0].chunk_type == "table"
    assert "| Product | Qty |" in small_chunks[0].text
    assert small_chunks[0].section == "Hardware"

    # Large table that exceeds token limit
    large_rows = [[f"Device_{i}", f"Model_{i}", f"SN_{i*1000}"] for i in range(25)]
    large_table = TableBlock(
        table_id="t2",
        page_number=2,
        headers=["Item", "Model", "Serial"],
        rows=large_rows,
        raw_markdown="| Item | Model | Serial |\n| --- | --- | --- |\n" + "\n".join([f"| Device_{i} | Model_{i} | SN_{i*1000} |" for i in range(25)]),
    )
    large_chunks = chunker.chunk_table(
        table=large_table,
        bid_id="Bid2",
        file_name="inventory.pdf",
        document_type="specs",
        addendum_number=None,
        section="Inventory List",
        start_source_order=1,
    )
    assert len(large_chunks) > 1
    for chunk in large_chunks:
        assert "| Item | Model | Serial |" in chunk.text
        assert "| --- | --- | --- |" in chunk.text
        assert chunk.chunk_type == "table"


def test_text_chunker_section_detection_and_overlap():
    """Verify heading detection and overlap across text chunks."""
    chunker = TextChunker(target_tokens=40, max_tokens=60, overlap_tokens=15)
    
    sample_text = (
        "SECTION I. PROPOSAL INSTRUCTIONS\n\n"
        "All proposals must be submitted electronically before the closing deadline. "
        "Late submissions will be rejected automatically without consideration.\n\n"
        "SECTION II. TECHNICAL SPECIFICATIONS\n\n"
        "The vendor shall provide 500 units of student laptops and 500 docking stations. "
        "All hardware must include 3-year on-site warranty coverage with next business day support."
    )
    
    chunks, final_sec, next_order = chunker.chunk_page_text(
        page_text=sample_text,
        bid_id="Bid1",
        file_name="rfp.pdf",
        document_type="rfp",
        page_number=3,
        addendum_number=None,
        start_source_order=1,
    )
    
    assert len(chunks) >= 2
    # Check section inheritance
    sections = [c.section for c in chunks if c.section]
    assert any("TECHNICAL SPECIFICATIONS" in s for s in sections)


def test_chunk_to_evidence_and_citation():
    """Verify chunk converts to Evidence and Citation while preserving provenance."""
    chunk = Chunk(
        chunk_id="chk_Bid1_p4_0003_abcdef123456",
        bid_id="Bid1",
        file_name="Addendum 2.pdf",
        document_type="addendum",
        page_number=4,
        section="Submission Deadline Extension",
        addendum_number=2,
        text="The submission deadline is extended to November 20, 2026 at 2:00 PM.",
        chunk_type="text",
        token_count=18,
        source_order=3,
        metadata={"document_date": "2026-10-15"},
    )

    # Convert to Evidence
    evidence = chunk.to_evidence(score=0.92, rank=1, retrieval_source="hybrid")
    assert isinstance(evidence, Evidence)
    assert evidence.bid_id == "Bid1"
    assert evidence.file_name == "Addendum 2.pdf"
    assert evidence.page_number == 4
    assert evidence.addendum_number == 2
    assert evidence.section == "Submission Deadline Extension"
    assert evidence.score == 0.92
    assert evidence.retrieval_source == "hybrid"

    # Convert to Citation
    citation = chunk.to_citation()
    assert isinstance(citation, Citation)
    assert citation.bid_id == "Bid1"
    assert citation.chunk_id == chunk.chunk_id
    assert citation.addendum_number == 2


def test_chunking_end_to_end_on_real_bid(bid2_path: Path, tmp_path: Path):
    """Verify full chunking pipeline on real Bid2 ingestion output."""
    if not bid2_path.exists():
        pytest.skip("Bid2 data not available")

    # Ingest Bid2
    ingest_result = IngestionService.ingest_folder(bid2_path)
    assert len(ingest_result.documents) == 5

    # Chunk all documents
    chunker = DocumentChunker(target_tokens=700, max_tokens=850, overlap_tokens=100)
    all_chunks = chunker.chunk_bid(ingest_result.documents)

    assert len(all_chunks) > 0
    # Verify all chunks have required provenance fields
    for chunk in all_chunks:
        assert chunk.bid_id == "Bid2"
        assert chunk.file_name in {d.metadata.file_name for d in ingest_result.documents}
        assert chunk.page_number >= 1
        assert chunk.chunk_id.startswith("chk_Bid2_")
        assert len(chunk.text) > 0
        assert chunk.token_count > 0

    # Test saving and reloading from JSONL
    saved_path = save_chunks("Bid2", all_chunks, output_dir=tmp_path)
    assert saved_path.exists()

    reloaded_chunks = load_chunks("Bid2", output_dir=tmp_path)
    assert len(reloaded_chunks) == len(all_chunks)
    assert reloaded_chunks[0].chunk_id == all_chunks[0].chunk_id

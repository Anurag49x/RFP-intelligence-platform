"""Tests for IngestionService orchestrating end-to-end ingestion on real bid folders."""

from pathlib import Path
import pytest
from app.ingestion.service import IngestionService


def test_ingest_bid1_folder(bid1_path: Path, tmp_path: Path):
    """Verify full ingestion of Bid1 folder."""
    if not bid1_path.exists():
        pytest.skip("Bid1 path does not exist in environment")

    result = IngestionService.ingest_folder(bid1_path)

    assert result.bid_id == "Bid1"
    assert len(result.documents) == 4
    assert result.summary["total_files_discovered"] == 4
    assert result.summary["total_documents_ingested"] == 4

    # Check classifications
    types = {d.metadata.doc_type for d in result.documents}
    assert "rfp" in types
    assert "addendum" in types
    assert "bid_page" in types

    # Check addendum numbers
    addendums = [d for d in result.documents if d.metadata.doc_type == "addendum"]
    addendum_nums = {d.metadata.addendum_number for d in addendums}
    assert 1 in addendum_nums
    assert 2 in addendum_nums

    # Verify canonical JSON can be saved
    out_file = IngestionService.save_canonical_json(result, output_dir=tmp_path)
    assert out_file.exists()
    assert out_file.stat().st_size > 1000


def test_ingest_bid2_folder(bid2_path: Path, tmp_path: Path):
    """Verify full ingestion of Bid2 folder."""
    if not bid2_path.exists():
        pytest.skip("Bid2 path does not exist in environment")

    result = IngestionService.ingest_folder(bid2_path)

    assert result.bid_id == "Bid2"
    assert len(result.documents) == 5
    assert result.summary["total_files_discovered"] == 5
    assert result.summary["total_documents_ingested"] == 5

    # Check classifications
    types = {d.metadata.doc_type for d in result.documents}
    assert "rfp" in types
    assert "specs" in types
    assert "affidavit" in types
    assert "bid_page" in types

    # Verify affidavits count
    affidavits = [d for d in result.documents if d.metadata.doc_type == "affidavit"]
    assert len(affidavits) == 2

    # Verify specs count
    specs = [d for d in result.documents if d.metadata.doc_type == "specs"]
    assert len(specs) == 1

    # Verify canonical JSON can be saved
    out_file = IngestionService.save_canonical_json(result, output_dir=tmp_path)
    assert out_file.exists()
    assert out_file.stat().st_size > 1000

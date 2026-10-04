"""Tests for PDFParser component."""

from pathlib import Path
import pytest
from app.ingestion.pdf_parser import PDFParser
from app.schemas.canonical import DocumentMetadata


def test_parse_real_pdf_addendum(bid1_path: Path):
    """Verify parsing of actual Bid1 Addendum 1 PDF."""
    pdf_file = bid1_path / "Addendum 1 RFP JA-207652 Student and Staff Computing Devices.pdf"
    if not pdf_file.exists():
        pytest.skip("Test file not available in test environment")

    metadata = DocumentMetadata(
        bid_id="Bid1",
        file_name=pdf_file.name,
        doc_type="addendum",
        addendum_number=1,
        source_path=str(pdf_file),
    )

    doc, warnings, errors = PDFParser.parse_pdf(pdf_file, metadata)
    assert doc is not None
    assert len(errors) == 0
    assert doc.page_count > 0
    assert doc.raw_text_length > 100
    assert len(doc.pages) == doc.page_count
    for page in doc.pages:
        assert page.page_number >= 1


def test_parse_real_pdf_specs(bid2_path: Path):
    """Verify parsing of actual Bid2 Dell Laptop Specs PDF."""
    pdf_file = bid2_path / "Dell_Laptop_Specs.pdf"
    if not pdf_file.exists():
        pytest.skip("Test file not available in test environment")

    metadata = DocumentMetadata(
        bid_id="Bid2",
        file_name=pdf_file.name,
        doc_type="specs",
        source_path=str(pdf_file),
    )

    doc, warnings, errors = PDFParser.parse_pdf(pdf_file, metadata)
    assert doc is not None
    assert doc.page_count > 0
    assert doc.raw_text_length > 50


def test_nonexistent_pdf_returns_error():
    """Verify non-existent PDF returns IngestionError gracefully without crashing."""
    metadata = DocumentMetadata(
        bid_id="TestBid",
        file_name="nonexistent.pdf",
        doc_type="rfp",
        source_path="nonexistent.pdf",
    )
    doc, warnings, errors = PDFParser.parse_pdf("nonexistent.pdf", metadata)
    assert doc is None
    assert len(errors) == 1
    assert errors[0].error_type == "FileNotFoundError"

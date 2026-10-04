"""Tests for Canonical Schemas and Metadata models."""

from app.schemas.canonical import (
    Document,
    DocumentMetadata,
    DocumentPage,
    TableBlock,
)


def test_canonical_document_schema_validation():
    """Verify serialization and validation of canonical Document objects."""
    table = TableBlock(
        table_id="page_1_table_1",
        page_number=1,
        headers=["Col1", "Col2"],
        rows=[["A", "B"]],
        raw_markdown="| Col1 | Col2 |\n|---|---|\n| A | B |",
    )
    page = DocumentPage(
        page_number=1,
        text="Sample page text",
        tables=[table],
        is_suspicious_or_empty=False,
    )
    metadata = DocumentMetadata(
        bid_id="Bid1",
        file_name="sample.pdf",
        doc_type="rfp",
        addendum_number=None,
        source_path="/path/to/sample.pdf",
        file_hash="abcdef1234567890",
    )
    doc = Document(
        metadata=metadata,
        pages=[page],
        raw_text_length=16,
        page_count=1,
    )

    doc_dict = doc.model_dump()
    assert doc_dict["metadata"]["bid_id"] == "Bid1"
    assert doc_dict["pages"][0]["tables"][0]["headers"] == ["Col1", "Col2"]
    assert doc_dict["page_count"] == 1

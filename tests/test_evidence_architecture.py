"""Tests for Phase 8: Evidence, Citation, FieldResult models, and EvidenceStore."""

import pytest
from pydantic import ValidationError

from app.evidence.store import EvidenceStore
from app.schemas.canonical import Chunk, Citation, Evidence, FieldResult, SearchResult


def test_valid_citation_and_properties():
    """Verify Citation attributes and backward-compatible properties."""
    cit = Citation(
        bid_id="Bid1",
        file_name="rfp.pdf",
        page_number=3,
        chunk_id="chk_123",
        text="Snippet text here",
        document_type="rfp",
        section="Scope of Work",
        addendum_number=None,
    )
    assert cit.file == "rfp.pdf"
    assert cit.page == 3
    assert cit.chunk_id == "chk_123"
    assert cit.text == "Snippet text here"


def test_evidence_to_citation_conversion():
    """Verify Evidence converts cleanly into a Citation preserving provenance."""
    ev = Evidence(
        bid_id="Bid2",
        file_name="porfp.pdf",
        page_number=2,
        chunk_id="chk_bid2_01",
        text="Dell Latitude 5550 specifications",
        document_type="rfp",
        section="Hardware Models",
        addendum_number=None,
        score=0.95,
        rank=1,
        retrieval_source="dense",
    )
    cit = ev.to_citation()
    assert isinstance(cit, Citation)
    assert cit.file_name == "porfp.pdf"
    assert cit.file == "porfp.pdf"
    assert cit.page_number == 2
    assert cit.page == 2
    assert cit.chunk_id == "chk_bid2_01"
    assert cit.bid_id == "Bid2"
    assert cit.text == "Dell Latitude 5550 specifications"


def test_field_result_validation_rules():
    """Verify FieldResult rules: confidence bounds, non-null source requirement, null notes."""
    # 1. Valid non-null field with citation
    cit = Citation(
        bid_id="Bid1",
        file_name="rfp.pdf",
        page_number=1,
        chunk_id="chk_real_01",
        text="Deadline: Nov 15 2026",
    )
    # Register chunk in EvidenceStore
    EvidenceStore.register_chunk(
        Chunk(
            chunk_id="chk_real_01",
            bid_id="Bid1",
            file_name="rfp.pdf",
            document_type="rfp",
            page_number=1,
            text="Deadline: Nov 15 2026",
        )
    )

    valid_res = FieldResult(
        value="Nov 15 2026",
        sources=[cit],
        confidence=0.95,
        notes="Verified from Addendum 2",
    )
    errs = EvidenceStore.validate_field_result(valid_res, field_name="due_date")
    assert len(errs) == 0

    # 2. Non-null field without sources must fail validation
    invalid_no_source = FieldResult(
        value="Nov 15 2026",
        sources=[],
        confidence=0.95,
    )
    errs_no_source = EvidenceStore.validate_field_result(invalid_no_source, field_name="due_date")
    assert len(errs_no_source) > 0
    assert "must have at least one source citation" in errs_no_source[0]

    # 3. Source pointing to nonexistent chunk must fail
    cit_fake = Citation(
        bid_id="Bid1",
        file_name="rfp.pdf",
        page_number=1,
        chunk_id="chk_nonexistent_999",
        text="Fake text",
    )
    invalid_fake_source = FieldResult(
        value="Nov 15 2026",
        sources=[cit_fake],
        confidence=0.9,
    )
    errs_fake = EvidenceStore.validate_field_result(invalid_fake_source, field_name="due_date")
    assert len(errs_fake) > 0
    assert "does not exist in EvidenceStore" in errs_fake[0]

    # 4. Valid null field
    null_res = FieldResult(
        value=None,
        sources=[],
        confidence=0.0,
        notes="Not found in documents.",
    )
    errs_null = EvidenceStore.validate_field_result(null_res, field_name="bid_bond")
    assert len(errs_null) == 0

    # 5. Invalid confidence out of range [0, 1]
    with pytest.raises(ValidationError):
        FieldResult(
            value=None,
            confidence=1.5,
        )


def test_citation_deduplication():
    """Verify deduplication removes redundant citations with identical bid_id and chunk_id."""
    c1 = Citation(bid_id="Bid1", file_name="f.pdf", page_number=1, chunk_id="chk_01", text="text1")
    c2 = Citation(bid_id="Bid1", file_name="f.pdf", page_number=2, chunk_id="chk_02", text="text2")
    c1_dup = Citation(bid_id="Bid1", file_name="f.pdf", page_number=1, chunk_id="chk_01", text="text1 dup")

    deduped = EvidenceStore.deduplicate_citations([c1, c2, c1_dup])
    assert len(deduped) == 2
    assert [c.chunk_id for c in deduped] == ["chk_01", "chk_02"]

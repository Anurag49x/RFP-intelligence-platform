"""Unit tests for Phase 12 Validator and Targeted Retry loop."""

import pytest
from unittest.mock import MagicMock

from app.agents.retry_agent import RetryAgent
from app.agents.validator_agent import ValidatorAgent
from app.evidence.store import EvidenceStore
from app.schemas.canonical import Citation, Evidence, FieldResult
from app.validation.validator import ExtractionValidator


def test_validator_passes_well_formed_fields():
    validator = ExtractionValidator(check_registry=False)
    fields = {
        "due_date": FieldResult(
            value="October 10, 2024",
            sources=[Citation(chunk_id="c1", file_name="addendum.pdf", page_number=1, text="Oct 10")],
            confidence=0.95,
        ),
        "product": FieldResult(
            value=None,
            sources=[],
            confidence=0.0,
            notes="Not found in documents.",
        ),
    }

    res = validator.validate(fields)
    assert res.is_valid is True
    assert len(res.rejected_fields) == 0
    assert "due_date" in res.passed_fields
    assert "product" in res.passed_fields


def test_validator_fails_missing_citation_for_non_null():
    validator = ExtractionValidator(check_registry=False)
    fields = {
        "model_no": FieldResult(
            value="Dell Latitude 5440",
            sources=[],  # NO CITATIONS -> MUST BE REJECTED
            confidence=0.8,
        )
    }

    res = validator.validate(fields)
    assert res.is_valid is False
    assert "model_no" in res.rejected_fields
    assert any(iss.issue_type == "MISSING_CITATION" for iss in res.issues)


def test_validator_fails_out_of_bounds_confidence():
    validator = ExtractionValidator(check_registry=False)
    fields = {
        "title": FieldResult.model_construct(
            value="Laptops",
            sources=[Citation(chunk_id="c1", file_name="rfp.pdf", page_number=1)],
            confidence=1.5,  # OUT OF RANGE via model_construct
        )
    }

    res = validator.validate(fields)
    assert res.is_valid is False
    assert "title" in res.rejected_fields
    assert any(iss.issue_type == "INVALID_CONFIDENCE" for iss in res.issues)


def test_retry_agent_repairs_rejected_field():
    tool = MagicMock()
    tool.search_rfp.return_value = [
        Evidence(
            chunk_id="chunk-repair-1",
            bid_id="Bid1",
            file_name="sample_rfp.pdf",
            page_number=2,
            document_type="rfp",
            text="Proposed laptop model: Dell Latitude 5440.",
        )
    ]

    retry_agent = RetryAgent(retrieval_tool=tool)
    initial_fields = {
        "model_no": FieldResult(value="Dell Latitude 5440", sources=[], confidence=0.8),
    }

    repaired_fields, new_count = retry_agent.run(
        bid_id="Bid1",
        rejected_fields=["model_no"],
        current_fields=initial_fields,
        retry_count=0,
    )

    assert new_count == 1
    repaired = repaired_fields["model_no"]
    assert repaired.value is not None
    assert len(repaired.sources) >= 1

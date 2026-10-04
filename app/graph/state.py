"""LangGraph state schema for multi-agent RFP extraction workflow."""

import operator
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict

from app.extraction.schemas import BidOutput
from app.reconciliation.models import AddendumChange
from app.schemas.canonical import FieldResult
from app.validation.models import ValidationResult


def merge_field_results(
    left: Dict[str, FieldResult],
    right: Dict[str, FieldResult],
) -> Dict[str, FieldResult]:
    """Reducer to merge extracted field results from parallel specialist agent branches."""
    merged = dict(left or {})
    merged.update(right or {})
    return merged


def append_changes(
    left: List[AddendumChange],
    right: List[AddendumChange],
) -> List[AddendumChange]:
    """Reducer to accumulate addendum changes."""
    return (left or []) + (right or [])


def append_strings(
    left: List[str],
    right: List[str],
) -> List[str]:
    """Reducer to accumulate error or trace logs."""
    return (left or []) + (right or [])


class RFPState(TypedDict):
    """Complete execution state for the LangGraph extraction pipeline."""

    bid_id: str
    extracted_fields: Annotated[Dict[str, FieldResult], merge_field_results]
    addendum_changes: Annotated[List[AddendumChange], append_changes]
    validation_result: Optional[ValidationResult]
    retry_count: int
    final_output: Optional[BidOutput]
    errors: Annotated[List[str], append_strings]

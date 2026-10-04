"""Unit tests for Phase 11 Addendum Reconciliation."""

import pytest
from unittest.mock import MagicMock

from app.agents.addendum_agent import AddendumAgent
from app.reconciliation.models import AddendumChange, ChangeType
from app.reconciliation.reconciler import AddendumReconciler
from app.schemas.canonical import Citation, Evidence, FieldResult, SearchResponse, SearchResult


def test_addendum_reconciler_with_no_addenda():
    engine = MagicMock()
    engine.search.return_value = SearchResponse(query="", total_results=0, results=[])

    reconciler = AddendumReconciler(search_engine=engine)
    original_fields = {
        "due_date": FieldResult(
            value="October 1, 2024",
            sources=[Citation(chunk_id="c1", file_name="rfp.pdf", page_number=2, text="Due Oct 1")],
            confidence=0.9,
        )
    }

    reconciled_fields, changes = reconciler.reconcile("Bid2", original_fields)
    assert len(changes) == 0
    assert reconciled_fields["due_date"].value == "October 1, 2024"


def test_addendum_reconciler_due_date_override():
    engine = MagicMock()
    ev = Evidence(
        chunk_id="addendum-chunk-2",
        bid_id="Bid1",
        file_name="Bid_1_Addendum_2.pdf",
        page_number=1,
        document_type="addendum",
        addendum_number=2,
        section="Amended Schedule",
        text="The proposal due date is now extended to October 10, 2024 at 2:00 PM CST.",
    )
    engine.search.return_value = SearchResponse(
        query="", total_results=1, results=[SearchResult(chunk_id=ev.chunk_id, rank=1, score=0.9, text=ev.text, retrieval_source="dense", evidence=ev)]
    )

    reconciler = AddendumReconciler(search_engine=engine)
    original_fields = {
        "due_date": FieldResult(
            value="October 1, 2024",
            sources=[Citation(chunk_id="c1", file_name="rfp.pdf", page_number=2, text="Due Oct 1")],
            confidence=0.85,
        )
    }

    reconciled_fields, changes = reconciler.reconcile("Bid1", original_fields)
    assert len(changes) == 1
    ch = changes[0]
    assert ch.field == "due_date"
    assert ch.change_type == ChangeType.MODIFICATION
    assert "October 10, 2024" in ch.new_value
    assert ch.addendum_number == 2
    assert "October 10, 2024" in reconciled_fields["due_date"].value


def test_addendum_agent_wrapper():
    tool = MagicMock()
    tool.search_rfp.return_value = []
    agent = AddendumAgent(reconciler=AddendumReconciler(retrieval_tool=tool))

    fields = {
        "title": FieldResult(value="Procurement", sources=[Citation(chunk_id="c1", file_name="rfp.pdf", page_number=1)])
    }
    reconciled, changes = agent.run("Bid1", fields)
    assert "title" in reconciled
    assert len(changes) == 0

"""Integration test for unseen bid discovery, ingestion, reconciliation, and extraction."""

import pytest
from app.graph.runner import RFPExtractionPipeline
from app.indexing.service import IndexingService
from scripts.test_unseen_bid import create_unseen_bid_fixture


def test_unseen_bid_e2e_pipeline(tmp_path):
    fixture_dir = create_unseen_bid_fixture()
    bid_id = "UnseenBid_Test"

    # 1. Indexing
    service = IndexingService()
    report = service.index_folder(str(fixture_dir), bid_id=bid_id)
    assert (report.files_new + report.files_unchanged + report.files_modified) == 4
    assert report.status == "success"

    # 2. Multi-Agent Extraction & Addendum Reconciliation
    pipeline = RFPExtractionPipeline()
    state = pipeline.run_extraction(bid_id)

    assert state["validation_result"].is_valid is True
    assert len(state["addendum_changes"]) >= 1

    due_change = [c for c in state["addendum_changes"] if c.field == "due_date"]
    assert len(due_change) == 1
    assert "November 30, 2024" in due_change[0].new_value

    final_output = state["final_output"].to_aliased_dict()
    assert "November 30, 2024" in final_output["Due Date"]["value"]
    assert len(final_output["Due Date"]["sources"]) >= 1

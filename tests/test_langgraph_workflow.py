"""End-to-end integration test for LangGraph multi-agent extraction workflow."""

import pytest
from app.extraction.schemas import BidOutput
from app.graph.runner import RFPExtractionPipeline
from app.graph.workflow import create_extraction_graph


def test_compiled_graph_structure():
    graph = create_extraction_graph()
    assert graph is not None
    # Verify graph node names exist
    node_names = list(graph.nodes.keys())
    assert "entity_specialist" in node_names
    assert "logistics_specialist" in node_names
    assert "product_specialist" in node_names
    assert "legal_specialist" in node_names
    assert "addendum_reconciler" in node_names
    assert "validator" in node_names
    assert "retry_agent" in node_names
    assert "serializer" in node_names


def test_extraction_pipeline_execution_bid1():
    pipeline = RFPExtractionPipeline()
    output = pipeline.extract_bid("Bid1")

    assert isinstance(output, BidOutput)
    # Check that all 20 fields are populated with FieldResults
    field_dict = output.model_dump()
    assert len(field_dict) == 20
    assert "due_date" in field_dict
    assert "bid_number" in field_dict
    assert "model_no" in field_dict
    assert "contract_or_cooperative" in field_dict

    # Check aliased dictionary export
    aliased = output.to_aliased_dict()
    assert "Due Date" in aliased
    assert "Bid Number" in aliased
    assert "Model_no" in aliased
    assert "Part_no" in aliased


def test_extraction_pipeline_execution_bid2():
    pipeline = RFPExtractionPipeline()
    output = pipeline.extract_bid("Bid2")

    assert isinstance(output, BidOutput)
    aliased = output.to_aliased_dict()
    assert len(aliased) == 20

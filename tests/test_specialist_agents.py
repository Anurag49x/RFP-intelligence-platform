"""Unit tests for specialist extraction agents (Logistics, Product, Legal, Entity)."""

import pytest
from unittest.mock import MagicMock

from app.agents.entity_agent import EntitySpecialistAgent
from app.agents.legal_agent import LegalSpecialistAgent
from app.agents.logistics_agent import LogisticsSpecialistAgent
from app.agents.product_agent import ProductSpecialistAgent
from app.schemas.canonical import Citation, Evidence, FieldResult


@pytest.fixture
def mock_retrieval_tool():
    tool = MagicMock()
    # Return mock evidence chunks
    mock_evidence = [
        Evidence(
            chunk_id="chunk-101",
            bid_id="Bid1",
            file_name="sample_rfp.pdf",
            page_number=3,
            document_type="rfp",
            section="Schedule",
            text="Proposals are due on October 1, 2024. Contact: procurement@dallasisd.org.",
        ),
        Evidence(
            chunk_id="chunk-102",
            bid_id="Bid1",
            file_name="sample_spec.pdf",
            page_number=1,
            document_type="spec",
            section="Hardware",
            text="Proposed laptop model: Dell Latitude 5440 with Thunderbolt Dock WD22TB4.",
        ),
    ]
    tool.search_rfp.return_value = mock_evidence
    return tool


def test_logistics_agent(mock_retrieval_tool):
    agent = LogisticsSpecialistAgent(retrieval_tool=mock_retrieval_tool)
    results = agent.extract("Bid1")
    
    assert isinstance(results, dict)
    for field in agent.fields:
        assert field in results
        assert isinstance(results[field], FieldResult)
    
    assert "due_date" in results
    assert "bid_submission_type" in results


def test_product_agent(mock_retrieval_tool):
    agent = ProductSpecialistAgent(retrieval_tool=mock_retrieval_tool)
    results = agent.extract("Bid1")
    
    assert isinstance(results, dict)
    for field in agent.fields:
        assert field in results
        assert isinstance(results[field], FieldResult)

    assert "model_no" in results
    assert "part_no" in results


def test_legal_agent(mock_retrieval_tool):
    agent = LegalSpecialistAgent(retrieval_tool=mock_retrieval_tool)
    results = agent.extract("Bid1")
    
    assert isinstance(results, dict)
    for field in agent.fields:
        assert field in results
        assert isinstance(results[field], FieldResult)

    assert "bid_bond_requirement" in results
    assert "additional_documentation" in results


def test_entity_agent(mock_retrieval_tool):
    agent = EntitySpecialistAgent(retrieval_tool=mock_retrieval_tool)
    results = agent.extract("Bid1")
    
    assert isinstance(results, dict)
    for field in agent.fields:
        assert field in results
        assert isinstance(results[field], FieldResult)

    assert "bid_number" in results
    assert "title" in results

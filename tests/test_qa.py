"""Unit and integration tests for Phase 13 Grounded Q&A Engine."""

import pytest
from app.qa.engine import QAEngine
from app.qa.models import AskRequest, AskResponse, QueryIntent, QueryUnderstandingEngine


def test_query_understanding_intent_classification():
    q1 = QueryUnderstandingEngine.analyze("What is the final deadline for Bid1?")
    assert q1["intent"] == QueryIntent.ADDENDUM_AWARE
    assert "Bid1" in q1["target_bids"]

    q2 = QueryUnderstandingEngine.analyze("Compare warranty requirements between Bid1 and Bid2.")
    assert q2["intent"] == QueryIntent.CROSS_BID_COMPARISON
    assert "Bid1" in q2["target_bids"]
    assert "Bid2" in q2["target_bids"]

    q3 = QueryUnderstandingEngine.analyze("What is PORFP #E20P4600040?")
    assert "E20P4600040" in q3["extracted_identifiers"]


def test_qa_engine_deadline_bid1():
    engine = QAEngine()
    req = AskRequest(question="What is the final deadline for Bid1?", bid_id="Bid1")
    resp = engine.answer_question(req)

    assert isinstance(resp, AskResponse)
    assert any(term in resp.answer.lower() for term in ["july 9, 2024", "october 10, 2024", "due", "deadline", "date"])
    assert len(resp.citations) >= 1
    assert resp.confidence > 0.7
    assert resp.validation_status in ["passed", "repaired"]


def test_qa_engine_affidavits_bid2():
    engine = QAEngine()
    req = AskRequest(question="Which affidavits are required for Bid2?", bid_id="Bid2")
    resp = engine.answer_question(req)

    assert isinstance(resp, AskResponse)
    assert "affidavit" in resp.answer.lower()
    assert len(resp.citations) >= 1
    assert resp.confidence > 0.7


def test_qa_engine_what_changed_addendum2():
    engine = QAEngine()
    req = AskRequest(question="What changed in Addendum 2?", bid_id="Bid1")
    resp = engine.answer_question(req)

    assert isinstance(resp, AskResponse)
    assert "Addendum 2" in resp.answer or "due date" in resp.answer.lower()
    assert len(resp.citations) >= 1


def test_qa_engine_compare_warranty():
    engine = QAEngine()
    req = AskRequest(question="Compare warranty requirements between Bid1 and Bid2.")
    resp = engine.answer_question(req)

    assert isinstance(resp, AskResponse)
    assert "warranty" in resp.answer.lower()
    assert len(resp.citations) >= 1


def test_qa_engine_negative_question_not_found():
    engine = QAEngine()
    req = AskRequest(question="What is the required employee headcount for the vendor?", bid_id="Bid1")
    resp = engine.answer_question(req)

    assert isinstance(resp, AskResponse)
    assert resp.answer.strip() == "Not found in documents."
    assert resp.confidence == 0.0
    assert resp.validation_status == "not_found"

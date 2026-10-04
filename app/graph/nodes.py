"""LangGraph node functions for the multi-agent RFP extraction workflow."""

from typing import Any, Dict
from app.agents.addendum_agent import AddendumAgent
from app.agents.entity_agent import EntitySpecialistAgent
from app.agents.legal_agent import LegalSpecialistAgent
from app.agents.logistics_agent import LogisticsSpecialistAgent
from app.agents.product_agent import ProductSpecialistAgent
from app.agents.retry_agent import RetryAgent
from app.agents.validator_agent import ValidatorAgent
from app.extraction.schemas import BidOutput
from app.graph.state import RFPState
from app.logging import logger


def entity_node(state: RFPState) -> Dict[str, Any]:
    """Execute EntitySpecialistAgent to extract bid metadata, agency, and title."""
    bid_id = state["bid_id"]
    agent = EntitySpecialistAgent()
    extracted = agent.extract(bid_id)
    return {"extracted_fields": extracted}


def logistics_node(state: RFPState) -> Dict[str, Any]:
    """Execute LogisticsSpecialistAgent to extract timeline, delivery, and submission logistics."""
    bid_id = state["bid_id"]
    agent = LogisticsSpecialistAgent()
    extracted = agent.extract(bid_id)
    return {"extracted_fields": extracted}


def product_node(state: RFPState) -> Dict[str, Any]:
    """Execute ProductSpecialistAgent to extract hardware, model, and technical specifications."""
    bid_id = state["bid_id"]
    agent = ProductSpecialistAgent()
    extracted = agent.extract(bid_id)
    return {"extracted_fields": extracted}


def legal_node(state: RFPState) -> Dict[str, Any]:
    """Execute LegalSpecialistAgent to extract bonds, required affidavits, and purchasing vehicles."""
    bid_id = state["bid_id"]
    agent = LegalSpecialistAgent()
    extracted = agent.extract(bid_id)
    return {"extracted_fields": extracted}


def addendum_node(state: RFPState) -> Dict[str, Any]:
    """Execute AddendumAgent to reconcile extracted fields with addenda revisions."""
    bid_id = state["bid_id"]
    extracted = state.get("extracted_fields", {})
    agent = AddendumAgent()
    reconciled_fields, changes = agent.run(bid_id, extracted)
    return {
        "extracted_fields": reconciled_fields,
        "addendum_changes": changes,
    }


def validator_node(state: RFPState) -> Dict[str, Any]:
    """Execute ValidatorAgent to verify evidence grounding and citation integrity."""
    bid_id = state["bid_id"]
    extracted = state.get("extracted_fields", {})
    agent = ValidatorAgent()
    val_result = agent.run(bid_id, extracted)
    return {"validation_result": val_result}


def retry_node(state: RFPState) -> Dict[str, Any]:
    """Execute RetryAgent for targeted re-retrieval on rejected fields."""
    bid_id = state["bid_id"]
    extracted = state.get("extracted_fields", {})
    val_result = state.get("validation_result")
    retry_count = state.get("retry_count", 0)
    rejected_fields = val_result.rejected_fields if val_result else []

    agent = RetryAgent()
    updated_fields, new_retry_count = agent.run(
        bid_id=bid_id,
        rejected_fields=rejected_fields,
        current_fields=extracted,
        retry_count=retry_count,
    )
    return {
        "extracted_fields": updated_fields,
        "retry_count": new_retry_count,
    }


def serialization_node(state: RFPState) -> Dict[str, Any]:
    """Construct final canonical BidOutput record from validated fields."""
    extracted = state.get("extracted_fields", {})
    bid_output = BidOutput.from_field_dict(extracted)
    logger.info(f"Serialization complete for bid '{state['bid_id']}'")
    return {"final_output": bid_output}

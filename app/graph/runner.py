"""Execution engine and entrypoint for multi-agent RFP extraction."""

from typing import Any, Dict, Optional
from app.evidence.store import EvidenceStore
from app.extraction.schemas import BidOutput
from app.graph.state import RFPState
from app.graph.workflow import create_extraction_graph
from app.logging import logger


class RFPExtractionPipeline:
    """High-level multi-agent extraction pipeline running the compiled LangGraph workflow."""

    def __init__(self):
        self.graph = create_extraction_graph()

    def run_extraction(self, bid_id: str) -> RFPState:
        """Execute the complete multi-agent workflow for a specific bid."""
        logger.info(f"--- Starting Multi-Agent RFP Extraction for '{bid_id}' ---")

        initial_state: RFPState = {
            "bid_id": bid_id,
            "extracted_fields": {},
            "addendum_changes": [],
            "validation_result": None,
            "retry_count": 0,
            "final_output": None,
            "errors": [],
        }

        final_state = self.graph.invoke(initial_state)
        logger.info(f"--- Multi-Agent RFP Extraction completed for '{bid_id}' ---")
        return final_state

    def extract_bid(self, bid_id: str) -> BidOutput:
        """Extract structured 20-field BidOutput record for a specific bid."""
        state = self.run_extraction(bid_id)
        final_output = state.get("final_output")
        if not final_output:
            # Fallback to constructing from extracted_fields
            final_output = BidOutput.from_field_dict(state.get("extracted_fields", {}))
        return final_output

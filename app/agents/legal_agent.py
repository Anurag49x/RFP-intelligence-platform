"""Legal, compliance, and affidavit specialist extraction agent."""

from typing import Dict, List, Optional
from app.agents.retrieval_tool import RetrievalTool
from app.extraction.field_map import FIELD_TARGETED_QUERIES, LEGAL_FIELDS
from app.extraction.llm import LLMExtractor
from app.logging import logger
from app.schemas.canonical import Evidence, FieldResult


class LegalSpecialistAgent:
    """Specialist agent responsible for extracting bonds, required affidavits, and contract/cooperative vehicles."""

    def __init__(
        self,
        retrieval_tool: Optional[RetrievalTool] = None,
        llm_extractor: Optional[LLMExtractor] = None,
    ):
        self.retrieval_tool = retrieval_tool or RetrievalTool()
        self.llm_extractor = llm_extractor or LLMExtractor()
        self.fields = LEGAL_FIELDS

    def extract(self, bid_id: str) -> Dict[str, FieldResult]:
        """Retrieve evidence and extract all legal/compliance fields for the specified bid."""
        logger.info(f"LegalSpecialistAgent executing for bid '{bid_id}' (Fields: {self.fields})")

        # Collect targeted evidence passages for legal fields
        evidence_map: Dict[str, Evidence] = {}
        for field in self.fields:
            queries = FIELD_TARGETED_QUERIES.get(field, [field.replace("_", " ")])
            for query in queries:
                results = self.retrieval_tool.search_rfp(
                    query=query,
                    bid_id=bid_id,
                    top_k=4,
                    use_reranker=False,
                )
                for ev in results:
                    if ev.chunk_id not in evidence_map:
                        evidence_map[ev.chunk_id] = ev

        evidence_passages = list(evidence_map.values())
        logger.info(
            f"LegalSpecialistAgent gathered {len(evidence_passages)} distinct evidence chunks for '{bid_id}'"
        )

        extracted = self.llm_extractor.extract_fields(
            field_names=self.fields,
            evidence_passages=evidence_passages,
            bid_id=bid_id,
        )
        return extracted

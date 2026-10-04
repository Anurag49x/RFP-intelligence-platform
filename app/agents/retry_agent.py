"""Targeted retry agent for repairing rejected extraction fields."""

from typing import Dict, List, Optional, Tuple
from app.agents.retrieval_tool import RetrievalTool
from app.evidence.store import EvidenceStore
from app.extraction.field_map import FIELD_TARGETED_QUERIES
from app.extraction.llm import LLMExtractor
from app.logging import logger
from app.schemas.canonical import Evidence, FieldResult


class RetryAgent:
    """Agent node responsible for targeted re-retrieval and re-extraction of rejected fields."""

    def __init__(
        self,
        retrieval_tool: Optional[RetrievalTool] = None,
        llm_extractor: Optional[LLMExtractor] = None,
        max_retries: int = 2,
    ):
        self.retrieval_tool = retrieval_tool or RetrievalTool()
        self.llm_extractor = llm_extractor or LLMExtractor()
        self.max_retries = max_retries

    def run(
        self,
        bid_id: str,
        rejected_fields: List[str],
        current_fields: Dict[str, FieldResult],
        retry_count: int,
    ) -> Tuple[Dict[str, FieldResult], int]:
        """Execute targeted re-retrieval with expanded queries for rejected fields."""
        new_retry_count = retry_count + 1
        logger.info(
            f"RetryAgent executing attempt {new_retry_count}/{self.max_retries} for rejected fields: {rejected_fields}"
        )

        updated_fields = dict(current_fields)

        for field in rejected_fields:
            queries = FIELD_TARGETED_QUERIES.get(field, [field.replace("_", " ")])
            # Expanded fallback query
            expanded_queries = queries + [f"all details specifications for {field.replace('_', ' ')}"]
            
            evidence_map: Dict[str, Evidence] = {}
            for q in expanded_queries:
                passages = self.retrieval_tool.search_rfp(
                    query=q,
                    bid_id=bid_id,
                    top_k=6,
                    use_reranker=False,
                )
                for p in passages:
                    if p.chunk_id not in evidence_map:
                        evidence_map[p.chunk_id] = p

            ev_list = list(evidence_map.values())
            logger.info(f"RetryAgent found {len(ev_list)} candidate chunks for rejected field '{field}'")

            re_extracted = self.llm_extractor.extract_fields(
                field_names=[field],
                evidence_passages=ev_list,
                bid_id=bid_id,
            )

            res = re_extracted.get(field)
            if res and res.value is not None and res.sources:
                # Re-extraction succeeded with verified sources
                updated_fields[field] = res
                logger.info(f"RetryAgent successfully repaired field '{field}': '{res.value}'")
            else:
                # If still ungrounded or absent, enforce null safety
                updated_fields[field] = FieldResult(
                    value=None,
                    sources=[],
                    confidence=0.0,
                    notes=f"Unresolved after retry attempt {new_retry_count}: Not found in documents.",
                )
                logger.info(f"RetryAgent resolved '{field}' to null (no verifiable evidence).")

        return updated_fields, new_retry_count

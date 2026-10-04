"""Targeted retrieval tool for specialist extraction agents."""

from typing import List, Optional
from app.logging import logger
from app.retrieval.hybrid import HybridSearchEngine
from app.schemas.canonical import Evidence, SearchFilters


class RetrievalTool:
    """Provides targeted document retrieval with metadata filtering for extraction agents."""

    def __init__(self, search_engine: Optional[HybridSearchEngine] = None):
        self.search_engine = search_engine or HybridSearchEngine()

    def search_rfp(
        self,
        query: str,
        bid_id: str,
        document_type: Optional[str] = None,
        top_k: int = 5,
        use_reranker: bool = True,
    ) -> List[Evidence]:
        """Perform targeted hybrid retrieval and reranking for a specific bid and query.

        Args:
            query: Natural language or keyword query string.
            bid_id: Target bid identifier (e.g. 'Bid1', 'Bid2').
            document_type: Optional filter for document type ('rfp', 'addendum', 'spec', 'affidavit').
            top_k: Number of evidence passages to return.
            use_reranker: Whether to apply Jina reranker.

        Returns:
            List of Evidence objects with full citation provenance.
        """
        try:
            filters = SearchFilters(
                bid_id=bid_id,
                document_type=document_type,
            )
            response = self.search_engine.search(
                query=query,
                top_k=top_k,
                filters=filters,
                use_reranker=use_reranker,
            )
            # Extract underlying Evidence objects from SearchResults
            evidence_list: List[Evidence] = []
            for item in response.results:
                if hasattr(item, "evidence") and item.evidence:
                    evidence_list.append(item.evidence)
                elif isinstance(item, Evidence):
                    evidence_list.append(item)
            return evidence_list
        except Exception as e:
            logger.error(f"RetrievalTool error for bid '{bid_id}' query '{query}': {e}")
            return []

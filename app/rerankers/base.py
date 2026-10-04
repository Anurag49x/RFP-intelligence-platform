"""Abstract base interface for document reranker providers."""

from abc import ABC, abstractmethod
from typing import List

from app.schemas.canonical import SearchResult


class RerankerProvider(ABC):
    """Abstract interface for listwise and cross-encoder document rerankers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the reranker model in use."""
        pass

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 5,
    ) -> List[SearchResult]:
        """Rerank candidate search results against the query and return the top_k.

        Args:
            query: The user query string.
            candidates: Retrieved candidates from first-stage retrieval (e.g. RRF).
            top_k: Maximum number of reranked results to return.

        Returns:
            Reranked list of SearchResult items with updated rank, rerank_score,
            and preserved previous_score & evidence provenance.
        """
        pass

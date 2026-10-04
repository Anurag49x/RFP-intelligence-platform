"""Abstract base class for Vector Store implementations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.schemas.canonical import Chunk, SearchFilters, SearchResult


class VectorStore(ABC):
    """Interface for vector database operations."""

    @abstractmethod
    def create_collection_if_not_exists(self, collection_name: str, dimension: int):
        """Create vector collection if it does not exist."""
        pass

    @abstractmethod
    def upsert_chunks(
        self,
        collection_name: str,
        chunks: List[Chunk],
        vectors: List[List[float]],
    ) -> int:
        """Upsert chunks with vectors into the collection. Returns count of upserted points."""
        pass

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 20,
        filters: Optional[SearchFilters] = None,
    ) -> List[SearchResult]:
        """Perform similarity search with optional metadata filtering."""
        pass

    @abstractmethod
    def count(self, collection_name: str) -> int:
        """Return the number of points in the collection."""
        pass

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        pass

    @abstractmethod
    def delete_chunks(self, collection_name: str, chunk_ids: List[str]) -> int:
        """Delete specific chunks from the vector store collection by chunk_id."""
        pass


import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient, models

from app.config import get_settings
from app.logging import logger
from app.schemas.canonical import Chunk, Evidence, SearchFilters, SearchResult
from app.vectorstore.base import VectorStore

_CLIENT_CACHE: Dict[str, QdrantClient] = {}
_CLIENT_LOCK = threading.Lock()


class QdrantVectorStore(VectorStore):
    """Qdrant vector database implementation with deterministic point IDs and native filtering."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        local_path: Optional[str] = "outputs/qdrant_storage",
        prefer_local_fallback: bool = True,
    ):
        settings = get_settings()
        target_url = url or settings.qdrant_url
        target_api_key = api_key or settings.qdrant_api_key

        self.client: QdrantClient
        self.is_embedded = False

        # Attempt remote connection first if URL is configured
        connected = False
        if target_url and not prefer_local_fallback:
            try:
                cache_key = f"remote:{target_url}"
                with _CLIENT_LOCK:
                    if cache_key not in _CLIENT_CACHE:
                        _CLIENT_CACHE[cache_key] = QdrantClient(url=target_url, api_key=target_api_key, timeout=5.0)
                    self.client = _CLIENT_CACHE[cache_key]
                self.client.get_collections()
                connected = True
                logger.info(f"Connected to Qdrant server at {target_url}")
            except Exception as e:
                logger.warning(f"Could not connect to Qdrant server at {target_url}: {str(e)}")

        # Fallback to local persistent disk storage
        if not connected:
            if local_path == ":memory:":
                self.client = QdrantClient(":memory:")
                self.is_embedded = True
                logger.info("Initialized ephemeral in-memory Qdrant instance")
            else:
                storage_dir = Path(local_path or "outputs/qdrant_storage").resolve()
                storage_dir.mkdir(parents=True, exist_ok=True)
                cache_key = f"local:{str(storage_dir)}"
                with _CLIENT_LOCK:
                    if cache_key not in _CLIENT_CACHE:
                        try:
                            _CLIENT_CACHE[cache_key] = QdrantClient(path=str(storage_dir))
                        except Exception as lock_err:
                            logger.warning(
                                f"Storage dir {storage_dir} is locked by another process ({lock_err}). Falling back to ephemeral client."
                            )
                            _CLIENT_CACHE[cache_key] = QdrantClient(":memory:")
                    self.client = _CLIENT_CACHE[cache_key]
                self.is_embedded = True
                logger.info(f"Initialized local Qdrant instance at {storage_dir}")


    @staticmethod
    def chunk_id_to_point_id(chunk_id: str) -> str:
        """Derive a deterministic UUID from chunk_id for stable point identity."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists in Qdrant."""
        try:
            return self.client.collection_exists(collection_name=collection_name)
        except Exception:
            return False

    def create_collection_if_not_exists(self, collection_name: str, dimension: int = 1024):
        """Create a collection configured for cosine distance if it does not exist."""
        if not self.collection_exists(collection_name):
            logger.info(f"Creating Qdrant collection: {collection_name} (dimension={dimension})")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE,
                ),
            )

    def upsert_chunks(
        self,
        collection_name: str,
        chunks: List[Chunk],
        vectors: List[List[float]],
        batch_size: int = 100,
    ) -> int:
        """Upsert chunks with vectors into Qdrant in batches."""
        if not chunks or not vectors or len(chunks) != len(vectors):
            raise ValueError("Chunks and vectors must be non-empty and of equal length.")

        dimension = len(vectors[0])
        self.create_collection_if_not_exists(collection_name, dimension=dimension)

        points: List[models.PointStruct] = []
        for chunk, vector in zip(chunks, vectors):
            point_id = self.chunk_id_to_point_id(chunk.chunk_id)
            payload = {
                "chunk_id": chunk.chunk_id,
                "bid_id": chunk.bid_id,
                "file_name": chunk.file_name,
                "document_type": chunk.document_type,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "addendum_number": chunk.addendum_number,
                "chunk_type": chunk.chunk_type,
                "token_count": chunk.token_count,
                "source_order": chunk.source_order,
                "text": chunk.text,
                "metadata": chunk.metadata,
            }
            points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))

        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(collection_name=collection_name, points=batch)
            total_upserted += len(batch)

        logger.info(f"Upserted {total_upserted} points into Qdrant collection: {collection_name}")
        return total_upserted

    def _build_filter(self, filters: Optional[SearchFilters]) -> Optional[models.Filter]:
        """Convert SearchFilters into Qdrant native Filter object."""
        if not filters:
            return None

        conditions = []
        if filters.bid_id:
            conditions.append(
                models.FieldCondition(key="bid_id", match=models.MatchValue(value=filters.bid_id))
            )
        if filters.document_type:
            conditions.append(
                models.FieldCondition(
                    key="document_type", match=models.MatchValue(value=filters.document_type)
                )
            )
        if filters.addendum_number is not None:
            conditions.append(
                models.FieldCondition(
                    key="addendum_number", match=models.MatchValue(value=filters.addendum_number)
                )
            )
        if filters.file_name:
            conditions.append(
                models.FieldCondition(key="file_name", match=models.MatchValue(value=filters.file_name))
            )

        return models.Filter(must=conditions) if conditions else None

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 20,
        filters: Optional[SearchFilters] = None,
    ) -> List[SearchResult]:
        """Perform cosine similarity vector search with optional payload filtering."""
        if not self.collection_exists(collection_name):
            logger.warning(f"Collection {collection_name} does not exist for search")
            return []

        qdrant_filter = self._build_filter(filters)

        try:
            query_res = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
                with_payload=True,
            )
            scored_points = query_res.points
        except Exception as e:
            logger.error(f"Qdrant search error in collection {collection_name}: {str(e)}")
            return []

        results: List[SearchResult] = []
        for rank_idx, point in enumerate(scored_points, start=1):
            p = point.payload or {}
            evidence = Evidence(
                bid_id=p.get("bid_id", ""),
                file_name=p.get("file_name", ""),
                page_number=p.get("page_number", 1),
                chunk_id=p.get("chunk_id", str(point.id)),
                text=p.get("text", ""),
                document_type=p.get("document_type", "other"),
                section=p.get("section"),
                addendum_number=p.get("addendum_number"),
                document_date=(p.get("metadata") or {}).get("document_date"),
                chunk_type=p.get("chunk_type", "text"),
                score=float(point.score),
                rank=rank_idx,
                retrieval_source="dense",
            )
            results.append(
                SearchResult(
                    rank=rank_idx,
                    chunk_id=evidence.chunk_id,
                    text=evidence.text,
                    score=float(point.score),
                    retrieval_source="dense",
                    evidence=evidence,
                )
            )

        return results

    def count(self, collection_name: str) -> int:
        """Return total number of points in the collection."""
        if not self.collection_exists(collection_name):
            return 0
        try:
            return self.client.count(collection_name=collection_name).count
        except Exception:
            return 0

    def delete_chunks(self, collection_name: str, chunk_ids: List[str]) -> int:
        """Delete specific points from Qdrant by deterministic chunk_id point UUIDs."""
        if not chunk_ids or not self.collection_exists(collection_name):
            return 0

        point_ids = [self.chunk_id_to_point_id(cid) for cid in chunk_ids]
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(points=point_ids),
            )
            logger.info(f"Deleted {len(point_ids)} points from Qdrant collection: {collection_name}")
            return len(point_ids)
        except Exception as e:
            logger.error(f"Failed to delete points from Qdrant collection {collection_name}: {e}")
            return 0


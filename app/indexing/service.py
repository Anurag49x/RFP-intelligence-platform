"""Unified Indexing Service orchestrating Ingestion -> Chunking -> Embedding -> Qdrant & BM25 with incremental sync."""

from pathlib import Path
from typing import Optional

from app.embeddings.base import EmbeddingProvider
from app.embeddings.cache import EmbeddingCache
from app.indexing.manager import IndexingReport, IndexManager
from app.indexing.registry import DocumentRegistry
from app.ingestion.ocr import OCRProvider
from app.lexical.bm25 import BM25Index
from app.vectorstore.base import VectorStore


class IndexingService:
    """Production indexing service connecting all pipeline stages with persistent caching and incremental sync."""

    def __init__(
        self,
        registry: Optional[DocumentRegistry] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        embedding_cache: Optional[EmbeddingCache] = None,
        vector_store: Optional[VectorStore] = None,
        bm25_index: Optional[BM25Index] = None,
        collection_name: str = "rfp_chunks",
        bm25_corpus_path: str | Path = "data/bm25/corpus.jsonl",
    ):
        self.manager = IndexManager(
            registry=registry,
            embedding_provider=embedding_provider,
            embedding_cache=embedding_cache,
            vector_store=vector_store,
            bm25_index=bm25_index,
            collection_name=collection_name,
            bm25_corpus_path=bm25_corpus_path,
        )

    def index_folder(
        self,
        folder_path: str | Path,
        bid_id: Optional[str] = None,
        ocr_provider: Optional[OCRProvider] = None,
    ) -> IndexingReport:
        """Execute incremental sync on a document directory."""
        return self.manager.sync_folder(
            folder_path=folder_path,
            bid_id=bid_id,
            ocr_provider=ocr_provider,
        )

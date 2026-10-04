"""Incremental Index Manager orchestrating document discovery, change detection, and selective re-indexing."""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from app.chunking.chunker import DocumentChunker
from app.chunking.storage import load_chunks, save_chunks
from app.config import get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.cache import EmbeddingCache
from app.embeddings.jina import JinaEmbeddingProvider
from app.indexing.hashing import compute_file_hash
from app.indexing.registry import DocumentRecord, DocumentRegistry
from app.ingestion.discovery import FileDiscovery
from app.ingestion.ocr import OCRProvider
from app.ingestion.service import IngestionService
from app.lexical.bm25 import BM25Index
from app.logging import logger
from app.schemas.canonical import Chunk, Document
from app.vectorstore.base import VectorStore
from app.vectorstore.qdrant import QdrantVectorStore


class IndexingReport(BaseModel):
    """Detailed metrics report of incremental document indexing operations."""

    status: str = "success"
    bid_id: str
    folder_path: str
    files_new: int = 0
    files_unchanged: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    chunks_added: int = 0
    chunks_removed: int = 0
    chunks_created: int = 0
    embeddings_created: int = 0
    embeddings_requested: int = 0
    embedding_cache_hits: int = 0
    embeddings_cached: int = 0
    vectors_upserted: int = 0
    bm25_indexed_chunks: int = 0
    elapsed_seconds: float = 0.0
    errors: List[str] = Field(default_factory=list)



class IndexManager:
    """Production Incremental Index Manager orchestrating change detection, cache reuse, and index cleanup."""

    CHUNKING_VERSION = "v1"

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
        settings = get_settings()
        self.registry = registry or DocumentRegistry()
        self.embedding_provider = embedding_provider or JinaEmbeddingProvider()
        self.embedding_cache = embedding_cache or EmbeddingCache()
        self.vector_store = vector_store or QdrantVectorStore()
        self.bm25_index = bm25_index or BM25Index.load(bm25_corpus_path)
        self.collection_name = collection_name
        self.bm25_corpus_path = Path(bm25_corpus_path)
        self.embedding_model = self.embedding_provider.model_name

    def sync_folder(
        self,
        folder_path: str | Path,
        bid_id: Optional[str] = None,
        ocr_provider: Optional[OCRProvider] = None,
    ) -> IndexingReport:
        """Synchronize an RFP bid folder incrementally against registry, Qdrant, and BM25."""
        start_time = time.time()
        target_dir = Path(folder_path).resolve()
        resolved_bid = bid_id or target_dir.name

        logger.info(f"Starting incremental sync for {resolved_bid} at {target_dir}")

        # 1. Discover current physical files
        try:
            discovered_files = FileDiscovery.discover_files(target_dir, bid_id=resolved_bid)
        except Exception as e:
            logger.error(f"Discovery error in {target_dir}: {e}")
            return IndexingReport(
                status="error",
                bid_id=resolved_bid,
                folder_path=str(target_dir),
                errors=[str(e)],
                elapsed_seconds=round(time.time() - start_time, 2),
            )

        current_disk_paths = {str(Path(f.file_path).resolve()): Path(f.file_path) for f in discovered_files}


        # 2. Query registry for previously indexed files of this bid
        existing_records = {r.file_path: r for r in self.registry.get_records_by_bid(resolved_bid)}

        files_new: List[Path] = []
        files_unchanged: List[Path] = []
        files_modified: List[Path] = []
        files_deleted: List[DocumentRecord] = []

        # Check for deleted files (in registry but missing on disk)
        for path_str, rec in existing_records.items():
            if path_str not in current_disk_paths:
                files_deleted.append(rec)

        # Check for new, modified, or unchanged files
        for path_str, file_path in current_disk_paths.items():
            current_hash = compute_file_hash(file_path)
            rec = existing_records.get(path_str)

            if not rec:
                files_new.append(file_path)
            elif (
                rec.file_hash != current_hash
                or rec.chunking_version != self.CHUNKING_VERSION
                or rec.embedding_model != self.embedding_model
            ):
                files_modified.append(file_path)
            else:
                files_unchanged.append(file_path)

        logger.info(
            f"Sync change detection for {resolved_bid}: "
            f"new={len(files_new)}, unchanged={len(files_unchanged)}, "
            f"modified={len(files_modified)}, deleted={len(files_deleted)}"
        )

        total_chunks_removed = 0
        total_chunks_added = 0
        total_embeddings_created = 0
        total_embeddings_cached = 0
        total_vectors_upserted = 0
        sync_errors: List[str] = []

        # 3. Handle Deleted Files: Cleanup Qdrant, BM25, and Registry
        for del_rec in files_deleted:
            if del_rec.chunk_ids:
                logger.info(f"Removing {len(del_rec.chunk_ids)} chunks for deleted file: {del_rec.file_name}")
                self.vector_store.delete_chunks(self.collection_name, del_rec.chunk_ids)
                self.bm25_index.remove_chunks(del_rec.chunk_ids)
                total_chunks_removed += len(del_rec.chunk_ids)
            self.registry.delete_record(del_rec.file_path)

        # 4. Handle Modified Files: Purge stale chunks first
        for mod_path in files_modified:
            mod_path_str = str(mod_path.resolve())
            old_rec = existing_records.get(mod_path_str)
            if old_rec and old_rec.chunk_ids:
                logger.info(f"Purging {len(old_rec.chunk_ids)} stale chunks for modified file: {old_rec.file_name}")
                self.vector_store.delete_chunks(self.collection_name, old_rec.chunk_ids)
                self.bm25_index.remove_chunks(old_rec.chunk_ids)
                total_chunks_removed += len(old_rec.chunk_ids)

        # 5. Ingest and Process New + Modified Files
        files_to_process = files_new + files_modified
        new_chunks_to_upsert: List[Chunk] = []

        if files_to_process:
            chunker = DocumentChunker()
            for fp in files_to_process:
                try:
                    # Ingest single file
                    single_doc_result = IngestionService.ingest_folder(
                        folder_path=target_dir,
                        bid_id=resolved_bid,
                        ocr_provider=ocr_provider,
                    )
                    # Locate document matching this file
                    matching_docs = [d for d in single_doc_result.documents if Path(d.metadata.source_path).resolve() == fp.resolve()]
                    if not matching_docs:
                        continue
                    doc = matching_docs[0]

                    # Chunk document
                    doc_chunks = chunker.chunk_document(doc)
                    new_chunks_to_upsert.extend(doc_chunks)

                    # Update registry entry for this document
                    doc_chunk_ids = [c.chunk_id for c in doc_chunks]
                    record = DocumentRecord(
                        file_path=str(fp.resolve()),
                        file_name=fp.name,
                        bid_id=resolved_bid,
                        file_hash=compute_file_hash(fp),
                        file_size=fp.stat().st_size,
                        modified_time=fp.stat().st_mtime,
                        document_type=doc.metadata.doc_type,
                        addendum_number=doc.metadata.addendum_number,
                        chunk_ids=doc_chunk_ids,
                        chunking_version=self.CHUNKING_VERSION,
                        embedding_model=self.embedding_model,
                        status="indexed",
                    )
                    self.registry.upsert_record(record)

                except Exception as e:
                    logger.error(f"Failed to process file {fp.name}: {e}")
                    sync_errors.append(f"{fp.name}: {str(e)}")

        # 6. Embed and Index New/Modified Chunks (with embedding cache lookup)
        if new_chunks_to_upsert:
            cache_keys = [
                EmbeddingCache.compute_cache_key(self.embedding_model, c.text)
                for c in new_chunks_to_upsert
            ]
            cached_map = self.embedding_cache.get_batch(cache_keys)
            cache_hits = len(cached_map)
            cache_misses = len(new_chunks_to_upsert) - cache_hits
            total_embeddings_cached += cache_hits
            total_embeddings_created += cache_misses

            miss_indices = [i for i, k in enumerate(cache_keys) if k not in cached_map]
            newly_embedded: List[List[float]] = []

            if miss_indices:
                miss_texts = [new_chunks_to_upsert[i].text for i in miss_indices]
                logger.info(f"Generating {len(miss_texts)} new embeddings for {resolved_bid}...")
                newly_embedded = self.embedding_provider.embed_documents(miss_texts)

                # Persist new embeddings in SQLite cache
                cache_records = [
                    (cache_keys[idx], self.embedding_model, new_chunks_to_upsert[idx].chunk_id, vec)
                    for idx, vec in zip(miss_indices, newly_embedded)
                ]
                self.embedding_cache.set_batch(cache_records)

            # Build full vector list
            all_vectors: List[List[float]] = []
            miss_iter = iter(newly_embedded)
            for key in cache_keys:
                if key in cached_map:
                    all_vectors.append(cached_map[key])
                else:
                    all_vectors.append(next(miss_iter))

            # Upsert into Qdrant
            try:
                upserted = self.vector_store.upsert_chunks(
                    collection_name=self.collection_name,
                    chunks=new_chunks_to_upsert,
                    vectors=all_vectors,
                )
                total_vectors_upserted += upserted
            except Exception as e:
                logger.error(f"Failed to upsert to Qdrant: {e}")
                sync_errors.append(f"Qdrant upsert: {str(e)}")

            # Update BM25 index
            self.bm25_index.add_chunks(new_chunks_to_upsert)
            total_chunks_added += len(new_chunks_to_upsert)

        # 7. Persist updated BM25 corpus & all current chunks for this bid
        if files_to_process or files_deleted:
            self.bm25_index.save(self.bm25_corpus_path)
            # Reconstruct and save bid chunks JSONL
            all_bid_records = self.registry.get_records_by_bid(resolved_bid)
            active_chunk_ids = {cid for r in all_bid_records for cid in r.chunk_ids}
            current_bid_chunks = [c for c in self.bm25_index.chunks if c.chunk_id in active_chunk_ids]
            save_chunks(bid_id=resolved_bid, chunks=current_bid_chunks)

        elapsed = round(time.time() - start_time, 2)
        logger.info(
            f"Incremental sync complete for {resolved_bid} in {elapsed}s: "
            f"new={len(files_new)}, mod={len(files_modified)}, del={len(files_deleted)}, "
            f"chunks_added={total_chunks_added}, chunks_removed={total_chunks_removed}, "
            f"cached_emb={total_embeddings_cached}, new_emb={total_embeddings_created}"
        )

        return IndexingReport(
            status="success" if not sync_errors else "partial_success",
            bid_id=resolved_bid,
            folder_path=str(target_dir),
            files_new=len(files_new),
            files_unchanged=len(files_unchanged),
            files_modified=len(files_modified),
            files_deleted=len(files_deleted),
            chunks_added=total_chunks_added,
            chunks_removed=total_chunks_removed,
            chunks_created=total_chunks_added,
            embeddings_created=total_embeddings_created,
            embeddings_requested=total_embeddings_created,
            embedding_cache_hits=total_embeddings_cached,
            embeddings_cached=total_embeddings_cached,
            vectors_upserted=total_vectors_upserted,
            bm25_indexed_chunks=len(self.bm25_index.chunks),
            elapsed_seconds=elapsed,
            errors=sync_errors,
        )

    def remove_file(self, file_path: str | Path) -> bool:
        """Remove a single file's chunks from Qdrant, BM25, and registry."""
        norm_path = str(Path(file_path).resolve())
        rec = self.registry.get_record(norm_path)
        if not rec:
            return False

        if rec.chunk_ids:
            self.vector_store.delete_chunks(self.collection_name, rec.chunk_ids)
            self.bm25_index.remove_chunks(rec.chunk_ids)
            self.bm25_index.save(self.bm25_corpus_path)

        self.registry.delete_record(norm_path)
        return True

"""Master DocumentChunker orchestrating section-aware and table-aware chunking."""

from typing import Any, Dict, List, Optional
from app.chunking.table_chunker import TableChunker
from app.chunking.text_chunker import TextChunker
from app.logging import logger
from app.schemas.canonical import Chunk, Document


class DocumentChunker:
    """Transforms canonical documents into structured, retrieval-ready chunks."""

    def __init__(
        self,
        target_tokens: int = 700,
        max_tokens: int = 850,
        overlap_tokens: int = 100,
    ):
        self.text_chunker = TextChunker(
            target_tokens=target_tokens,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )
        self.table_chunker = TableChunker(max_tokens=target_tokens)

    def chunk_document(
        self,
        doc: Document,
        start_source_order: int = 1,
    ) -> List[Chunk]:
        """Convert a single canonical Document into a list of Chunk instances."""
        chunks: List[Chunk] = []
        meta = doc.metadata
        current_section: Optional[str] = None
        order_idx = start_source_order

        base_meta: Dict[str, Any] = {
            "document_date": meta.document_date,
            "title": meta.title,
            "file_size_bytes": meta.file_size_bytes,
            "file_hash": meta.file_hash,
        }

        logger.info(
            f"Chunking document: {meta.file_name} ({len(doc.pages)} pages, bid_id={meta.bid_id})"
        )

        for page in doc.pages:
            # 1. Chunk tables on this page
            for table in page.tables:
                table_chunks = self.table_chunker.chunk_table(
                    table=table,
                    bid_id=meta.bid_id,
                    file_name=meta.file_name,
                    document_type=meta.doc_type,
                    addendum_number=meta.addendum_number,
                    section=current_section,
                    start_source_order=order_idx,
                    base_metadata=base_meta,
                )
                chunks.extend(table_chunks)
                order_idx += len(table_chunks)

            # 2. Chunk text on this page
            text_chunks, updated_section, next_order = self.text_chunker.chunk_page_text(
                page_text=page.text,
                bid_id=meta.bid_id,
                file_name=meta.file_name,
                document_type=meta.doc_type,
                page_number=page.page_number,
                addendum_number=meta.addendum_number,
                start_source_order=order_idx,
                initial_section=current_section,
                base_metadata=base_meta,
            )
            chunks.extend(text_chunks)
            current_section = updated_section
            order_idx = next_order

        logger.info(
            f"Generated {len(chunks)} chunks for document {meta.file_name} "
            f"(text chunks={sum(1 for c in chunks if c.chunk_type == 'text')}, "
            f"table chunks={sum(1 for c in chunks if c.chunk_type == 'table')})"
        )
        return chunks

    def chunk_bid(self, documents: List[Document]) -> List[Chunk]:
        """Convert all canonical documents in a bid into a unified list of Chunk instances."""
        all_chunks: List[Chunk] = []
        global_order = 1

        for doc in documents:
            doc_chunks = self.chunk_document(doc, start_source_order=global_order)
            all_chunks.extend(doc_chunks)
            global_order += len(doc_chunks)

        return all_chunks

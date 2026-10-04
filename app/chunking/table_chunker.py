"""Table-aware chunking preserving headers, row integrity, and markdown structure."""

from typing import Any, Dict, List, Optional
from app.chunking.ids import generate_chunk_id
from app.chunking.tokenizer import count_tokens
from app.schemas.canonical import Chunk, TableBlock


class TableChunker:
    """Chunks structured tables while guaranteeing column header preservation across slices."""

    def __init__(self, max_tokens: int = 700):
        self.max_tokens = max_tokens

    def chunk_table(
        self,
        table: TableBlock,
        bid_id: str,
        file_name: str,
        document_type: str,
        addendum_number: Optional[int],
        section: Optional[str],
        start_source_order: int,
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """Convert a TableBlock into one or more Chunk objects with preserved headers."""
        chunks: List[Chunk] = []
        meta = dict(base_metadata or {})
        meta["table_id"] = table.table_id

        # If full table markdown is within token limits, produce an atomic table chunk
        full_tokens = count_tokens(table.raw_markdown)
        if full_tokens <= self.max_tokens or not table.rows:
            chunk_id = generate_chunk_id(
                bid_id=bid_id,
                file_name=file_name,
                page_number=table.page_number,
                source_order=start_source_order,
                text=table.raw_markdown,
                section=section,
            )
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    bid_id=bid_id,
                    file_name=file_name,
                    document_type=document_type,
                    page_number=table.page_number,
                    section=section,
                    addendum_number=addendum_number,
                    text=table.raw_markdown,
                    chunk_type="table",
                    token_count=full_tokens,
                    source_order=start_source_order,
                    metadata=meta,
                )
            )
            return chunks

        # Large table splitting: split rows into batches while repeating headers
        headers = table.headers
        safe_headers = [h.replace("|", "\\|") for h in headers]
        header_line = "| " + " | ".join(safe_headers) + " |"
        separator_line = "| " + " | ".join(["---"] * len(safe_headers)) + " |"
        header_block = f"{header_line}\n{separator_line}"
        header_tokens = count_tokens(header_block)

        current_rows: List[List[str]] = []
        current_tokens = header_tokens
        order_idx = start_source_order

        for row in table.rows:
            padded_row = list(row) + [""] * (len(safe_headers) - len(row))
            safe_row = [str(c).replace("|", "\\|") for c in padded_row[: len(safe_headers)]]
            row_line = "| " + " | ".join(safe_row) + " |"
            row_tokens = count_tokens(row_line)

            if current_rows and (current_tokens + row_tokens > self.max_tokens):
                # Emit current table slice
                slice_md = header_block + "\n" + "\n".join(
                    ["| " + " | ".join([str(c).replace("|", "\\|") for c in r]) + " |" for r in current_rows]
                )
                chunk_id = generate_chunk_id(
                    bid_id=bid_id,
                    file_name=file_name,
                    page_number=table.page_number,
                    source_order=order_idx,
                    text=slice_md,
                    section=section,
                )
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        bid_id=bid_id,
                        file_name=file_name,
                        document_type=document_type,
                        page_number=table.page_number,
                        section=section,
                        addendum_number=addendum_number,
                        text=slice_md,
                        chunk_type="table",
                        token_count=count_tokens(slice_md),
                        source_order=order_idx,
                        metadata=meta,
                    )
                )
                order_idx += 1
                current_rows = [padded_row[: len(safe_headers)]]
                current_tokens = header_tokens + row_tokens
            else:
                current_rows.append(padded_row[: len(safe_headers)])
                current_tokens += row_tokens

        # Emit remaining rows
        if current_rows:
            slice_md = header_block + "\n" + "\n".join(
                ["| " + " | ".join([str(c).replace("|", "\\|") for c in r]) + " |" for r in current_rows]
            )
            chunk_id = generate_chunk_id(
                bid_id=bid_id,
                file_name=file_name,
                page_number=table.page_number,
                source_order=order_idx,
                text=slice_md,
                section=section,
            )
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    bid_id=bid_id,
                    file_name=file_name,
                    document_type=document_type,
                    page_number=table.page_number,
                    section=section,
                    addendum_number=addendum_number,
                    text=slice_md,
                    chunk_type="table",
                    token_count=count_tokens(slice_md),
                    source_order=order_idx,
                    metadata=meta,
                )
            )

        return chunks

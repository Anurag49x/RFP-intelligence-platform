"""Section-aware text chunking preserving logical paragraphs, lists, headings, and overlap."""

import re
from typing import Any, Dict, List, Optional, Tuple
from app.chunking.ids import generate_chunk_id
from app.chunking.tokenizer import count_tokens
from app.schemas.canonical import Chunk


class TextChunker:
    """Chunks text while tracking section titles and maintaining semantic boundaries."""

    HEADING_PATTERNS = [
        re.compile(r"^(?:SECTION|ARTICLE|PART|EXHIBIT|ATTACHMENT)\s+[A-Z0-9IVX]+[:\.\s-]*(.*)$", re.IGNORECASE),
        re.compile(r"^#+\s+(.+)$"),
        re.compile(r"^(\d+\.\d+(?:\.\d+)?\s+[A-Z].*)$"),
        re.compile(r"^([A-Z\s,/-]{4,60}):?$"),
    ]

    def __init__(self, target_tokens: int = 700, max_tokens: int = 850, overlap_tokens: int = 100):
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    @classmethod
    def detect_heading(cls, line: str) -> Optional[str]:
        """Detect if a line is a section or structural heading."""
        cleaned = line.strip()
        if not cleaned or len(cleaned) > 100:
            return None
        for pattern in cls.HEADING_PATTERNS:
            match = pattern.match(cleaned)
            if match:
                heading = match.group(1).strip() if match.groups() else cleaned
                return heading or cleaned
        return None

    def _split_oversized_block(self, text: str) -> List[str]:
        """Split a large paragraph into sentence-level or list-level units."""
        # Try splitting by list items or sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        units: List[str] = []
        current = ""
        for s in sentences:
            if not current:
                current = s
            elif count_tokens(current + " " + s) <= self.target_tokens:
                current += " " + s
            else:
                units.append(current)
                current = s
        if current:
            units.append(current)
        return units or [text]

    def chunk_page_text(
        self,
        page_text: str,
        bid_id: str,
        file_name: str,
        document_type: str,
        page_number: int,
        addendum_number: Optional[int],
        start_source_order: int,
        initial_section: Optional[str] = None,
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Chunk], Optional[str], int]:
        """Chunk a single page's text into section-aware Chunk objects with overlap."""
        if not page_text.strip():
            return [], initial_section, start_source_order

        chunks: List[Chunk] = []
        meta = dict(base_metadata or {})
        current_section = initial_section
        order_idx = start_source_order

        # Split into paragraphs / lines
        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]

        current_blocks: List[str] = []
        current_tokens = 0

        for p in paragraphs:
            # Check for section heading
            first_line = p.split("\n")[0].strip()
            heading = self.detect_heading(first_line)
            if heading:
                current_section = heading

            # If paragraph itself is oversized, break into smaller units
            p_tokens = count_tokens(p)
            sub_blocks = self._split_oversized_block(p) if p_tokens > self.max_tokens else [p]

            for block in sub_blocks:
                block_tokens = count_tokens(block)

                if current_blocks and (current_tokens + block_tokens > self.target_tokens):
                    # Emit chunk
                    chunk_text = "\n\n".join(current_blocks).strip()
                    chunk_id = generate_chunk_id(
                        bid_id=bid_id,
                        file_name=file_name,
                        page_number=page_number,
                        source_order=order_idx,
                        text=chunk_text,
                        section=current_section,
                    )
                    chunks.append(
                        Chunk(
                            chunk_id=chunk_id,
                            bid_id=bid_id,
                            file_name=file_name,
                            document_type=document_type,
                            page_number=page_number,
                            section=current_section,
                            addendum_number=addendum_number,
                            text=chunk_text,
                            chunk_type="text",
                            token_count=count_tokens(chunk_text),
                            source_order=order_idx,
                            metadata=meta,
                        )
                    )
                    order_idx += 1

                    # Compute overlap from end of current_blocks
                    overlap_blocks: List[str] = []
                    overlap_tok = 0
                    for b in reversed(current_blocks):
                        b_tok = count_tokens(b)
                        if overlap_tok + b_tok <= self.overlap_tokens:
                            overlap_blocks.insert(0, b)
                            overlap_tok += b_tok
                        else:
                            break

                    current_blocks = overlap_blocks + [block]
                    current_tokens = overlap_tok + block_tokens
                else:
                    current_blocks.append(block)
                    current_tokens += block_tokens

        # Emit trailing block
        if current_blocks:
            chunk_text = "\n\n".join(current_blocks).strip()
            if chunk_text:
                chunk_id = generate_chunk_id(
                    bid_id=bid_id,
                    file_name=file_name,
                    page_number=page_number,
                    source_order=order_idx,
                    text=chunk_text,
                    section=current_section,
                )
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        bid_id=bid_id,
                        file_name=file_name,
                        document_type=document_type,
                        page_number=page_number,
                        section=current_section,
                        addendum_number=addendum_number,
                        text=chunk_text,
                        chunk_type="text",
                        token_count=count_tokens(chunk_text),
                        source_order=order_idx,
                        metadata=meta,
                    )
                )
                order_idx += 1

        return chunks, current_section, order_idx

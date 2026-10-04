"""Canonical Evidence Store and provenance registry for verifying agent citations."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from app.chunking.storage import load_chunks
from app.logging import logger
from app.schemas.canonical import Citation, Chunk, Evidence, FieldResult


class EvidenceStore:
    """In-memory and persisted registry for verifying and looking up canonical chunks and citations."""

    _cache: Dict[str, Chunk] = {}

    @classmethod
    def load_bid_chunks(cls, bid_id: str, chunks_dir: Union[str, Path] = "data/chunks") -> List[Chunk]:
        """Load and cache chunks for a specific bid."""
        chunks = load_chunks(bid_id, output_dir=chunks_dir)
        for c in chunks:
            cls._cache[c.chunk_id] = c
        return chunks

    @classmethod
    def load_all_known_chunks(cls, chunks_dir: Union[str, Path] = "data/chunks"):
        """Scan chunks directory and preload all active chunks into cache."""
        dir_path = Path(chunks_dir).resolve()
        if not dir_path.exists():
            return
        for file in dir_path.glob("*.jsonl"):
            bid_id = file.stem
            cls.load_bid_chunks(bid_id, chunks_dir=dir_path)


    @classmethod
    def register_chunk(cls, chunk: Chunk):
        """Manually register or update a chunk in the active store."""
        cls._cache[chunk.chunk_id] = chunk

    @classmethod
    def register_chunks(cls, chunks: List[Chunk]):
        """Manually register multiple chunks."""
        for c in chunks:
            cls._cache[c.chunk_id] = c

    @classmethod
    def get(cls, chunk_id: str) -> Optional[Chunk]:
        """Lookup a canonical chunk by chunk_id."""
        if chunk_id in cls._cache:
            return cls._cache[chunk_id]

        # Try searching persisted corpus if not yet cached
        cls.load_all_known_chunks()
        return cls._cache.get(chunk_id)

    @classmethod
    def count(cls) -> int:
        """Return total number of registered chunks."""
        if not cls._cache:
            cls.load_all_known_chunks()
        return len(cls._cache)

    @classmethod
    def exists(cls, chunk_id: str) -> bool:
        """Check if a chunk_id exists in the canonical store."""
        return cls.get(chunk_id) is not None

    @classmethod
    def get_evidence(cls, chunk_id: str) -> Optional[Evidence]:
        """Lookup chunk and convert to Evidence object."""
        chk = cls.get(chunk_id)
        if chk:
            return chk.to_evidence()
        return None

    @classmethod
    def deduplicate_citations(cls, citations: List[Citation]) -> List[Citation]:
        """Deduplicate citations by (bid_id, chunk_id) while preserving first occurrence order."""
        seen: Set[str] = set()
        deduped: List[Citation] = []
        for cit in citations:
            key = f"{cit.bid_id}::{cit.chunk_id}"
            if key not in seen:
                seen.add(key)
                deduped.append(cit)
        return deduped

    @classmethod
    def validate_field_result(cls, result: FieldResult, field_name: str = "") -> List[str]:
        """Deterministic validation of FieldResult evidence contract rules."""
        errors: List[str] = []

        # Rule 1: Confidence bounds
        if result.confidence < 0.0 or result.confidence > 1.0:
            errors.append(f"Confidence {result.confidence} for field '{field_name}' must be between 0.0 and 1.0.")

        # Rule 2: Non-null values MUST have at least one source citation
        if result.value is not None:
            if not result.sources:
                errors.append(f"Non-null value '{result.value}' for field '{field_name}' must have at least one source citation.")
            for i, src in enumerate(result.sources):
                if not src.chunk_id:
                    errors.append(f"Citation #{i+1} for field '{field_name}' is missing chunk_id.")
                elif not cls.exists(src.chunk_id):
                    errors.append(f"Citation chunk_id '{src.chunk_id}' for field '{field_name}' does not exist in EvidenceStore.")

        # Rule 3: Null values must have explanatory notes
        if result.value is None:
            if not result.notes:
                errors.append(f"Null field '{field_name}' must provide explanatory notes (e.g. 'Not found in documents.').")

        return errors

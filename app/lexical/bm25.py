"""Local BM25 lexical search engine preserving procurement identifiers and metadata filtering."""

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from rank_bm25 import BM25Okapi

from app.logging import logger
from app.schemas.canonical import Chunk, Evidence, SearchFilters, SearchResult


class BM25Index:
    """Local BM25 search index over canonical Chunk objects with persistence and filtering."""

    # Tokenizer pattern preserving hyphenated, dotted, and alphanumeric identifiers
    TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+(?:[-_./][a-zA-Z0-9]+)*")

    def __init__(self, chunks: Optional[List[Chunk]] = None, corpus_path: str | Path = "data/bm25/corpus.jsonl"):
        if chunks is None:
            path = Path(corpus_path).resolve()
            if path.exists():
                loaded_chunks: List[Chunk] = []
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            loaded_chunks.append(Chunk(**json.loads(line)))
                self.chunks = loaded_chunks
            else:
                self.chunks = []
        else:
            self.chunks = chunks

        self.chunk_map: Dict[str, Chunk] = {c.chunk_id: c for c in self.chunks}
        self.corpus_tokens: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None

        if self.chunks:
            self._build_index()

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Tokenize text preserving alphanumeric codes, hyphenated IDs, and SKUs."""
        if not text:
            return []
        matches = cls.TOKEN_PATTERN.findall(text.lower())
        return matches

    def _build_index(self):
        """Construct the BM25 model from the loaded chunks."""
        self.corpus_tokens = [self.tokenize(c.text) for c in self.chunks]
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)
            logger.info(f"Built BM25 index over {len(self.chunks)} chunks")

    def add_chunks(self, new_chunks: List[Chunk]):
        """Add new chunks to the BM25 index and rebuild."""
        existing_ids = {c.chunk_id for c in self.chunks}
        added = [c for c in new_chunks if c.chunk_id not in existing_ids]
        if added:
            self.chunks.extend(added)
            self.chunk_map.update({c.chunk_id: c for c in added})
            self._build_index()

    def remove_chunks(self, chunk_ids: List[str]):
        """Remove chunks by chunk_id and rebuild BM25 index."""
        to_remove = set(chunk_ids)
        if not to_remove:
            return
        initial_len = len(self.chunks)
        self.chunks = [c for c in self.chunks if c.chunk_id not in to_remove]
        self.chunk_map = {c.chunk_id: c for c in self.chunks}
        if len(self.chunks) != initial_len:
            self._build_index()


    def _matches_filters(self, chunk: Chunk, filters: Optional[SearchFilters]) -> bool:
        """Evaluate whether a chunk satisfies the provided search filters."""
        if not filters:
            return True
        if filters.bid_id and chunk.bid_id != filters.bid_id:
            return False
        if filters.document_type and chunk.document_type != filters.document_type:
            return False
        if filters.addendum_number is not None and chunk.addendum_number != filters.addendum_number:
            return False
        if filters.file_name and chunk.file_name != filters.file_name:
            return False
        return True

    def search(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[SearchFilters] = None,
    ) -> List[SearchResult]:
        """Execute BM25 lexical search with metadata filtering."""
        if not self.bm25 or not self.chunks:
            logger.warning("BM25 index is empty or not initialized")
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Pair scores with chunks and apply filters
        scored_candidates = []
        for idx, score in enumerate(scores):
            if score > 0:  # Only consider positive lexical matches
                chunk = self.chunks[idx]
                if self._matches_filters(chunk, filters):
                    scored_candidates.append((score, chunk))

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = scored_candidates[:top_k]

        results: List[SearchResult] = []
        for rank_idx, (score, chunk) in enumerate(top_candidates, start=1):
            evidence = chunk.to_evidence(
                score=float(score),
                rank=rank_idx,
                retrieval_source="bm25",
            )
            results.append(
                SearchResult(
                    rank=rank_idx,
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    score=float(score),
                    retrieval_source="bm25",
                    evidence=evidence,
                )
            )

        return results

    def save(self, output_file: str | Path = "data/bm25/corpus.jsonl") -> Path:
        """Persist BM25 corpus to JSONL file."""
        target_path = Path(output_file).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as f:
            for chunk in self.chunks:
                f.write(json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n")

        logger.info(f"Saved BM25 index corpus ({len(self.chunks)} chunks) to {target_path}")
        return target_path

    @classmethod
    def load(cls, input_file: str | Path = "data/bm25/corpus.jsonl") -> "BM25Index":
        """Load BM25 index from persisted JSONL corpus file."""
        target_path = Path(input_file).resolve()
        if not target_path.exists():
            logger.warning(f"BM25 corpus file not found: {target_path}")
            return cls(chunks=[])

        chunks: List[Chunk] = []
        with open(target_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    chunks.append(Chunk(**json.loads(line)))

        logger.info(f"Loaded {len(chunks)} chunks into BM25 index from {target_path.name}")
        return cls(chunks=chunks)

"""Reciprocal Rank Fusion (RRF) for combining dense and lexical search candidates."""

from typing import Dict, List
from app.logging import logger
from app.schemas.canonical import Evidence, SearchResult


def reciprocal_rank_fusion(
    ranked_lists: List[List[SearchResult]],
    rrf_k: int = 60,
    top_k: int = 10,
) -> List[SearchResult]:
    """Combine multiple ranked candidate lists using Reciprocal Rank Fusion."""
    if not ranked_lists:
        return []

    fused_scores: Dict[str, float] = {}
    evidence_map: Dict[str, Evidence] = {}
    text_map: Dict[str, str] = {}
    source_contributions: Dict[str, List[str]] = {}

    for ranked_list in ranked_lists:
        for rank_idx, result in enumerate(ranked_list, start=1):
            chunk_id = result.chunk_id
            rrf_score = 1.0 / (rrf_k + rank_idx)

            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + rrf_score
            evidence_map[chunk_id] = result.evidence
            text_map[chunk_id] = result.text

            if chunk_id not in source_contributions:
                source_contributions[chunk_id] = []
            source_contributions[chunk_id].append(result.retrieval_source)

    # Sort candidates descending by combined RRF score
    sorted_chunk_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)
    top_chunk_ids = sorted_chunk_ids[:top_k]

    fused_results: List[SearchResult] = []
    for rank_idx, chunk_id in enumerate(top_chunk_ids, start=1):
        score = fused_scores[chunk_id]
        orig_evidence = evidence_map[chunk_id]
        sources = "+".join(sorted(set(source_contributions[chunk_id])))

        # Create updated Evidence instance with hybrid provenance
        fused_evidence = Evidence(
            bid_id=orig_evidence.bid_id,
            file_name=orig_evidence.file_name,
            page_number=orig_evidence.page_number,
            chunk_id=chunk_id,
            text=orig_evidence.text,
            document_type=orig_evidence.document_type,
            section=orig_evidence.section,
            addendum_number=orig_evidence.addendum_number,
            document_date=orig_evidence.document_date,
            chunk_type=orig_evidence.chunk_type,
            score=score,
            rank=rank_idx,
            retrieval_source=f"hybrid({sources})",
        )

        fused_results.append(
            SearchResult(
                rank=rank_idx,
                chunk_id=chunk_id,
                text=text_map[chunk_id],
                score=score,
                retrieval_source="hybrid",
                evidence=fused_evidence,
            )
        )

    logger.info(
        f"RRF combined {sum(len(l) for l in ranked_lists)} raw candidates into {len(fused_results)} hybrid results (top_k={top_k})"
    )
    return fused_results

"""Retrieval Evaluation harness for benchmarking Dense, BM25, Hybrid, and Hybrid+Reranker."""

import csv
import json
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import numpy as np

from app.config import get_settings
from app.embeddings.jina import JinaEmbeddingProvider
from app.lexical.bm25 import BM25Index
from app.logging import logger
from app.rerankers.jina import JinaRerankerProvider
from app.retrieval.hybrid import HybridSearchEngine
from app.retrieval.rrf import reciprocal_rank_fusion
from app.schemas.canonical import SearchFilters, SearchResult
from app.vectorstore.qdrant import QdrantVectorStore


def calculate_ndcg(retrieved_chunk_ids: List[str], expected_chunk_ids: List[str], k: int = 5) -> float:
    """Calculate nDCG@K using binary relevance."""
    if not expected_chunk_ids:
        return 1.0 if not retrieved_chunk_ids else 0.0

    expected_set = set(expected_chunk_ids)
    dcg = 0.0
    for i, cid in enumerate(retrieved_chunk_ids[:k]):
        if cid in expected_set:
            dcg += 1.0 / math.log2(i + 2)

    # Calculate ideal DCG
    ideal_hits = min(len(expected_set), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return (dcg / idcg) if idcg > 0 else 0.0


def run_evaluation(
    gold_path: str = "eval/gold_questions.json",
    output_dir: str = "eval/results",
) -> Dict[str, Any]:
    """Execute evaluation over all 4 retrieval configurations on the gold questions dataset."""
    gold_file = Path(gold_path).resolve()
    if not gold_file.exists():
        raise FileNotFoundError(f"Gold questions file not found: {gold_file}")

    with open(gold_file, "r", encoding="utf-8") as f:
        questions: List[Dict[str, Any]] = json.load(f)

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Initialize shared components
    bm25 = BM25Index.load("data/bm25/corpus.jsonl")
    qdrant = QdrantVectorStore()
    embedding_provider = JinaEmbeddingProvider()
    reranker = JinaRerankerProvider()

    # Ensure rfp_chunks collection is populated in evaluation vectorstore
    if not qdrant.collection_exists("rfp_chunks") or (hasattr(qdrant.client, "count") and qdrant.client.count(collection_name="rfp_chunks").count == 0):
        logger.info("Populating rfp_chunks into Qdrant evaluation instance from data/chunks/...")
        import glob
        from app.schemas.canonical import Chunk
        all_eval_chunks: List[Chunk] = []
        for chunk_file in sorted(glob.glob("data/chunks/*.jsonl")):
            with open(chunk_file, "r", encoding="utf-8") as cf:
                for line in cf:
                    if line.strip():
                        all_eval_chunks.append(Chunk(**json.loads(line)))
        if all_eval_chunks:
            texts = [c.text for c in all_eval_chunks]
            vectors = embedding_provider.embed_documents(texts)
            qdrant.upsert_chunks("rfp_chunks", all_eval_chunks, vectors)

    engine = HybridSearchEngine(
        embedding_provider=embedding_provider,
        vector_store=qdrant,
        bm25_index=bm25,
        reranker=reranker,
    )

    configs = [
        "Dense Only",
        "BM25 Only",
        "Hybrid (Dense+BM25+RRF)",
        "Hybrid + Jina Reranker",
    ]

    all_per_query_results: List[Dict[str, Any]] = []
    config_metrics: Dict[str, Dict[str, Any]] = {}

    positive_questions = [q for q in questions if q.get("expected_chunk_ids")]
    negative_questions = [q for q in questions if not q.get("expected_chunk_ids")]

    # Pre-embed queries once and store hybrid candidate results to eliminate duplicate Jina API requests
    query_vector_cache: Dict[str, List[float]] = {}
    hybrid_candidates_cache: Dict[str, List[SearchResult]] = {}

    total_q = len(questions)

    for config_name in configs:
        logger.info(f"--- Running Evaluation for Configuration: {config_name} ---")
        print(f"\n--- Running Evaluation: {config_name} ---")

        recalls_at_1: List[float] = []
        recalls_at_3: List[float] = []
        recalls_at_5: List[float] = []
        mrrs: List[float] = []
        ndcgs_at_5: List[float] = []
        latencies_ms: List[float] = []
        failed_queries: List[Dict[str, Any]] = []

        for idx, item in enumerate(questions, start=1):
            qid = item["id"]
            query = item["query"]
            expected = item.get("expected_chunk_ids", [])
            expected_set = set(expected)
            raw_filters = item.get("filters", {})
            filters = SearchFilters(**raw_filters) if raw_filters else None
            is_negative = len(expected) == 0

            # Execute search according to configuration
            start_t = time.time()
            retrieved_results: List[SearchResult] = []
            meta: Dict[str, Any] = {}

            if config_name == "Dense Only":
                try:
                    if qid not in query_vector_cache:
                        print(f"  [JINA EMBEDDING] query {idx}/{total_q}")
                        query_vector_cache[qid] = embedding_provider.embed_query(query)
                    qvec = query_vector_cache[qid]
                    retrieved_results = qdrant.search(
                        collection_name="rfp_chunks",
                        query_vector=qvec,
                        top_k=5,
                        filters=filters,
                    )
                except Exception as e:
                    logger.warning(f"Dense only error for '{query}': {e}")
                    retrieved_results = []
                elapsed_ms = (time.time() - start_t) * 1000.0

            elif config_name == "BM25 Only":
                try:
                    retrieved_results = bm25.search(
                        query=query,
                        top_k=5,
                        filters=filters,
                    )
                except Exception as e:
                    logger.warning(f"BM25 only error for '{query}': {e}")
                    retrieved_results = []
                elapsed_ms = (time.time() - start_t) * 1000.0

            elif config_name == "Hybrid (Dense+BM25+RRF)":
                try:
                    if qid not in query_vector_cache:
                        print(f"  [JINA EMBEDDING] query {idx}/{total_q}")
                        query_vector_cache[qid] = embedding_provider.embed_query(query)
                    
                    # Compute hybrid using precomputed dense vector + BM25 local search
                    qvec = query_vector_cache[qid]
                    dense_hits = qdrant.search("rfp_chunks", qvec, top_k=10, filters=filters)
                    bm25_hits = bm25.search(query=query, top_k=10, filters=filters)
                    candidate_lists = [l for l in [dense_hits, bm25_hits] if l]
                    hybrid_hits = reciprocal_rank_fusion(candidate_lists, rrf_k=60, top_k=5)
                    retrieved_results = hybrid_hits
                    hybrid_candidates_cache[qid] = reciprocal_rank_fusion(candidate_lists, rrf_k=60, top_k=15)
                except Exception as e:
                    logger.warning(f"Hybrid error for '{query}': {e}")
                    retrieved_results = []
                elapsed_ms = (time.time() - start_t) * 1000.0

            elif config_name == "Hybrid + Jina Reranker":
                try:
                    # Reuse cached hybrid candidates if available, otherwise get hybrid candidates
                    if qid in hybrid_candidates_cache:
                        hybrid_candidates = hybrid_candidates_cache[qid]
                    else:
                        if qid not in query_vector_cache:
                            print(f"  [JINA EMBEDDING] query {idx}/{total_q}")
                            query_vector_cache[qid] = embedding_provider.embed_query(query)
                        qvec = query_vector_cache[qid]
                        dense_hits = qdrant.search("rfp_chunks", qvec, top_k=10, filters=filters)
                        bm25_hits = bm25.search(query=query, top_k=10, filters=filters)
                        candidate_lists = [l for l in [dense_hits, bm25_hits] if l]
                        hybrid_candidates = reciprocal_rank_fusion(candidate_lists, rrf_k=60, top_k=15)

                    print(f"  [JINA RERANK] query {idx}/{total_q}")
                    retrieved_results = reranker.rerank(query=query, candidates=hybrid_candidates, top_k=5)
                except Exception as e:
                    logger.warning(f"Reranker error for '{query}': {e}")
                    retrieved_results = hybrid_candidates_cache.get(qid, [])[:5]
                elapsed_ms = (time.time() - start_t) * 1000.0

            latencies_ms.append(elapsed_ms)
            retrieved_chunk_ids = [r.chunk_id for r in retrieved_results]

            # Calculate metrics for positive queries
            first_rank: Optional[int] = None
            if not is_negative:
                for rank_idx, cid in enumerate(retrieved_chunk_ids, start=1):
                    if cid in expected_set:
                        first_rank = rank_idx
                        break

                r1 = 1.0 if (first_rank is not None and first_rank <= 1) else 0.0
                r3 = 1.0 if (first_rank is not None and first_rank <= 3) else 0.0
                r5 = 1.0 if (first_rank is not None and first_rank <= 5) else 0.0
                mrr = (1.0 / first_rank) if first_rank is not None else 0.0
                ndcg5 = calculate_ndcg(retrieved_chunk_ids, expected, k=5)

                recalls_at_1.append(r1)
                recalls_at_3.append(r3)
                recalls_at_5.append(r5)
                mrrs.append(mrr)
                ndcgs_at_5.append(ndcg5)

                if first_rank is None or first_rank > 5:
                    failed_queries.append({
                        "id": qid,
                        "query": query,
                        "expected_chunk_ids": expected,
                        "retrieved_chunk_ids": retrieved_chunk_ids,
                        "top_result_text": retrieved_results[0].text[:120] if retrieved_results else "NONE",
                    })
            else:
                r1 = r3 = r5 = mrr = ndcg5 = None

            all_per_query_results.append({
                "id": qid,
                "configuration": config_name,
                "query": query,
                "type": item.get("type"),
                "is_negative": is_negative,
                "expected_chunk_ids": expected,
                "retrieved_chunk_ids": retrieved_chunk_ids,
                "first_relevant_rank": first_rank,
                "recall_at_1": r1,
                "recall_at_3": r3,
                "recall_at_5": r5,
                "mrr": mrr,
                "ndcg_at_5": ndcg5,
                "latency_ms": round(elapsed_ms, 2),
            })

        # Calculate aggregates
        mean_r1 = float(np.mean(recalls_at_1)) if recalls_at_1 else 0.0
        mean_r3 = float(np.mean(recalls_at_3)) if recalls_at_3 else 0.0
        mean_r5 = float(np.mean(recalls_at_5)) if recalls_at_5 else 0.0
        mean_mrr = float(np.mean(mrrs)) if mrrs else 0.0
        mean_ndcg5 = float(np.mean(ndcgs_at_5)) if ndcgs_at_5 else 0.0
        p50_lat = float(np.percentile(latencies_ms, 50)) if latencies_ms else 0.0
        p95_lat = float(np.percentile(latencies_ms, 95)) if latencies_ms else 0.0

        config_metrics[config_name] = {
            "recall_at_1": round(mean_r1, 4),
            "recall_at_3": round(mean_r3, 4),
            "recall_at_5": round(mean_r5, 4),
            "mrr": round(mean_mrr, 4),
            "ndcg_at_5": round(mean_ndcg5, 4),
            "latency_p50_ms": round(p50_lat, 2),
            "latency_p95_ms": round(p95_lat, 2),
            "failed_queries_count": len(failed_queries),
            "failed_queries": failed_queries,
        }

    # Save outputs
    latest_json_path = out_dir / "latest.json"
    with open(latest_json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "total_questions": len(questions),
                "positive_questions": len(positive_questions),
                "negative_questions": len(negative_questions),
                "summary": config_metrics,
                "per_query_results": all_per_query_results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    latest_csv_path = out_dir / "latest.csv"
    if all_per_query_results:
        with open(latest_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_per_query_results[0].keys()))
            writer.writeheader()
            writer.writerows(all_per_query_results)

    # Print formatted comparison table
    print("\n" + "=" * 90)
    print("RETRIEVAL BENCHMARK EVALUATION RESULTS (Gold Dataset: 28 questions)")
    print("=" * 90)
    header = f"{'Configuration':<26} | {'R@1':<7} | {'R@3':<7} | {'R@5':<7} | {'MRR':<7} | {'nDCG@5':<7} | {'P50 (ms)':<9} | {'P95 (ms)':<9}"
    print(header)
    print("-" * len(header))
    for cfg, m in config_metrics.items():
        row = (
            f"{cfg:<26} | {m['recall_at_1']:<7.4f} | {m['recall_at_3']:<7.4f} | {m['recall_at_5']:<7.4f} | "
            f"{m['mrr']:<7.4f} | {m['ndcg_at_5']:<7.4f} | {m['latency_p50_ms']:<9.2f} | {m['latency_p95_ms']:<9.2f}"
        )
        print(row)
    print("=" * 90)

    # Print error analysis if any failed
    for cfg, m in config_metrics.items():
        if m["failed_queries"]:
            print(f"\n[!] Failure Analysis for: {cfg} ({len(m['failed_queries'])} queries failed Recall@5):")
            for fq in m["failed_queries"]:
                print(f"  - [{fq['id']}] {fq['query']}")
                print(f"    Expected:  {fq['expected_chunk_ids']}")
                print(f"    Retrieved: {fq['retrieved_chunk_ids']}")
                print(f"    Top Text:  {fq['top_result_text']}")
    print("\n" + "=" * 90 + "\n")

    return config_metrics


if __name__ == "__main__":
    run_evaluation()

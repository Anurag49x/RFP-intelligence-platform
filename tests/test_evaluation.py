"""Tests for Phase 6: Retrieval Evaluation metrics and runner."""

from pathlib import Path
import pytest

from eval.run_retrieval_eval import calculate_ndcg, run_evaluation


def test_ndcg_calculation_exact():
    """Verify nDCG@K correctly computes graded/binary ranking relevance."""
    # Top 1 hit
    assert calculate_ndcg(["c1", "c2", "c3"], ["c1"], k=3) == 1.0
    # Rank 2 hit
    score_rank2 = calculate_ndcg(["c2", "c1", "c3"], ["c1"], k=3)
    assert 0.6 < score_rank2 < 0.7  # (1/log2(3)) / (1/log2(2)) = 1/1.585 ~ 0.6309
    # No hit
    assert calculate_ndcg(["c2", "c3"], ["c1"], k=3) == 0.0
    # Empty ground truth (negative query)
    assert calculate_ndcg([], [], k=3) == 1.0


def test_run_retrieval_eval_produces_artifacts(tmp_path: Path):
    """Verify run_evaluation executes and generates latest.json and latest.csv."""
    import json
    # Create mini gold fixture for fast unit testing
    mini_gold = tmp_path / "mini_gold.json"
    with open(mini_gold, "w", encoding="utf-8") as f:
        json.dump([
            {"id": "q1", "query": "What is the proposal due date?", "expected_chunk_ids": ["c1"], "filters": {}},
            {"id": "q2", "query": "What is the Dell model?", "expected_chunk_ids": ["c2"], "filters": {}}
        ], f)

    results = run_evaluation(
        gold_path=str(mini_gold),
        output_dir=str(tmp_path / "results"),
    )
    assert "BM25 Only" in results
    assert "Hybrid (Dense+BM25+RRF)" in results
    assert "Hybrid + Jina Reranker" in results

    json_file = tmp_path / "results" / "latest.json"
    csv_file = tmp_path / "results" / "latest.csv"
    assert json_file.exists()
    assert csv_file.exists()

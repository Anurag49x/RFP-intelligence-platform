import threading
import time
from typing import Any, Dict, List, Optional
import httpx

from app.config import get_settings
from app.logging import logger
from app.rerankers.base import RerankerProvider
from app.schemas.canonical import Evidence, SearchResult

_RERANK_LOCK = threading.Lock()


class JinaRerankerProvider(RerankerProvider):
    """Production reranker client for Jina AI's reranking API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: float = 15.0,
        max_retries: int = 4,
        initial_backoff: float = 2.0,
    ):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.jina_api_key
        self._model_name = model_name or settings.jina_reranker_model or "jina-reranker-v3.5"
        base_url = api_url or settings.jina_api_url or "https://api.jina.ai/v1"
        self.endpoint = f"{base_url.rstrip('/')}/rerank"
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    @property
    def model_name(self) -> str:
        return self._model_name

    def _call_api(self, query: str, documents: List[str], top_n: int) -> List[Dict[str, Any]]:
        """Call Jina Rerank API with exponential backoff for transient errors."""
        if not self.api_key:
            raise ValueError("Jina API key is not configured. Please set JINA_API_KEY in .env or environment.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": self._model_name,
            "query": query,
            "documents": documents,
            "top_n": top_n,
        }

        timeout_cfg = httpx.Timeout(self.timeout, connect=5.0, read=self.timeout, write=5.0, pool=5.0)
        last_err: Optional[Exception] = None
        with _RERANK_LOCK:
            for attempt in range(1, self.max_retries + 1):
                try:
                    with httpx.Client(timeout=timeout_cfg) as client:
                        response = client.post(self.endpoint, headers=headers, json=payload)

                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])
                        return results

                    # Handle transient retryable errors (429 Rate Limit, 502/503/504)
                    if response.status_code in (429, 502, 503, 504) and attempt < self.max_retries:
                        sleep_time = min(self.initial_backoff * (2 ** (attempt - 1)), 8.0)
                        logger.warning(
                            f"[JINA RERANK] HTTP {response.status_code} (attempt {attempt}/{self.max_retries}). "
                            f"Retrying in {sleep_time:.1f}s... Detail: {response.text[:100]}"
                        )
                        time.sleep(sleep_time)
                        continue

                    # Non-retryable error
                    logger.error(f"[JINA RERANK] HTTP {response.status_code} failure (attempt {attempt}/{self.max_retries}): {response.text[:100]}")
                    response.raise_for_status()

                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    last_err = e
                    if attempt < self.max_retries:
                        sleep_time = min(self.initial_backoff * (2 ** (attempt - 1)), 8.0)
                        logger.warning(
                            f"[JINA RERANK] Network/timeout error (attempt {attempt}/{self.max_retries}): {e}. "
                            f"Retrying in {sleep_time:.1f}s..."
                        )
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"[JINA RERANK] Call failed permanently after {self.max_retries} attempts: {e}")
                        break
                except Exception as e:
                    last_err = e
                    logger.error(f"[JINA RERANK] Unexpected error on attempt {attempt}/{self.max_retries}: {e}")
                    break

        raise RuntimeError(f"Jina rerank failed after {self.max_retries} attempts. Last error: {last_err}")

    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 5,
    ) -> List[SearchResult]:
        """Rerank candidate results using Jina listwise/cross-encoder reranking."""
        if not candidates or not query.strip():
            return []

        # 1. Deduplicate candidates by chunk_id while preserving order
        seen_ids = set()
        deduped_candidates: List[SearchResult] = []
        for c in candidates:
            if c.chunk_id not in seen_ids:
                seen_ids.add(c.chunk_id)
                deduped_candidates.append(c)

        if not deduped_candidates:
            return []

        # Prune candidate list to max 8 chunks and truncate text to 1000 chars to avoid TPM limits
        max_candidates = min(len(deduped_candidates), max(top_k * 2, 8))
        pruned_candidates = deduped_candidates[:max_candidates]

        # 2. Prepare documents list for Jina API
        doc_texts = [c.text[:1000] for c in pruned_candidates]
        target_top_n = min(top_k, len(pruned_candidates))

        # 3. Call Jina Rerank API
        try:
            api_results = self._call_api(query=query.strip(), documents=doc_texts, top_n=target_top_n)
        except Exception as e:
            logger.warning(f"Jina rerank API call failed ({e}); falling back to top candidates.")
            return pruned_candidates[:top_k]

        # 4. Map API results back to SearchResult preserving provenance
        reranked_results: List[SearchResult] = []
        for new_rank, item in enumerate(api_results, start=1):
            idx = item.get("index")
            if idx is None or idx < 0 or idx >= len(deduped_candidates):
                logger.warning(f"Jina rerank returned invalid index: {idx}")
                continue

            orig_result = deduped_candidates[idx]
            relevance_score = float(item.get("relevance_score", 0.0))

            # Create updated Evidence with rerank provenance
            orig_ev = orig_result.evidence
            updated_evidence = Evidence(
                bid_id=orig_ev.bid_id,
                file_name=orig_ev.file_name,
                page_number=orig_ev.page_number,
                chunk_id=orig_ev.chunk_id,
                text=orig_ev.text,
                document_type=orig_ev.document_type,
                section=orig_ev.section,
                addendum_number=orig_ev.addendum_number,
                document_date=orig_ev.document_date,
                chunk_type=orig_ev.chunk_type,
                score=relevance_score,
                rank=new_rank,
                retrieval_source=f"{orig_ev.retrieval_source or orig_result.retrieval_source}+rerank",
            )

            reranked_results.append(
                SearchResult(
                    rank=new_rank,
                    chunk_id=orig_result.chunk_id,
                    text=orig_result.text,
                    score=relevance_score,
                    retrieval_source="hybrid+rerank",
                    evidence=updated_evidence,
                    rerank_score=relevance_score,
                    previous_score=orig_result.score,
                    rerank_rank=new_rank,
                )
            )

        logger.info(
            f"Jina reranked {len(deduped_candidates)} candidates into {len(reranked_results)} top results (top_k={top_k})"
        )
        return reranked_results

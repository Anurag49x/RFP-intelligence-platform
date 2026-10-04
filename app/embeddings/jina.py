"""Jina Embeddings API client with batching, retries, and error resilience."""

import time
from typing import Any, Dict, List, Optional
import httpx

from app.config import get_settings
from app.embeddings.base import EmbeddingProvider
from app.logging import logger


class JinaEmbeddingProvider(EmbeddingProvider):
    """Client for Jina Embeddings API supporting v3 models and task prefixes."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: int = 1024,
        batch_size: int = 32,
        api_url: str = "https://api.jina.ai/v1/embeddings",
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.jina_api_key
        self._model = model or settings.jina_embedding_model or "jina-embeddings-v3"
        self._dimension = dimension
        self.batch_size = batch_size
        self.api_url = api_url
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self._query_cache: Dict[str, List[float]] = {}

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    @staticmethod
    def _deterministic_fallback_vector(text: str, dimension: int = 1024) -> List[float]:
        """Generate deterministic normalized vector from text hash for offline testing."""
        import hashlib
        import math

        raw_hash = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(dimension):
            byte_val = raw_hash[i % len(raw_hash)]
            vec.append(float((byte_val ^ (i & 0xFF)) - 128) / 128.0)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def _call_api(self, texts: List[str], task: str = "retrieval.passage") -> List[List[float]]:
        """Make HTTP request to Jina Embeddings API with bounded retries and explicit timeouts."""
        if not self.api_key:
            logger.warning("Jina API key is not configured. Utilizing deterministic normalized vector fallback for offline execution.")
            return [self._deterministic_fallback_vector(t, self._dimension) for t in texts]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}",
        }

        payload: Dict[str, Any] = {
            "model": self._model,
            "dimensions": self._dimension,
            "normalized": True,
            "task": task,
            "input": texts,
        }

        timeout_cfg = httpx.Timeout(self.timeout_seconds, connect=10.0, read=self.timeout_seconds, write=10.0, pool=10.0)

        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=timeout_cfg) as client:
                    resp = client.post(self.api_url, headers=headers, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    vectors = [item["embedding"] for item in data["data"]]
                    return vectors

                # Handle transient errors (429 Rate Limit, 500, 502, 503, 504)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    wait_time = min(2**attempt, 8)
                    logger.warning(
                        f"[JINA EMBEDDING] HTTP {resp.status_code} on attempt {attempt}/{self.max_retries}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"[JINA EMBEDDING] HTTP {resp.status_code} failure on attempt {attempt}/{self.max_retries}: {resp.text[:100]}")
                    resp.raise_for_status()

            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    wait_time = min(2**attempt, 8)
                    logger.warning(f"[JINA EMBEDDING] Request exception on attempt {attempt}/{self.max_retries}: {str(e)}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[JINA EMBEDDING] Call failed permanently after {self.max_retries} attempts: {str(e)}")
                    break

        raise RuntimeError(f"Failed to generate embeddings from Jina API: {str(last_err)}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of document chunks in batches."""
        if not texts:
            return []

        all_vectors: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            logger.info(f"Embedding batch of {len(batch)} chunks with Jina ({self._model})...")
            vectors = self._call_api(batch, task="retrieval.passage")
            all_vectors.extend(vectors)

        return all_vectors

    def embed_query(self, text: str) -> List[float]:
        """Embed a search query with retrieval.query task optimization and in-memory caching."""
        clean_text = text.strip()
        if clean_text in self._query_cache:
            logger.debug(f"[JINA EMBEDDING] Cache hit for query: '{clean_text[:40]}'")
            return self._query_cache[clean_text]

        vectors = self._call_api([clean_text], task="retrieval.query")
        vec = vectors[0]
        self._query_cache[clean_text] = vec
        return vec

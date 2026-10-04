"""Persistent SQLite embedding cache to eliminate redundant API calls."""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.logging import logger


class EmbeddingCache:
    """Persistent SQLite cache for embedding vectors."""

    def __init__(self, db_path: str | Path = "outputs/cache/embeddings.db"):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection."""
        return sqlite3.connect(str(self.db_path), timeout=30.0)

    def _init_db(self):
        """Initialize database table and index."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    cache_key TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    chunk_id TEXT,
                    vector_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON embeddings(model)")
            conn.commit()

    @staticmethod
    def compute_cache_key(model: str, text: str) -> str:
        """Compute stable SHA-256 hash of normalized text combined with model name."""
        normalized = " ".join(text.split()).strip()
        payload = f"{model}:{normalized}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get(self, cache_key: str) -> Optional[List[float]]:
        """Retrieve a single vector from cache if present."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT vector_json FROM embeddings WHERE cache_key = ?", (cache_key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None

    def get_batch(self, cache_keys: List[str]) -> Dict[str, List[float]]:
        """Retrieve multiple vectors in a single SQLite query."""
        if not cache_keys:
            return {}

        results: Dict[str, List[float]] = {}
        # Chunk queries into batches of 500 for SQLite parameter limits
        batch_size = 500
        with self._get_connection() as conn:
            for i in range(0, len(cache_keys), batch_size):
                sub_keys = cache_keys[i : i + batch_size]
                placeholders = ",".join("?" for _ in sub_keys)
                cursor = conn.execute(
                    f"SELECT cache_key, vector_json FROM embeddings WHERE cache_key IN ({placeholders})",
                    sub_keys,
                )
                for key, vec_json in cursor.fetchall():
                    results[key] = json.loads(vec_json)

        return results

    def set_batch(self, records: List[Tuple[str, str, Optional[str], List[float]]]):
        """Save a batch of (cache_key, model, chunk_id, vector) records to cache."""
        if not records:
            return

        now = time.time()
        rows = [
            (cache_key, model, chunk_id or "", json.dumps(vector), now)
            for cache_key, model, chunk_id, vector in records
        ]

        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO embeddings (cache_key, model, chunk_id, vector_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

        logger.info(f"Persisted {len(records)} embedding vectors to SQLite cache at {self.db_path.name}")

    def count(self) -> int:
        """Return total cached vectors count."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
            return cursor.fetchone()[0]

    def get_stats(self) -> Dict[str, Any]:
        """Return embedding cache statistics."""
        return {
            "total_cached_embeddings": self.count(),
            "cache_path": str(self.db_path),
        }

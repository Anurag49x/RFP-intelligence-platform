"""Persistent SQLite Document Registry for tracking indexed files, hashes, and chunk provenance."""

import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.logging import logger


class DocumentRecord(BaseModel):
    """Metadata record for an indexed document file."""

    file_path: str
    file_name: str
    bid_id: str
    file_hash: str
    file_size: int = 0
    modified_time: float = 0.0
    document_type: str = "other"
    addendum_number: Optional[int] = None
    chunk_ids: List[str] = Field(default_factory=list)
    chunking_version: str = "v1"
    embedding_model: str = "jina-embeddings-v3"
    indexed_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    status: str = "indexed"
    error: Optional[str] = None


class DocumentRegistry:
    """Thread-safe SQLite storage for indexed document registry records."""

    def __init__(self, db_path: str | Path = "outputs/registry/document_registry.db"):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a sqlite connection with WAL mode and row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self):
        """Create registry tables and indices if not present."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_registry (
                    file_path TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    bid_id TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    modified_time REAL NOT NULL,
                    document_type TEXT NOT NULL,
                    addendum_number INTEGER,
                    chunk_ids TEXT NOT NULL,
                    chunking_version TEXT NOT NULL,
                    embedding_model TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_reg_bid ON document_registry(bid_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_reg_hash ON document_registry(file_hash);")
            conn.commit()

    def get_record(self, file_path: str | Path) -> Optional[DocumentRecord]:
        """Fetch registry record for a specific file path."""
        norm_path = str(Path(file_path).resolve())
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM document_registry WHERE file_path = ?;", (norm_path,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def get_records_by_bid(self, bid_id: str) -> List[DocumentRecord]:
        """Fetch all registry records associated with a specific bid."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM document_registry WHERE bid_id = ?;", (bid_id,))
            rows = cur.fetchall()
            return [self._row_to_record(r) for r in rows]

    def get_all_records(self) -> List[DocumentRecord]:
        """Fetch all registry records."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM document_registry;")
            rows = cur.fetchall()
            return [self._row_to_record(r) for r in rows]

    def upsert_record(self, record: DocumentRecord):
        """Insert or update a document registry record."""
        norm_path = str(Path(record.file_path).resolve())
        chunk_ids_json = json.dumps(record.chunk_ids)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO document_registry (
                    file_path, file_name, bid_id, file_hash, file_size, modified_time,
                    document_type, addendum_number, chunk_ids, chunking_version,
                    embedding_model, indexed_at, status, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_name = excluded.file_name,
                    bid_id = excluded.bid_id,
                    file_hash = excluded.file_hash,
                    file_size = excluded.file_size,
                    modified_time = excluded.modified_time,
                    document_type = excluded.document_type,
                    addendum_number = excluded.addendum_number,
                    chunk_ids = excluded.chunk_ids,
                    chunking_version = excluded.chunking_version,
                    embedding_model = excluded.embedding_model,
                    indexed_at = excluded.indexed_at,
                    status = excluded.status,
                    error = excluded.error;
                """,
                (
                    norm_path,
                    record.file_name,
                    record.bid_id,
                    record.file_hash,
                    record.file_size,
                    record.modified_time,
                    record.document_type,
                    record.addendum_number,
                    chunk_ids_json,
                    record.chunking_version,
                    record.embedding_model,
                    record.indexed_at,
                    record.status,
                    record.error,
                ),
            )
            conn.commit()

    def delete_record(self, file_path: str | Path) -> bool:
        """Delete a document registry record by file path."""
        norm_path = str(Path(file_path).resolve())
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM document_registry WHERE file_path = ?;", (norm_path,))
            conn.commit()
            return cur.rowcount > 0

    def delete_records_by_bid(self, bid_id: str) -> int:
        """Delete all registry records for a bid."""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM document_registry WHERE bid_id = ?;", (bid_id,))
            conn.commit()
            return cur.rowcount

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> DocumentRecord:
        chunk_ids = json.loads(row["chunk_ids"]) if row["chunk_ids"] else []
        return DocumentRecord(
            file_path=row["file_path"],
            file_name=row["file_name"],
            bid_id=row["bid_id"],
            file_hash=row["file_hash"],
            file_size=row["file_size"],
            modified_time=row["modified_time"],
            document_type=row["document_type"],
            addendum_number=row["addendum_number"],
            chunk_ids=chunk_ids,
            chunking_version=row["chunking_version"],
            embedding_model=row["embedding_model"],
            indexed_at=row["indexed_at"],
            status=row["status"],
            error=row["error"],
        )

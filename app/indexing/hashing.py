"""Deterministic content hashing utilities for change detection and file registry."""

import hashlib
from pathlib import Path
from typing import Union


def compute_file_hash(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Calculate the SHA-256 hash of file contents in streamed chunks."""
    target_path = Path(file_path).resolve()
    if not target_path.exists():
        raise FileNotFoundError(f"Cannot compute hash for nonexistent file: {target_path}")

    hasher = hashlib.sha256()
    with open(target_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_content_hash(text: str) -> str:
    """Calculate SHA-256 of normalized text content."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

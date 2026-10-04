"""Deterministic chunk ID generator for the RFP Intelligence Platform."""

import hashlib
import re
from typing import Optional


def generate_chunk_id(
    bid_id: str,
    file_name: str,
    page_number: int,
    source_order: int,
    text: str,
    section: Optional[str] = None,
) -> str:
    """Generate a stable, unique, deterministic chunk ID from source metadata and text."""
    # Normalize text for hashing (collapse whitespace)
    normalized_text = " ".join(text.split()).strip()
    
    # Clean bid_id and file_name for human-readable prefix
    clean_bid = re.sub(r"[^a-zA-Z0-9_-]", "_", bid_id)
    
    # Hash payload
    hasher = hashlib.sha256()
    hasher.update(bid_id.encode("utf-8"))
    hasher.update(file_name.encode("utf-8"))
    hasher.update(str(page_number).encode("utf-8"))
    hasher.update(str(source_order).encode("utf-8"))
    if section:
        hasher.update(section.encode("utf-8"))
    hasher.update(normalized_text.encode("utf-8"))
    
    content_hash = hasher.hexdigest()[:12]
    return f"chk_{clean_bid}_p{page_number}_{source_order:04d}_{content_hash}"

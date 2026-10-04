"""Canonical chunk storage in JSONL format."""

import json
from pathlib import Path
from typing import Iterator, List, Optional
from app.logging import logger
from app.schemas.canonical import Chunk


def save_chunks(
    bid_id: str,
    chunks: List[Chunk],
    output_dir: str | Path = "data/chunks",
) -> Path:
    """Save chunks to a JSONL file under the specified directory."""
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{bid_id}.jsonl"

    with open(target_file, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n")

    logger.info(f"Saved {len(chunks)} chunks for {bid_id} to {target_file}")
    return target_file


def load_chunks(
    bid_id: str,
    output_dir: str | Path = "data/chunks",
) -> List[Chunk]:
    """Load all chunks for a bid from its canonical JSONL file."""
    target_dir = Path(output_dir).resolve()
    target_file = target_dir / f"{bid_id}.jsonl"

    if not target_file.exists():
        logger.warning(f"Chunk file not found for bid: {bid_id} at {target_file}")
        return []

    chunks: List[Chunk] = []
    with open(target_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    chunks.append(Chunk(**data))
                except Exception as e:
                    logger.error(f"Error parsing chunk on line {line_num} in {target_file.name}: {str(e)}")

    logger.info(f"Loaded {len(chunks)} chunks for {bid_id} from {target_file}")
    return chunks


def iter_chunks(
    bid_id: str,
    output_dir: str | Path = "data/chunks",
) -> Iterator[Chunk]:
    """Stream chunks for a bid line-by-line from JSONL."""
    target_dir = Path(output_dir).resolve()
    target_file = target_dir / f"{bid_id}.jsonl"

    if not target_file.exists():
        return

    with open(target_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield Chunk(**json.loads(line))

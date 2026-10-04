"""File discovery component for discovering bid documents in directories."""

import hashlib
import mimetypes
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from app.logging import logger

SUPPORTED_EXTENSIONS = {".pdf", ".html", ".htm"}
IGNORED_FILENAMES = {".ds_store", "thumbs.db", "desktop.ini"}
IGNORED_PREFIXES = {".", "~$"}


class DiscoveredFile(BaseModel):
    """Normalized representation of a discovered file in a bid folder."""

    file_path: str
    file_name: str
    extension: str
    file_size_bytes: int
    mime_type: Optional[str] = None
    file_hash: str
    bid_id: str


class FileDiscovery:
    """Discovers and filters supported documents within a bid directory."""

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute SHA-256 hash of a file for change tracking and caching."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def resolve_bid_id(cls, folder_path: Path) -> str:
        """Infer bid_id from the folder path generically."""
        return folder_path.resolve().name

    @classmethod
    def is_supported_file(cls, path: Path) -> bool:
        """Check if a file should be ingested based on extension and filename rules."""
        if not path.is_file():
            return False

        filename_lower = path.name.lower()

        # Check ignored filenames and temporary prefixes
        if filename_lower in IGNORED_FILENAMES:
            return False
        if any(filename_lower.startswith(prefix) for prefix in IGNORED_PREFIXES):
            return False

        # Check supported extensions
        return path.suffix.lower() in SUPPORTED_EXTENSIONS

    @classmethod
    def discover_files(cls, folder_path: str | Path, bid_id: Optional[str] = None) -> List[DiscoveredFile]:
        """Recursively discover supported files in the target folder in deterministic order."""
        target_dir = Path(folder_path).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            logger.error(f"Folder path does not exist or is not a directory: {target_dir}")
            return []

        resolved_bid_id = bid_id or cls.resolve_bid_id(target_dir)
        discovered: List[DiscoveredFile] = []

        logger.info(f"Scanning directory for documents: {target_dir} (bid_id={resolved_bid_id})")

        for file_path in sorted(target_dir.rglob("*")):
            if cls.is_supported_file(file_path):
                ext = file_path.suffix.lower()
                mime_type, _ = mimetypes.guess_type(str(file_path))
                size = file_path.stat().st_size
                file_hash = cls.compute_sha256(file_path)

                discovered_file = DiscoveredFile(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    extension=ext,
                    file_size_bytes=size,
                    mime_type=mime_type or ("application/pdf" if ext == ".pdf" else "text/html"),
                    file_hash=file_hash,
                    bid_id=resolved_bid_id,
                )
                discovered.append(discovered_file)
                logger.info(f"Discovered supported file: {file_path.name} ({size} bytes)")

        logger.info(f"Discovery complete: Found {len(discovered)} supported files in {target_dir.name}")
        return discovered

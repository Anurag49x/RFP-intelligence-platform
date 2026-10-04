"""Tests for FileDiscovery component."""

from pathlib import Path
import pytest
from app.ingestion.discovery import FileDiscovery


def test_discover_files_bid1(bid1_path: Path):
    """Verify discovery finds all supported files in Bid1."""
    files = FileDiscovery.discover_files(bid1_path)
    assert len(files) == 4
    extensions = {f.extension for f in files}
    assert ".pdf" in extensions
    assert ".html" in extensions
    for f in files:
        assert f.bid_id == "Bid1"
        assert len(f.file_hash) == 64  # SHA-256


def test_discover_files_bid2(bid2_path: Path):
    """Verify discovery finds all supported files in Bid2."""
    files = FileDiscovery.discover_files(bid2_path)
    assert len(files) == 5
    for f in files:
        assert f.bid_id == "Bid2"
        assert f.file_size_bytes > 0


def test_ignore_unsupported_files(tmp_path: Path):
    """Verify ignored files (temp files, hidden files, unsupported formats) are skipped."""
    (tmp_path / "valid.pdf").write_bytes(b"%PDF-1.4 test")
    (tmp_path / "valid.html").write_text("<html><body>test</body></html>")
    (tmp_path / ".DS_Store").write_bytes(b"temp")
    (tmp_path / "Thumbs.db").write_bytes(b"temp")
    (tmp_path / "~$temp_file.pdf").write_bytes(b"temp")
    (tmp_path / "notes.txt").write_text("plain text")

    files = FileDiscovery.discover_files(tmp_path, bid_id="TestBid")
    names = [f.file_name for f in files]
    assert names == ["valid.html", "valid.pdf"]
    assert len(files) == 2


def test_deterministic_ordering(bid1_path: Path):
    """Verify discovery returns identical ordering across multiple invocations."""
    run1 = [f.file_name for f in FileDiscovery.discover_files(bid1_path)]
    run2 = [f.file_name for f in FileDiscovery.discover_files(bid1_path)]
    assert run1 == run2

"""Tests for Groq Vision OCR Provider, Caching, and PDF OCR Fallback."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import pymupdf

from app.ingestion.ocr import GroqOCRProvider, OCRProvider, OCRResult
from app.ingestion.pdf_parser import PDFParser
from app.schemas.canonical import DocumentMetadata, DocumentPage


class MockOCRProvider(OCRProvider):
    """Mock OCR provider for deterministic testing without external API calls."""

    def __init__(self, response_text: str = "Transcribed RFP text JA-207652", should_fail: bool = False):
        self.response_text = response_text
        self.should_fail = should_fail
        self.call_count = 0

    def is_available(self) -> bool:
        return True

    def ocr_image(self, image_bytes: bytes, mime_type: str = "image/png", page_number: int = 1) -> OCRResult:
        self.call_count += 1
        if self.should_fail:
            return OCRResult(
                text="",
                page_number=page_number,
                provider="groq",
                model="mock-vision",
                status="failed",
                error="Mock API Error",
            )
        return OCRResult(
            text=self.response_text,
            page_number=page_number,
            provider="groq",
            model="mock-vision",
            status="success",
            extraction_method="ocr",
        )


def test_normal_text_page_does_not_invoke_ocr(bid1_path: Path):
    """Verify that pages with normal digital text do not invoke OCR fallback."""
    pdf_file = bid1_path / "Addendum 1 RFP JA-207652 Student and Staff Computing Devices.pdf"
    if not pdf_file.exists():
        pytest.skip("Test file not found")

    mock_ocr = MockOCRProvider()
    metadata = DocumentMetadata(
        bid_id="Bid1",
        file_name=pdf_file.name,
        doc_type="addendum",
        source_path=str(pdf_file),
    )

    doc, warnings, errors = PDFParser.parse_pdf(pdf_file, metadata, ocr_provider=mock_ocr)
    assert doc is not None
    assert mock_ocr.call_count == 0  # Normal text extraction succeeded; no OCR needed
    for page in doc.pages:
        assert page.extraction_method == "text"


def test_scanned_page_invokes_ocr_and_preserves_provenance(tmp_path: Path):
    """Verify that a scanned/image-only page invokes OCR and preserves provenance."""
    # Create a synthetic PDF containing an image-only page (no digital text)
    pdf_path = tmp_path / "scanned_doc.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    # Draw a graphic without text
    page.draw_rect(pymupdf.Rect(50, 50, 200, 200), color=(0, 0, 0), fill=(0.8, 0.8, 0.8))
    doc.save(str(pdf_path))
    doc.close()

    mock_ocr = MockOCRProvider(
        response_text="Header: Proposal Requirement\nSolicitation No: BPM044557\nDue Date: 2026-11-15"
    )
    metadata = DocumentMetadata(
        bid_id="Bid2",
        file_name="scanned_doc.pdf",
        doc_type="rfp",
        source_path=str(pdf_path),
    )

    result_doc, warnings, errors = PDFParser.parse_pdf(pdf_path, metadata, ocr_provider=mock_ocr)

    assert result_doc is not None
    assert mock_ocr.call_count == 1
    assert len(result_doc.pages) == 1

    canonical_page = result_doc.pages[0]
    assert canonical_page.page_number == 1
    assert canonical_page.extraction_method == "ocr"
    assert "BPM044557" in canonical_page.text
    assert "Solicitation No: BPM044557" in canonical_page.text
    assert canonical_page.is_suspicious_or_empty is False

    # Check document level provenance
    assert result_doc.metadata.bid_id == "Bid2"
    assert result_doc.metadata.file_name == "scanned_doc.pdf"


def test_groq_ocr_cache_hit_and_miss(tmp_path: Path):
    """Verify persistent OCR cache hits avoid redundant API calls."""
    cache_dir = tmp_path / "ocr_cache"
    provider = GroqOCRProvider(api_key="test_groq_key", model="mock-model", cache_dir=str(cache_dir))

    fake_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_image_bytes"
    cache_key = provider._get_cache_key(fake_image)

    # Initial state: Cache miss
    assert provider._get_cached_result(cache_key, page_number=1) is None

    # Save to cache
    provider._save_cached_result(cache_key, text="Cached Transcribed Procurement Text", confidence=0.98)

    # Subsequent check: Cache hit
    cached = provider._get_cached_result(cache_key, page_number=1)
    assert cached is not None
    assert cached.status == "cached"
    assert cached.text == "Cached Transcribed Procurement Text"
    assert cached.extraction_method == "ocr"


def test_groq_ocr_transient_error_retries(tmp_path: Path):
    """Verify GroqOCRProvider retries on transient errors."""
    with patch("groq.Groq") as mock_groq_class:
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        # Simulate transient error on attempt 1, then success on attempt 2
        mock_client.chat.completions.create.side_effect = [
            Exception("Rate limit reached 429"),
            MagicMock(
                choices=[
                    MagicMock(message=MagicMock(content="Retried OCR content successful"))
                ]
            ),
        ]

        provider = GroqOCRProvider(
            api_key="test_key",
            model="llama-3.2-11b-vision-preview",
            cache_dir=str(tmp_path / "ocr_cache_retry"),
            max_retries=2,
        )

        with patch("time.sleep", return_value=None):
            result = provider.ocr_image(b"unique_retry_test_image_bytes", page_number=2)

        assert result.status == "success"
        assert result.text == "Retried OCR content successful"
        assert mock_client.chat.completions.create.call_count == 2


def test_groq_ocr_empty_or_malformed_response(tmp_path: Path):
    """Verify graceful handling when Groq Vision returns empty choices."""
    with patch("groq.Groq") as mock_groq_class:
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_client.chat.completions.create.return_value = MagicMock(choices=[])

        provider = GroqOCRProvider(
            api_key="test_key",
            model="llama-3.2-11b-vision-preview",
            cache_dir=str(tmp_path / "ocr_cache_empty"),
            max_retries=1,
        )

        result = provider.ocr_image(b"unique_empty_test_image_bytes", page_number=3)
        assert result.status == "failed"
        assert "Empty response" in result.error


def test_ocr_failure_does_not_crash_pipeline(tmp_path: Path):
    """Verify that when OCR fails, the page is recorded with warnings without crashing."""
    pdf_path = tmp_path / "failing_scanned.pdf"
    doc = pymupdf.open()
    doc.new_page(width=595, height=842)
    doc.save(str(pdf_path))
    doc.close()

    mock_ocr = MockOCRProvider(should_fail=True)
    metadata = DocumentMetadata(
        bid_id="Bid1",
        file_name="failing_scanned.pdf",
        doc_type="rfp",
        source_path=str(pdf_path),
    )

    result_doc, warnings, errors = PDFParser.parse_pdf(pdf_path, metadata, ocr_provider=mock_ocr)
    assert result_doc is not None
    assert len(errors) == 0  # No fatal error
    assert any("OCR fallback failed" in w.message for w in warnings)
    assert result_doc.pages[0].is_suspicious_or_empty is True

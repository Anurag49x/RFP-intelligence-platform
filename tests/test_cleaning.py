"""Tests for TextCleaner component."""

from app.ingestion.cleaning import TextCleaner


def test_normalize_unicode_whitespace():
    """Verify non-standard unicode spaces and CR linebreaks are normalized."""
    dirty_text = "This\u00A0is\u200Ba\ttest\r\nwith\rbreaks."
    cleaned = TextCleaner.normalize_whitespace(dirty_text)
    assert "\u00A0" not in cleaned
    assert "\u200B" not in cleaned
    assert "\r" not in cleaned
    assert "This is a test\nwith\nbreaks." == cleaned


def test_repair_hyphenated_words():
    """Verify broken words across linebreaks are repaired safely."""
    broken = "All require-\nments must be fulfilled for the procure-\nment process."
    repaired = TextCleaner.repair_line_breaks(broken)
    assert "requirements must be fulfilled" in repaired
    assert "procurement process." in repaired


def test_clean_page_text_collapses_excessive_newlines():
    """Verify multiple blank lines are collapsed to at most two newlines."""
    spaced = "Header\n\n\n\n\nSection 1\n\n\nParagraph text."
    cleaned = TextCleaner.clean_page_text(spaced)
    assert "\n\n\n" not in cleaned
    assert "Header\n\nSection 1\n\nParagraph text." == cleaned


def test_detect_and_remove_repeated_headers():
    """Verify running headers across multiple pages are safely removed."""
    pages = [
        "CONFIDENTIAL RFP JA-207652\nPage 1 body content with lots of details\nFooter 1",
        "CONFIDENTIAL RFP JA-207652\nPage 2 body content with lots of details\nFooter 2",
        "CONFIDENTIAL RFP JA-207652\nPage 3 body content with lots of details\nFooter 3",
        "CONFIDENTIAL RFP JA-207652\nPage 4 body content with lots of details\nFooter 4",
    ]
    cleaned = TextCleaner.detect_and_remove_repeated_headers(pages, min_repeat_ratio=0.75)
    for p in cleaned:
        assert not p.startswith("CONFIDENTIAL RFP JA-207652")
        assert "body content with lots of details" in p

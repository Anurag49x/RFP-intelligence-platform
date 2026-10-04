"""Tests for DocumentClassifier component."""

from pathlib import Path
from app.ingestion.classifier import DocumentClassifier


def test_classify_addendum_with_number():
    """Verify classification of Addendum files and number extraction."""
    res1 = DocumentClassifier.classify("Addendum 1 RFP JA-207652.pdf", "This addendum clarifies questions.")
    assert res1.doc_type == "addendum"
    assert res1.addendum_number == 1
    assert res1.confidence >= 0.85

    res2 = DocumentClassifier.classify("Addendum #2 - Computing Devices.pdf", "Amendment No. 2 to RFP.")
    assert res2.doc_type == "addendum"
    assert res2.addendum_number == 2


def test_classify_affidavit():
    """Verify classification of Affidavit documents."""
    res = DocumentClassifier.classify("Contract_Affidavit.pdf", "I hereby swear and affirm under penalty of perjury...")
    assert res.doc_type == "affidavit"
    assert res.confidence >= 0.90

    res_merc = DocumentClassifier.classify("Mercury_Affidavit.pdf", "Mercury free certification affidavit.")
    assert res_merc.doc_type == "affidavit"


def test_classify_specs():
    """Verify classification of Specification sheets."""
    res = DocumentClassifier.classify("Dell_Laptop_Specs.pdf", "Technical specifications for Latitude 5550.")
    assert res.doc_type == "specs"
    assert res.confidence >= 0.85


def test_classify_rfp():
    """Verify classification of main RFP documents."""
    res = DocumentClassifier.classify(
        "JA-207652 Student and Staff Computing Devices FINAL.pdf",
        "Request for Proposals (RFP) for Student and Staff Computing Devices.",
    )
    assert res.doc_type == "rfp"

    res_porfp = DocumentClassifier.classify(
        "PORFP_-_Dell_Laptop_Final.pdf",
        "Purchase Order Request for Proposal (PORFP) solicitation.",
    )
    assert res_porfp.doc_type == "rfp"


def test_classify_html_bid_page():
    """Verify classification of BidNet / portal HTML pages."""
    res = DocumentClassifier.classify(
        "Student and Staff Computing Devices - Bid Information.html",
        "<html><body>BidNet Direct Bid Information Sourcing #168884</body></html>",
    )
    assert res.doc_type == "bid_page"


def test_classify_fallback_other():
    """Verify unknown document formats fallback safely to 'other' without crashing."""
    res = DocumentClassifier.classify("unknown_document.bin", "binary gibberish content")
    assert res.doc_type == "other"
    assert res.confidence == 0.50

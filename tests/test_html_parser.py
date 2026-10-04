"""Tests for HTMLParser component."""

from pathlib import Path
import pytest
from app.ingestion.html_parser import HTMLParser
from app.schemas.canonical import DocumentMetadata


def test_parse_real_html_bid1(bid1_path: Path):
    """Verify parsing of actual Bid1 HTML portal page."""
    html_files = list(bid1_path.glob("*.html"))
    if not html_files:
        pytest.skip("No HTML file found in Bid1")

    html_file = html_files[0]
    metadata = DocumentMetadata(
        bid_id="Bid1",
        file_name=html_file.name,
        doc_type="bid_page",
        source_path=str(html_file),
    )

    doc, warnings, errors = HTMLParser.parse_html(html_file, metadata)
    assert doc is not None
    assert len(errors) == 0
    assert doc.page_count == 1
    assert doc.raw_text_length > 100
    assert len(doc.pages) == 1
    assert "portal_fields" in metadata.extra_metadata or doc.raw_text_length > 200


def test_parse_custom_html_with_table(tmp_path: Path):
    """Verify parsing of HTML with structured tables and metadata."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Procurement Solicitation 2026</title></head>
    <body>
        <script>console.log("ignore me");</script>
        <h1>Solicitation Details</h1>
        <div>Solicitation Number: RFP-998822</div>
        <div>Agency: Department of Technology</div>
        <p>This is a formal solicitation for computer hardware.</p>
        <table>
            <tr><th>Item</th><th>Quantity</th></tr>
            <tr><td>Workstation</td><td>150</td></tr>
        </table>
    </body>
    </html>
    """
    html_file = tmp_path / "test_portal.html"
    html_file.write_text(html_content, encoding="utf-8")

    metadata = DocumentMetadata(
        bid_id="TestBid",
        file_name=html_file.name,
        doc_type="bid_page",
        source_path=str(html_file),
    )

    doc, warnings, errors = HTMLParser.parse_html(html_file, metadata)
    assert doc is not None
    assert doc.metadata.title == "Procurement Solicitation 2026"
    assert len(doc.pages[0].tables) == 1
    table = doc.pages[0].tables[0]
    assert table.headers == ["Item", "Quantity"]
    assert table.rows == [["Workstation", "150"]]

"""Tests for TableExtractor component."""

from app.ingestion.table_extractor import TableExtractor


def test_clean_cell():
    """Verify cell cleaning strips excess whitespace and handles None."""
    assert TableExtractor.clean_cell(None) == ""
    assert TableExtractor.clean_cell("  Item   1 \n  Description\r\n ") == "Item 1 Description"


def test_format_as_markdown():
    """Verify markdown table generation."""
    headers = ["Item", "Quantity", "Price"]
    rows = [
        ["Laptop", "100", "$1200"],
        ["Monitor", "200", "$300"],
    ]
    md = TableExtractor.format_as_markdown(headers, rows)
    assert "| Item | Quantity | Price |" in md
    assert "| --- | --- | --- |" in md
    assert "| Laptop | 100 | $1200 |" in md
    assert "| Monitor | 200 | $300 |" in md


def test_extract_from_raw_tables():
    """Verify raw nested grid extraction into TableBlock instances."""
    raw_tables = [
        [
            ["Item Code", "Specification", "Qty"],
            ["LT-5550", "Intel Core i7, 16GB RAM", "50"],
            ["DK-01", "Thunderbolt 4 Dock", "50"],
            ["", "", ""],  # empty row
        ]
    ]
    blocks = TableExtractor.extract_from_raw_tables(raw_tables, page_number=3)
    assert len(blocks) == 1
    table = blocks[0]
    assert table.table_id == "page_3_table_1"
    assert table.page_number == 3
    assert table.headers == ["Item Code", "Specification", "Qty"]
    assert len(table.rows) == 2  # empty row filtered
    assert "| LT-5550 | Intel Core i7, 16GB RAM | 50 |" in table.raw_markdown

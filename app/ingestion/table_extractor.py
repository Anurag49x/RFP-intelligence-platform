"""Table extraction and Markdown formatting utilities for PDF and HTML documents."""

from typing import Any, List, Optional
from app.logging import logger
from app.schemas.canonical import TableBlock


class TableExtractor:
    """Extracts tables, cleans cell content, and formats them into structured TableBlock objects."""

    @staticmethod
    def clean_cell(cell: Any) -> str:
        """Clean individual cell content, removing excessive newlines and leading/trailing whitespace."""
        if cell is None:
            return ""
        text = str(cell).replace("\r\n", " ").replace("\n", " ")
        # Replace multiple spaces with single space
        return " ".join(text.split()).strip()

    @classmethod
    def format_as_markdown(cls, headers: List[str], rows: List[List[str]]) -> str:
        """Convert headers and rows into a GitHub-flavored Markdown table string."""
        if not headers and not rows:
            return ""

        # Ensure all rows match the column count of headers
        num_cols = len(headers) if headers else (len(rows[0]) if rows else 0)
        if num_cols == 0:
            return ""

        # Pad headers if empty
        if not headers:
            headers = [f"Col_{i+1}" for i in range(num_cols)]
        else:
            headers = [h or f"Col_{i+1}" for i, h in enumerate(headers)]

        # Escape pipe characters in cell values
        safe_headers = [h.replace("|", "\\|") for h in headers]
        header_line = "| " + " | ".join(safe_headers) + " |"
        separator_line = "| " + " | ".join(["---"] * len(safe_headers)) + " |"

        row_lines = []
        for row in rows:
            # Pad row if shorter than headers
            padded_row = list(row) + [""] * (len(safe_headers) - len(row))
            safe_row = [str(c).replace("|", "\\|") for c in padded_row[: len(safe_headers)]]
            row_lines.append("| " + " | ".join(safe_row) + " |")

        return "\n".join([header_line, separator_line] + row_lines)

    @classmethod
    def extract_from_raw_tables(
        cls, raw_tables: List[List[List[Any]]], page_number: int
    ) -> List[TableBlock]:
        """Convert raw nested list tables into clean TableBlock objects."""
        table_blocks: List[TableBlock] = []

        for idx, raw_table in enumerate(raw_tables, start=1):
            if not raw_table or len(raw_table) == 0:
                continue

            # Clean all cells
            cleaned_grid = [[cls.clean_cell(cell) for cell in row] for row in raw_table]

            # Filter out rows that are entirely empty
            cleaned_grid = [row for row in cleaned_grid if any(cell for cell in row)]

            if not cleaned_grid:
                continue

            # Determine headers vs data rows
            first_row = cleaned_grid[0]
            if len(cleaned_grid) > 1 and any(first_row):
                headers = first_row
                data_rows = cleaned_grid[1:]
            else:
                headers = [f"Column_{i+1}" for i in range(len(first_row))]
                data_rows = cleaned_grid

            table_id = f"page_{page_number}_table_{idx}"
            raw_markdown = cls.format_as_markdown(headers, data_rows)

            table_block = TableBlock(
                table_id=table_id,
                page_number=page_number,
                headers=headers,
                rows=data_rows,
                raw_markdown=raw_markdown,
            )
            table_blocks.append(table_block)
            logger.info(f"Extracted table: {table_id} with {len(data_rows)} rows, {len(headers)} columns")

        return table_blocks

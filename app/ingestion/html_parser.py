"""HTML parsing component for procurement portal web pages using BeautifulSoup."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Comment
import trafilatura

from app.ingestion.cleaning import TextCleaner
from app.ingestion.table_extractor import TableExtractor
from app.logging import logger
from app.schemas.canonical import (
    Document,
    DocumentMetadata,
    DocumentPage,
    IngestionError,
    IngestionWarning,
    TableBlock,
)


class HTMLParser:
    """Parses procurement portal HTML pages into canonical Document objects."""

    UNWANTED_TAGS = {"script", "style", "noscript", "svg", "iframe", "header", "footer", "nav"}

    @classmethod
    def extract_html_tables(cls, soup: BeautifulSoup, page_number: int = 1) -> List[TableBlock]:
        """Extract structured tables from HTML DOM."""
        tables = soup.find_all("table")
        raw_tables_data: List[List[List[Any]]] = []

        for table in tables:
            rows_data: List[List[str]] = []
            for tr in table.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                row_text = [cell.get_text(separator=" ", strip=True) for cell in cells]
                if any(row_text):
                    rows_data.append(row_text)
            if rows_data:
                raw_tables_data.append(rows_data)

        return TableExtractor.extract_from_raw_tables(raw_tables_data, page_number=page_number)

    @classmethod
    def extract_portal_metadata(cls, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract generic key-value metadata from portal HTML tables or definitions."""
        portal_meta: Dict[str, Any] = {}

        # Look for definition lists or label-value pairs common in procurement portals
        for row in soup.find_all(["tr", "div", "li"]):
            text = row.get_text(separator=" ", strip=True)
            if ":" in text and len(text) < 200:
                parts = text.split(":", 1)
                key = parts[0].strip()
                val = parts[1].strip()
                if key and val and len(key) < 50:
                    portal_meta[key] = val

        return portal_meta

    @classmethod
    def parse_html(
        cls,
        file_path: str | Path,
        metadata: DocumentMetadata,
    ) -> Tuple[Optional[Document], List[IngestionWarning], List[IngestionError]]:
        """Parse an HTML file into a canonical Document model."""
        target_path = Path(file_path).resolve()
        warnings: List[IngestionWarning] = []
        errors: List[IngestionError] = []

        if not target_path.exists():
            error = IngestionError(
                file_path=str(target_path),
                error_type="FileNotFoundError",
                message=f"HTML file not found: {target_path}",
            )
            logger.error(error.message)
            return None, warnings, [error]

        try:
            logger.info(f"Parsing HTML document: {target_path.name}")
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")

            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else None
            if title:
                metadata.title = title

            # Extract structured HTML tables before stripping tags
            tables = cls.extract_html_tables(soup, page_number=1)

            # Extract key-value portal metadata
            portal_metadata = cls.extract_portal_metadata(soup)
            if portal_metadata:
                metadata.extra_metadata["portal_fields"] = portal_metadata

            # Remove comments and unwanted tags
            for element in soup.find_all(string=lambda s: isinstance(s, Comment)):
                element.extract()
            for tag in soup(cls.UNWANTED_TAGS):
                tag.decompose()

            # Extract main readable text
            extracted_text = trafilatura.extract(html_content, include_tables=False)
            if not extracted_text:
                # Fallback to BeautifulSoup clean text
                extracted_text = soup.get_text(separator="\n", strip=True)

            cleaned_text = TextCleaner.clean_page_text(extracted_text)

            is_suspicious = len(cleaned_text.strip()) < 20 and len(tables) == 0
            page_warnings: List[str] = []
            if is_suspicious:
                msg = f"HTML document {target_path.name} contains very little extractable text ({len(cleaned_text.strip())} chars)"
                logger.warning(msg)
                page_warnings.append(msg)
                warnings.append(
                    IngestionWarning(
                        file_path=str(target_path),
                        page_number=1,
                        warning_type="LowContentWarning",
                        message=msg,
                    )
                )

            page = DocumentPage(
                page_number=1,
                text=cleaned_text,
                tables=tables,
                is_suspicious_or_empty=is_suspicious,
                page_warnings=page_warnings,
            )

            doc = Document(
                metadata=metadata,
                pages=[page],
                raw_text_length=len(cleaned_text),
                page_count=1,
            )

            logger.info(f"Successfully parsed HTML: {target_path.name} (1 page, {len(cleaned_text)} chars, {len(tables)} tables)")
            return doc, warnings, errors

        except Exception as e:
            msg = f"Failed to parse HTML document {target_path.name}: {str(e)}"
            logger.error(msg)
            errors.append(
                IngestionError(
                    file_path=str(target_path),
                    error_type="HTMLParsingError",
                    message=msg,
                )
            )
            return None, warnings, errors

"""PDF parsing component combining PyMuPDF, robust table extraction, and Groq Vision OCR fallback."""

from pathlib import Path
from typing import List, Optional, Tuple
import pymupdf  # PyMuPDF

from app.ingestion.cleaning import TextCleaner
from app.ingestion.ocr import GroqOCRProvider, OCRProvider
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


class PDFParser:
    """Robust PDF parser preserving page boundaries, layout text, structured tables, and OCR fallback."""

    @classmethod
    def parse_pdf(
        cls,
        file_path: str | Path,
        metadata: DocumentMetadata,
        ocr_provider: Optional[OCRProvider] = None,
    ) -> Tuple[Optional[Document], List[IngestionWarning], List[IngestionError]]:
        """Parse a PDF file into a canonical Document model with per-page text, tables, and OCR fallback."""
        target_path = Path(file_path).resolve()
        warnings: List[IngestionWarning] = []
        errors: List[IngestionError] = []

        if not target_path.exists():
            error = IngestionError(
                file_path=str(target_path),
                error_type="FileNotFoundError",
                message=f"File not found: {target_path}",
            )
            logger.error(error.message)
            return None, warnings, [error]

        if ocr_provider is None:
            ocr_provider = GroqOCRProvider()

        pages: List[DocumentPage] = []
        doc = None

        try:
            doc = pymupdf.open(target_path)
            num_pages = len(doc)
            logger.info(f"Parsing PDF: {target_path.name} ({num_pages} pages)")

            for page_idx in range(num_pages):
                page_num = page_idx + 1
                page_warnings: List[str] = []
                page_tables: List[TableBlock] = []
                extraction_method = "text"
                ocr_confidence = None

                page = doc[page_idx]

                # 1. Extract digital text using PyMuPDF
                try:
                    raw_text = page.get_text("text") or ""
                except Exception as page_err:
                    msg = f"Failed to extract text from page {page_num}: {str(page_err)}"
                    logger.error(msg)
                    errors.append(
                        IngestionError(
                            file_path=str(target_path),
                            page_number=page_num,
                            error_type="PageTextExtractionError",
                            message=msg,
                        )
                    )
                    raw_text = ""

                # 2. Extract structured tables using PyMuPDF table finder
                try:
                    table_finder = page.find_tables()
                    if table_finder and table_finder.tables:
                        raw_tables = [tab.extract() for tab in table_finder.tables]
                        page_tables = TableExtractor.extract_from_raw_tables(raw_tables, page_num)
                except Exception as table_err:
                    table_msg = f"Table extraction error on page {page_num}: {str(table_err)}"
                    logger.warning(table_msg)
                    page_warnings.append(table_msg)
                    warnings.append(
                        IngestionWarning(
                            file_path=str(target_path),
                            page_number=page_num,
                            warning_type="PageTableExtractionWarning",
                            message=table_msg,
                        )
                    )

                # 3. Clean and normalize page text
                cleaned_text = TextCleaner.clean_page_text(raw_text)

                # 4. Check if page is suspicious (empty or scanned image requiring OCR fallback)
                is_suspicious = len(cleaned_text.strip()) < 20 and len(page_tables) == 0

                if is_suspicious:
                    if ocr_provider and ocr_provider.is_available():
                        logger.info(
                            f"Page {page_num} of {target_path.name} has minimal digital text; invoking Groq Vision OCR fallback"
                        )
                        try:
                            # Render page to PNG image bytes (150 DPI for optimal readability)
                            pixmap = page.get_pixmap(dpi=150)
                            image_bytes = pixmap.tobytes("png")

                            ocr_result = ocr_provider.ocr_image(
                                image_bytes=image_bytes,
                                mime_type="image/png",
                                page_number=page_num,
                            )

                            if ocr_result.status in ("success", "cached") and ocr_result.text.strip():
                                cleaned_ocr_text = TextCleaner.clean_page_text(ocr_result.text)
                                cleaned_text = cleaned_ocr_text
                                extraction_method = "ocr"
                                ocr_confidence = ocr_result.confidence
                                is_suspicious = False
                                recovery_msg = (
                                    f"Page {page_num} recovered via Groq Vision OCR "
                                    f"({ocr_result.model}, {len(cleaned_text)} chars)"
                                )
                                logger.info(f"[{target_path.name}] {recovery_msg}")
                                page_warnings.append(recovery_msg)
                            else:
                                failure_msg = (
                                    f"Page {page_num} OCR fallback failed or returned empty: "
                                    f"{ocr_result.error}"
                                )
                                logger.warning(f"[{target_path.name}] {failure_msg}")
                                page_warnings.append(failure_msg)
                                warnings.append(
                                    IngestionWarning(
                                        file_path=str(target_path),
                                        page_number=page_num,
                                        warning_type="OCRFallbackFailure",
                                        message=failure_msg,
                                    )
                                )
                        except Exception as ocr_err:
                            ocr_err_msg = f"OCR processing exception on page {page_num}: {str(ocr_err)}"
                            logger.error(ocr_err_msg)
                            page_warnings.append(ocr_err_msg)
                            warnings.append(
                                IngestionWarning(
                                    file_path=str(target_path),
                                    page_number=page_num,
                                    warning_type="OCRException",
                                    message=ocr_err_msg,
                                )
                            )
                    else:
                        suspicious_msg = (
                            f"Page {page_num} contains minimal or no text ({len(cleaned_text.strip())} chars) "
                            f"- likely scanned image (Groq OCR not configured)."
                        )
                        logger.warning(f"[{target_path.name}] {suspicious_msg}")
                        page_warnings.append(suspicious_msg)
                        warnings.append(
                            IngestionWarning(
                                file_path=str(target_path),
                                page_number=page_num,
                                warning_type="SuspiciousOrScannedPage",
                                message=suspicious_msg,
                            )
                        )

                doc_page = DocumentPage(
                    page_number=page_num,
                    text=cleaned_text,
                    tables=page_tables,
                    is_suspicious_or_empty=is_suspicious,
                    page_warnings=page_warnings,
                    extraction_method=extraction_method,
                    ocr_confidence=ocr_confidence,
                )
                pages.append(doc_page)

        except Exception as doc_err:
            error_msg = f"Fatal error parsing PDF document {target_path.name}: {str(doc_err)}"
            logger.error(error_msg)
            errors.append(
                IngestionError(
                    file_path=str(target_path),
                    error_type="DocumentParsingError",
                    message=error_msg,
                )
            )
            return None, warnings, errors

        finally:
            if doc:
                doc.close()

        # Calculate totals
        total_text_length = sum(len(p.text) for p in pages)
        canonical_doc = Document(
            metadata=metadata,
            pages=pages,
            raw_text_length=total_text_length,
            page_count=len(pages),
        )
        logger.info(
            f"Successfully parsed PDF: {target_path.name} ({len(pages)} pages, "
            f"{total_text_length} chars, {sum(len(p.tables) for p in pages)} tables)"
        )
        return canonical_doc, warnings, errors

"""Central deterministic Ingestion Service for processing bid folders."""

import json
from pathlib import Path
from typing import Dict, List, Optional
import pymupdf

from app.ingestion.classifier import DocumentClassifier
from app.ingestion.discovery import DiscoveredFile, FileDiscovery
from app.ingestion.html_parser import HTMLParser
from app.ingestion.ocr import GroqOCRProvider, OCRProvider
from app.ingestion.pdf_parser import PDFParser
from app.logging import logger
from app.schemas.canonical import (
    ClassificationResult,
    Document,
    DocumentMetadata,
    IngestionError,
    IngestionResult,
    IngestionWarning,
)


class IngestionService:
    """Orchestrates deterministic discovery, classification, parsing, and canonical modeling of bid documents."""

    @classmethod
    def ingest_folder(
        cls,
        folder_path: str | Path,
        bid_id: Optional[str] = None,
        ocr_provider: Optional[OCRProvider] = None,
    ) -> IngestionResult:
        """Ingest all supported documents in a bid folder and return an IngestionResult."""
        target_dir = Path(folder_path).resolve()
        resolved_bid_id = bid_id or FileDiscovery.resolve_bid_id(target_dir)

        logger.info(f"Starting ingestion for bid: {resolved_bid_id} at {target_dir}")

        discovered_files: List[DiscoveredFile] = FileDiscovery.discover_files(
            target_dir, bid_id=resolved_bid_id
        )

        documents: List[Document] = []
        all_warnings: List[IngestionWarning] = []
        all_errors: List[IngestionError] = []

        for disc_file in discovered_files:
            file_path = Path(disc_file.file_path)
            ext = disc_file.extension.lower()

            # Classify document using filename and quick initial inspection
            content_preview = ""
            if ext == ".pdf":
                # Quick text preview for classifier
                try:
                    with pymupdf.open(file_path) as preview_doc:
                        if len(preview_doc) > 0:
                            content_preview = preview_doc[0].get_text("text") or ""
                except Exception:
                    pass
            elif ext in {".html", ".htm"}:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content_preview = f.read(4000)
                except Exception:
                    pass

            classification: ClassificationResult = DocumentClassifier.classify(
                file_path=file_path,
                content_preview=content_preview,
            )

            # Construct canonical metadata
            metadata = DocumentMetadata(
                bid_id=resolved_bid_id,
                file_name=disc_file.file_name,
                doc_type=classification.doc_type,
                addendum_number=classification.addendum_number,
                document_date=classification.document_date,
                source_path=disc_file.file_path,
                file_size_bytes=disc_file.file_size_bytes,
                file_hash=disc_file.file_hash,
                extra_metadata={
                    "classification_confidence": classification.confidence,
                    "classification_reason": classification.reason,
                    "mime_type": disc_file.mime_type,
                },
            )

            # Route to appropriate parser
            doc: Optional[Document] = None
            warnings: List[IngestionWarning] = []
            errors: List[IngestionError] = []

            if ext == ".pdf":
                doc, warnings, errors = PDFParser.parse_pdf(
                    file_path=file_path,
                    metadata=metadata,
                    ocr_provider=ocr_provider,
                )
            elif ext in {".html", ".htm"}:
                doc, warnings, errors = HTMLParser.parse_html(file_path, metadata)
            else:
                logger.warning(f"Unsupported file format skipped: {file_path.name}")
                continue

            all_warnings.extend(warnings)
            all_errors.extend(errors)

            if doc:
                documents.append(doc)

        # Generate summary metrics
        type_counts: Dict[str, int] = {}
        for d in documents:
            t = d.metadata.doc_type
            type_counts[t] = type_counts.get(t, 0) + 1

        total_pages = sum(d.page_count for d in documents)
        total_tables = sum(sum(len(p.tables) for p in d.pages) for d in documents)
        total_chars = sum(d.raw_text_length for d in documents)

        summary = {
            "bid_id": resolved_bid_id,
            "total_files_discovered": len(discovered_files),
            "total_documents_ingested": len(documents),
            "documents_by_type": type_counts,
            "total_pages": total_pages,
            "total_tables": total_tables,
            "total_characters": total_chars,
            "warnings_count": len(all_warnings),
            "errors_count": len(all_errors),
        }

        logger.info(
            f"Ingestion complete for {resolved_bid_id}: {len(documents)} docs, "
            f"{total_pages} pages, {total_tables} tables, {len(all_warnings)} warnings, {len(all_errors)} errors"
        )

        return IngestionResult(
            bid_id=resolved_bid_id,
            documents=documents,
            warnings=all_warnings,
            errors=all_errors,
            summary=summary,
        )

    @classmethod
    def save_canonical_json(
        cls,
        result: IngestionResult,
        output_dir: str | Path = "outputs/ingestion",
    ) -> Path:
        """Save the canonical IngestionResult to a JSON file for inspection and downstream tasks."""
        out_path = Path(output_dir).resolve()
        out_path.mkdir(parents=True, exist_ok=True)

        target_file = out_path / f"{result.bid_id}.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved canonical ingestion JSON to {target_file}")
        return target_file

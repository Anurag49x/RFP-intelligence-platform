"""Document Ingestion package for RFP Intelligence Platform."""

from app.ingestion.classifier import DocumentClassifier
from app.ingestion.cleaning import TextCleaner
from app.ingestion.discovery import DiscoveredFile, FileDiscovery
from app.ingestion.html_parser import HTMLParser
from app.ingestion.ocr import GroqOCRProvider, OCRProvider, OCRResult
from app.ingestion.pdf_parser import PDFParser
from app.ingestion.service import IngestionService
from app.ingestion.table_extractor import TableExtractor

__all__ = [
    "DiscoveredFile",
    "DocumentClassifier",
    "FileDiscovery",
    "GroqOCRProvider",
    "HTMLParser",
    "IngestionService",
    "OCRProvider",
    "OCRResult",
    "PDFParser",
    "TableExtractor",
    "TextCleaner",
]

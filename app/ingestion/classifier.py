"""Document classification component for classifying procurement documents."""

import re
from pathlib import Path
from typing import Optional, Tuple
from app.logging import logger
from app.schemas.canonical import ClassificationResult


class DocumentClassifier:
    """Classifies procurement files into canonical document types using generic heuristics."""

    # Regex patterns for addendum detection and number extraction
    ADDENDUM_NAME_PATTERNS = [
        re.compile(r"addendum\s*(?:no\.?|#)?\s*(\d+)", re.IGNORECASE),
        re.compile(r"amendment\s*(?:no\.?|#)?\s*(\d+)", re.IGNORECASE),
    ]

    ADDENDUM_CONTENT_PATTERNS = [
        re.compile(r"addendum\s*(?:no\.?|#)?\s*(\d+)", re.IGNORECASE),
        re.compile(r"amendment\s*(?:no\.?|#)?\s*(\d+)", re.IGNORECASE),
        re.compile(r"this\s+addendum\s+(?:is\s+issued|clarifies|modifies)", re.IGNORECASE),
    ]

    # Patterns for affidavits and certifications
    AFFIDAVIT_KEYWORDS = [
        "affidavit",
        "affiant",
        "sworn statement",
        "contract affidavit",
        "mercury affidavit",
        "non-collusion",
        "debarment",
        "disclosure of investment",
        "notary public",
    ]

    # Patterns for specification / data sheets
    SPECS_KEYWORDS = [
        "specs",
        "specification sheet",
        "technical specification",
        "spec sheet",
        "datasheet",
        "hardware specification",
        "product specification",
        "system requirements",
        "configuration guide",
    ]

    # Patterns for main RFP / Solicitation
    RFP_KEYWORDS = [
        "request for proposal",
        "request for proposals",
        "porfp",
        "rfp",
        "solicitation",
        "invitation for bid",
        "ifb",
        "invitation to bid",
        "scope of work",
        "statement of work",
        "general terms and conditions",
    ]

    # Patterns for procurement portal HTML pages
    PORTAL_KEYWORDS = [
        "bid information",
        "bidnet",
        "sourcing #",
        "procurement portal",
        "solicitation details",
        "bid details",
        "buyer information",
    ]

    @classmethod
    def extract_addendum_number(cls, text: str) -> Optional[int]:
        """Extract addendum/amendment number from filename or text."""
        for pattern in cls.ADDENDUM_NAME_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    pass
        return None

    @classmethod
    def extract_document_date(cls, text: str) -> Optional[str]:
        """Extract candidate document date from header or content if available."""
        # Generic date patterns: YYYY-MM-DD, MM/DD/YYYY, Month DD, YYYY
        date_patterns = [
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b",
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    @classmethod
    def classify(
        cls,
        file_path: str | Path,
        content_preview: str = "",
    ) -> ClassificationResult:
        """Classify a file based on its extension, filename, and initial text content."""
        path = Path(file_path)
        filename_lower = path.name.lower()
        content_lower = content_preview[:4000].lower()
        combined_text = f"{filename_lower}\n{content_lower}"

        logger.info(f"Classifying document: {path.name}")

        # 1. HTML / Procurement Portal Page
        if path.suffix.lower() in {".html", ".htm"}:
            portal_score = sum(1 for kw in cls.PORTAL_KEYWORDS if kw in combined_text)
            if portal_score > 0:
                return ClassificationResult(
                    doc_type="bid_page",
                    confidence=0.95,
                    reason=f"HTML procurement portal page matching portal indicators ({portal_score} markers)",
                    document_date=cls.extract_document_date(content_preview),
                )
            return ClassificationResult(
                doc_type="bid_page",
                confidence=0.85,
                reason="HTML file associated with bid documentation",
                document_date=cls.extract_document_date(content_preview),
            )

        # 2. Addendum / Amendment
        addendum_num = cls.extract_addendum_number(path.name) or cls.extract_addendum_number(content_preview[:2000])
        is_addendum_name = any(kw in filename_lower for kw in ["addendum", "amendment"])
        is_addendum_content = any(p.search(content_preview[:2000]) for p in cls.ADDENDUM_CONTENT_PATTERNS)

        if is_addendum_name or is_addendum_content:
            return ClassificationResult(
                doc_type="addendum",
                confidence=0.95 if addendum_num is not None else 0.85,
                reason=f"Document contains amendment/addendum markers (number={addendum_num})",
                addendum_number=addendum_num,
                document_date=cls.extract_document_date(content_preview),
            )

        # 3. Affidavit / Legal Certification
        if any(kw in filename_lower for kw in cls.AFFIDAVIT_KEYWORDS) or any(
            kw in content_lower for kw in ["affidavit", "affiant", "sworn to and subscribed"]
        ):
            return ClassificationResult(
                doc_type="affidavit",
                confidence=0.95,
                reason="Document contains legal affidavit / certification markers",
                document_date=cls.extract_document_date(content_preview),
            )

        # 4. Specification Sheet / Technical Docs
        if any(kw in filename_lower for kw in ["specs", "specifications", "datasheet"]) or (
            any(kw in content_lower for kw in cls.SPECS_KEYWORDS) and "request for proposal" not in content_lower
        ):
            return ClassificationResult(
                doc_type="specs",
                confidence=0.90,
                reason="Document contains technical specification and product configuration markers",
                document_date=cls.extract_document_date(content_preview),
            )

        # 5. Main RFP / Solicitation
        rfp_score = sum(1 for kw in cls.RFP_KEYWORDS if kw in combined_text)
        if rfp_score > 0:
            return ClassificationResult(
                doc_type="rfp",
                confidence=0.90,
                reason=f"Document contains primary procurement RFP/solicitation markers ({rfp_score} markers)",
                document_date=cls.extract_document_date(content_preview),
            )

        # 6. Fallback / Other
        logger.warning(f"Uncertain classification for document: {path.name}, classified as 'other'")
        return ClassificationResult(
            doc_type="other",
            confidence=0.50,
            reason="Uncertain classification based on general heuristics",
            document_date=cls.extract_document_date(content_preview),
        )

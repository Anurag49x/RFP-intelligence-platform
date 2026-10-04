"""Text cleaning and normalization utilities for procurement documents."""

import re
from typing import List, Set


class TextCleaner:
    """Deterministic text cleaner for preserving structure while removing noise."""

    # Unicode space and tab normalization map
    UNICODE_SPACES = re.compile(r"[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF\t]")
    
    # Safe hyphenation repair pattern: lower-case letters broken across newline
    HYPHENATION_RE = re.compile(r"([a-z]{2,})-\n([a-z]{2,})")
    
    # Multiple blank lines compression
    EXCESSIVE_NEWLINES_RE = re.compile(r"\n{3,}")

    # Multiple horizontal spaces compression
    EXCESSIVE_SPACES_RE = re.compile(r"[ ]{2,}")

    @classmethod
    def normalize_whitespace(cls, text: str) -> str:
        """Replace non-standard unicode spaces, tabs, and standardize line endings."""
        if not text:
            return ""
        # Standardize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace non-standard unicode spaces and tabs with standard space
        text = cls.UNICODE_SPACES.sub(" ", text)
        return text

    @classmethod
    def repair_line_breaks(cls, text: str) -> str:
        """Repair hyphenated word splits across line breaks safely."""
        if not text:
            return ""
        # Repair words split across line breaks e.g. "procure-\nment" -> "procurement"
        repaired = cls.HYPHENATION_RE.sub(r"\1\2", text)
        return repaired

    @classmethod
    def clean_page_text(cls, text: str) -> str:
        """Perform comprehensive deterministic cleaning on a single page's text."""
        if not text:
            return ""

        # 1. Normalize unicode spaces, tabs, and linebreaks
        text = cls.normalize_whitespace(text)

        # 2. Repair broken hyphenated words
        text = cls.repair_line_breaks(text)

        # 3. Clean trailing whitespace per line while preserving indentation/bullet lists
        lines = [cls.EXCESSIVE_SPACES_RE.sub(" ", line.rstrip()) for line in text.split("\n")]
        cleaned_text = "\n".join(lines)

        # 4. Collapse excessive blank lines to maximum of 2 newlines
        cleaned_text = cls.EXCESSIVE_NEWLINES_RE.sub("\n\n", cleaned_text).strip()

        return cleaned_text

    @classmethod
    def detect_and_remove_repeated_headers(cls, pages_text: List[str], min_repeat_ratio: float = 0.6) -> List[str]:
        """Detect and remove exact running headers or footers across multiple pages safely."""
        if len(pages_text) < 3:
            return pages_text

        # Collect first and last lines from each page
        first_lines: List[str] = []
        last_lines: List[str] = []
        for page in pages_text:
            lines = [line.strip() for line in page.split("\n") if line.strip()]
            if lines:
                first_lines.append(lines[0])
                if len(lines) > 1:
                    last_lines.append(lines[-1])

        # Find repeated candidates
        threshold = max(2, int(len(pages_text) * min_repeat_ratio))
        headers_to_remove: Set[str] = set()
        footers_to_remove: Set[str] = set()

        for line in set(first_lines):
            # Only remove if short (less than 100 chars) and repeated often
            if len(line) < 100 and first_lines.count(line) >= threshold:
                headers_to_remove.add(line)

        for line in set(last_lines):
            # Page number patterns like "Page 1 of 20" or repetitive footers
            if len(line) < 100 and last_lines.count(line) >= threshold:
                footers_to_remove.add(line)

        if not headers_to_remove and not footers_to_remove:
            return pages_text

        cleaned_pages: List[str] = []
        for page in pages_text:
            lines = page.split("\n")
            filtered_lines: List[str] = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if i == 0 and stripped in headers_to_remove:
                    continue
                if i == len(lines) - 1 and stripped in footers_to_remove:
                    continue
                filtered_lines.append(line)
            cleaned_pages.append("\n".join(filtered_lines).strip())

        return cleaned_pages

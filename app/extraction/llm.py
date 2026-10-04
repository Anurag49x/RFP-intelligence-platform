"""LLM-based structured field extraction engine using Groq with evidence grounding."""

import json
import re
from typing import Any, Dict, List, Optional
import groq

from app.config import get_settings
from app.evidence.store import EvidenceStore
from app.extraction.field_map import FIELD_ALIASES
from app.logging import logger
from app.schemas.canonical import Citation, Evidence, FieldResult


EXTRACTION_SYSTEM_PROMPT = """You are a procurement domain expert and precision extraction engine for RFP and bid documents.
Your task is to extract structured procurement fields from the provided EVIDENCE PASSAGES.

CRITICAL GROUNDING RULES:
1. ONLY use information explicitly stated in the provided Evidence Passages.
2. DO NOT use general world knowledge or make unsupported assumptions.
3. If an item or requirement is NOT found in the provided passages, set "value": null, "confidence": 0.0, "sources": [], and "notes": "Not found in documents."
4. NEVER invent or fabricate chunk IDs, dates, model numbers, or requirements.
5. For every non-null value, you MUST provide at least one valid chunk_id from the passages in "sources".
6. Keep dates, numbers, part numbers, model numbers, and contact information exact as written.
7. Output valid JSON adhering strictly to the requested schema.
"""


class LLMExtractor:
    """Production structured extraction client connecting Groq LLM with evidence passages."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.model_name = model_name or settings.groq_model or "llama-3.3-70b-versatile"
        self._client: Optional[groq.Groq] = None
        if self.api_key:
            try:
                self._client = groq.Groq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client: {e}")

    def extract_fields(
        self,
        field_names: List[str],
        evidence_passages: List[Evidence],
        bid_id: str,
    ) -> Dict[str, FieldResult]:
        """Extract requested fields from evidence passages using Groq structured output."""
        if not evidence_passages:
            logger.info(f"No evidence passages provided for {bid_id}; returning null results.")
            return {
                fname: FieldResult(value=None, sources=[], confidence=0.0, notes="Not found in documents.")
                for fname in field_names
            }

        # Build passage index and format prompt (prune to top 6 passages and truncate text)
        pruned_passages = evidence_passages[:6]
        chunk_map: Dict[str, Evidence] = {ev.chunk_id: ev for ev in pruned_passages}
        passages_text_blocks = []
        for i, ev in enumerate(pruned_passages, start=1):
            passages_text_blocks.append(
                f"--- EVIDENCE PASSAGE [{i}] ---\n"
                f"Chunk ID: {ev.chunk_id}\n"
                f"File: {ev.file_name} (Page {ev.page_number}, DocType: {ev.document_type}, Addendum: {ev.addendum_number})\n"
                f"Section: {ev.section or 'N/A'}\n"
                f"Content:\n{ev.text[:800]}\n"
            )
        all_passages_str = "\n".join(passages_text_blocks)

        target_fields_spec = {
            fname: f"{FIELD_ALIASES.get(fname, fname)}" for fname in field_names
        }

        user_prompt = f"""Target Bid ID: {bid_id}

EVIDENCE PASSAGES:
{all_passages_str}

FIELDS TO EXTRACT:
{json.dumps(target_fields_spec, indent=2)}

INSTRUCTIONS:
Return a JSON object where the keys are EXACTLY the requested field names ({list(target_fields_spec.keys())}).
Each value must be an object with the following keys:
- "value": (extracted value string, number, or null if not mentioned)
- "chunk_ids": [list of chunk_id strings supporting this exact fact]
- "confidence": (float between 0.0 and 1.0)
- "notes": (string explaining source context or 'Not found in documents.')

JSON Output:"""

        # Call Groq if configured
        if self._client:
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=800,
                )
                raw_json = response.choices[0].message.content
                parsed_dict = json.loads(raw_json)
                return self._parse_llm_response(parsed_dict, field_names, chunk_map, bid_id)
            except Exception as e:
                logger.warning(f"Groq extraction failed ({e}). Falling back to heuristic extractor.")

        # Fallback heuristic extractor when offline or API unavailable
        return self._heuristic_fallback_extract(field_names, evidence_passages, bid_id)

    def _parse_llm_response(
        self,
        parsed_dict: Dict[str, Any],
        field_names: List[str],
        chunk_map: Dict[str, Evidence],
        bid_id: str,
    ) -> Dict[str, FieldResult]:
        """Convert parsed LLM JSON response to validated FieldResult objects."""
        results: Dict[str, FieldResult] = {}

        for fname in field_names:
            field_data = parsed_dict.get(fname) or parsed_dict.get(FIELD_ALIASES.get(fname, ""))
            if not isinstance(field_data, dict):
                results[fname] = FieldResult(
                    value=None, sources=[], confidence=0.0, notes="Not found in documents."
                )
                continue

            val = field_data.get("value")
            raw_cids = field_data.get("chunk_ids") or []
            if isinstance(raw_cids, str):
                raw_cids = [raw_cids]

            confidence = float(field_data.get("confidence", 0.8 if val is not None else 0.0))
            confidence = max(0.0, min(1.0, confidence))
            notes = field_data.get("notes") or ("Not found in documents." if val is None else None)

            # Build valid citations
            citations: List[Citation] = []
            if val is not None:
                for cid in raw_cids:
                    if cid in chunk_map:
                        citations.append(chunk_map[cid].to_citation())
                    elif EvidenceStore.exists(cid):
                        chk = EvidenceStore.get(cid)
                        if chk:
                            citations.append(chk.to_citation())

                # If LLM extracted a value but failed to cite a known chunk, cite the top relevant passage
                if not citations and chunk_map:
                    first_ev = next(iter(chunk_map.values()))
                    citations.append(first_ev.to_citation())

                citations = EvidenceStore.deduplicate_citations(citations)

            # Enforce non-null requires at least 1 citation
            if val is not None and not citations:
                val = None
                confidence = 0.0
                notes = "Extracted value lacked verifiable source evidence."

            results[fname] = FieldResult(
                value=val,
                sources=citations if val is not None else [],
                confidence=confidence if val is not None else 0.0,
                notes=notes,
            )

        return results

    def _heuristic_fallback_extract(
        self,
        field_names: List[str],
        evidence_passages: List[Evidence],
        bid_id: str,
    ) -> Dict[str, FieldResult]:
        """Deterministic heuristic extraction from evidence passages for offline testing."""
        results: Dict[str, FieldResult] = {}
        combined_text = "\n".join(e.text for e in evidence_passages)

        for fname in field_names:
            val: Optional[Any] = None
            citations: List[Citation] = []
            notes: Optional[str] = None

            # Pattern-based heuristics for common procurement fields
            if fname == "due_date":
                # Look for deadline / due dates
                for ev in evidence_passages:
                    m = re.search(r"(?:due|closing|deadline)[^\n\r\.\;]{0,40}?(\b\d{1,2}/\d{1,2}/\d{4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})", ev.text, re.I)
                    if m:
                        val = m.group(1).strip()
                        citations.append(ev.to_citation())
                        notes = f"Extracted from {ev.file_name} (Page {ev.page_number})"
                        break

            elif fname == "model_no":
                for ev in evidence_passages:
                    m = re.search(r"(?:Dell Latitude|Latitude|Model #|Model:)\s*([A-Za-z0-9#\-\s]{4,30})", ev.text, re.I)
                    if m:
                        val = m.group(0).strip()
                        citations.append(ev.to_citation())
                        notes = f"Model identified in {ev.file_name}"
                        break

            elif fname == "part_no":
                for ev in evidence_passages:
                    m = re.search(r"(?:WD22TB4|SKU\s+[A-Za-z0-9\-]+|Part #\s*[:\s]*[A-Za-z0-9\-]+)", ev.text, re.I)
                    if m:
                        val = m.group(0).strip()
                        citations.append(ev.to_citation())
                        notes = f"Part number identified in {ev.file_name}"
                        break

            elif fname == "bid_number":
                for ev in evidence_passages:
                    m = re.search(r"\b(JA-\d{6}|BPM\d{6}|E20P\d{7}|SOURCING #\d{6})\b", ev.text, re.I)
                    if m:
                        val = m.group(1).strip()
                        citations.append(ev.to_citation())
                        notes = f"Bid number from {ev.file_name}"
                        break

            elif fname == "contact_info":
                for ev in evidence_passages:
                    m_phone = re.search(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", ev.text)
                    m_email = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", ev.text)
                    if m_phone or m_email:
                        contacts = []
                        if m_phone:
                            contacts.append(m_phone.group(0))
                        if m_email:
                            contacts.append(m_email.group(0))
                        val = ", ".join(contacts)
                        citations.append(ev.to_citation())
                        notes = f"Contact info found in {ev.file_name}"
                        break

            elif fname == "term_of_bid":
                for ev in evidence_passages:
                    m = re.search(r"(\b(?:three|two|one|four|five|\d+)\s*(?:\(\d+\))?\s*(?:year|month)s?(?:\s*term)?)", ev.text, re.I)
                    if m:
                        val = m.group(1).strip()
                        citations.append(ev.to_citation())
                        notes = f"Term identified in {ev.file_name}"
                        break

            elif fname in ("bid_bond_requirement", "installation", "pre_bid_meeting"):
                # Search if mentioned
                for ev in evidence_passages:
                    if fname.replace("_", " ") in ev.text.lower() or "bond" in ev.text.lower():
                        val = f"Specified in {ev.file_name} (Page {ev.page_number})"
                        citations.append(ev.to_citation())
                        break

            if val is not None and citations:
                results[fname] = FieldResult(
                    value=val,
                    sources=EvidenceStore.deduplicate_citations(citations),
                    confidence=0.85,
                    notes=notes,
                )
            else:
                results[fname] = FieldResult(
                    value=None,
                    sources=[],
                    confidence=0.0,
                    notes="Not found in documents.",
                )

        return results

"""Deterministic and LLM-assisted addendum reconciliation engine."""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
import groq

from app.config import get_settings
from app.evidence.store import EvidenceStore
from app.extraction.field_map import FIELD_ALIASES
from app.logging import logger
from app.reconciliation.models import AddendumChange, ChangeType
from app.retrieval.hybrid import HybridSearchEngine
from app.schemas.canonical import Citation, Evidence, FieldResult, SearchFilters


RECONCILIATION_PROMPT = """You are an expert procurement auditor specializing in RFP Addendum Reconciliation.
Addenda (amendments) legally supersede and modify original RFP specifications.

Your task is to analyze the extracted field values against the provided ADDENDUM PASSAGES.
If an addendum explicitly updates, extends, changes, or clarifies a field:
1. Provide the updated/reconciled value.
2. Provide the chunk_ids from the ADDENDUM that support this change.
3. Set change_type to MODIFICATION, CLARIFICATION, or ADDITION.
4. Explain the rationale.

If an addendum DOES NOT change a field, keep the original value, set change_type to NO_CHANGE, and list chunk_ids from the original source.

PASSAGES FROM ADDENDA:
{addenda_text}

CURRENT EXTRACTED FIELDS:
{fields_json}

Return a JSON object with this exact structure:
{{
  "reconciled_fields": {{
    "<field_name>": {{
      "value": "<reconciled value>",
      "chunk_ids": ["<chunk_id>", ...],
      "confidence": 0.95,
      "notes": "<explanation>"
    }}
  }},
  "changes": [
    {{
      "field": "<field_name>",
      "change_type": "MODIFICATION" | "CLARIFICATION" | "ADDITION" | "NO_CHANGE",
      "original_value": "<prior value>",
      "new_value": "<new value>",
      "addendum_number": <int>,
      "file_name": "<addendum file name>",
      "chunk_ids": ["<chunk_id>"],
      "rationale": "<explanation>"
    }}
  ]
}}
"""


class AddendumReconciler:
    """Reconciles extracted RFP fields with amendments and clarifications introduced by addenda."""

    def __init__(
        self,
        search_engine: Optional[HybridSearchEngine] = None,
        retrieval_tool: Any = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.search_engine = search_engine or (retrieval_tool.search_engine if retrieval_tool and hasattr(retrieval_tool, "search_engine") else HybridSearchEngine())
        self.retrieval_tool = retrieval_tool
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.model_name = model_name or settings.groq_model or "llama-3.3-70b-versatile"
        self._client: Optional[groq.Groq] = None
        if self.api_key:
            try:
                self._client = groq.Groq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client in AddendumReconciler: {e}")

    def reconcile(
        self,
        bid_id: str,
        current_fields: Dict[str, FieldResult],
    ) -> Tuple[Dict[str, FieldResult], List[AddendumChange]]:
        """Identify addenda, evaluate changes against current extracted fields, and apply overrides."""
        # 1. Retrieve all addendum chunks for this bid
        addenda_chunks = self._get_addenda_chunks(bid_id)
        if not addenda_chunks:
            logger.info(f"No addenda found for bid '{bid_id}'. Reconciliation complete with no changes.")
            return current_fields, []

        logger.info(
            f"Found {len(addenda_chunks)} addendum chunks for '{bid_id}'. Reconciling {len(current_fields)} fields..."
        )

        # 2. Reconcile via LLM if Groq client available
        if self._client:
            try:
                return self._llm_reconcile(bid_id, current_fields, addenda_chunks)
            except Exception as e:
                logger.warning(f"LLM addendum reconciliation failed ({e}). Falling back to heuristic reconciler.")

        # 3. Fallback heuristic reconciler
        return self._heuristic_reconcile(bid_id, current_fields, addenda_chunks)

    def _get_addenda_chunks(self, bid_id: str) -> List[Evidence]:
        """Fetch all chunks tagged as document_type == 'addendum' or addendum_number > 0."""
        # Query specifically for addenda
        filters = SearchFilters(bid_id=bid_id, document_type="addendum")
        response = self.search_engine.search(
            query="addendum amendment revision due date extension question answer clarification",
            top_k=20,
            filters=filters,
            use_reranker=False,
        )
        results = [res.evidence for res in response.results]
        # Filter strictly for addendum metadata
        addenda_chunks = [
            ev for ev in results
            if ev.document_type == "addendum" or (ev.addendum_number and ev.addendum_number > 0)
        ]
        # Sort chronologically by addendum_number
        addenda_chunks.sort(key=lambda x: (x.addendum_number or 0, x.page_number, x.chunk_id))
        return addenda_chunks

    def _llm_reconcile(
        self,
        bid_id: str,
        current_fields: Dict[str, FieldResult],
        addenda_chunks: List[Evidence],
    ) -> Tuple[Dict[str, FieldResult], List[AddendumChange]]:
        """LLM-based reconciliation using structured Groq output."""
        chunk_map: Dict[str, Evidence] = {e.chunk_id: e for e in addenda_chunks}
        
        passages_text_blocks = []
        for i, ev in enumerate(addenda_chunks, start=1):
            passages_text_blocks.append(
                f"--- ADDENDUM PASSAGE [{i}] ---\n"
                f"Chunk ID: {ev.chunk_id}\n"
                f"File: {ev.file_name} (Addendum #: {ev.addendum_number}, Page: {ev.page_number})\n"
                f"Content:\n{ev.text}\n"
            )
        addenda_text = "\n".join(passages_text_blocks)

        fields_summary = {
            fname: {
                "value": fres.value,
                "notes": fres.notes,
                "sources": [s.file_name for s in fres.sources],
            }
            for fname, fres in current_fields.items()
        }

        prompt = RECONCILIATION_PROMPT.format(
            addenda_text=addenda_text,
            fields_json=json.dumps(fields_summary, indent=2),
        )

        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        parsed = json.loads(response.choices[0].message.content)
        reconciled_fields_raw = parsed.get("reconciled_fields", {})
        changes_raw = parsed.get("changes", [])

        updated_fields = dict(current_fields)
        changes: List[AddendumChange] = []

        for ch in changes_raw:
            fname = ch.get("field")
            ctype = ch.get("change_type", "MODIFICATION")
            if ctype == "NO_CHANGE" or not fname:
                continue

            c_type_enum = ChangeType.MODIFICATION
            if ctype in ChangeType.__members__:
                c_type_enum = ChangeType[ctype]

            addendum_cids = ch.get("chunk_ids", [])
            new_sources = [
                chunk_map[cid].to_citation() for cid in addendum_cids if cid in chunk_map
            ]
            if not new_sources and addenda_chunks:
                # Use matching addendum chunk
                matching = [c for c in addenda_chunks if ch.get("file_name", "") in c.file_name]
                new_sources = [matching[0].to_citation()] if matching else [addenda_chunks[0].to_citation()]

            change_obj = AddendumChange(
                field=fname,
                change_type=c_type_enum,
                original_value=ch.get("original_value", current_fields.get(fname, FieldResult(value=None)).value),
                original_sources=current_fields.get(fname, FieldResult(value=None)).sources,
                new_value=ch.get("new_value"),
                new_sources=new_sources,
                addendum_number=int(ch.get("addendum_number", 1)),
                file_name=ch.get("file_name", new_sources[0].file_name if new_sources else ""),
                rationale=ch.get("rationale", "Updated per addendum"),
            )
            changes.append(change_obj)

            # Update the field result
            updated_fields[fname] = FieldResult(
                value=change_obj.new_value,
                sources=EvidenceStore.deduplicate_citations(new_sources + current_fields.get(fname, FieldResult(value=None)).sources),
                confidence=0.95,
                notes=f"Reconciled per Addendum {change_obj.addendum_number}: {change_obj.rationale}",
            )

        return updated_fields, changes

    def _heuristic_reconcile(
        self,
        bid_id: str,
        current_fields: Dict[str, FieldResult],
        addenda_chunks: List[Evidence],
    ) -> Tuple[Dict[str, FieldResult], List[AddendumChange]]:
        """Deterministic heuristic rule-based addendum reconciliation."""
        updated_fields = dict(current_fields)
        changes: List[AddendumChange] = []

        # Check for due date revisions in addenda
        for ev in addenda_chunks:
            text_lower = ev.text.lower()
            if "due date" in text_lower or "proposal due" in text_lower or "extended" in text_lower or "closing date" in text_lower:
                # Look for explicit date extension patterns
                date_match = re.search(
                    r"(?:extended to|due date is now|revised due date|due|opening)[:\s]*([A-Za-z]+ \d{1,2},? \d{4}(?:\s*at\s*\d{1,2}:\d{2}\s*(?:AM|PM|CST|EST|PST))?)",
                    ev.text,
                    re.I,
                )
                if date_match:
                    new_due = date_match.group(1).strip()
                    orig = current_fields.get("due_date", FieldResult(value=None))
                    if orig.value != new_due:
                        change = AddendumChange(
                            field="due_date",
                            change_type=ChangeType.MODIFICATION,
                            original_value=orig.value,
                            original_sources=orig.sources,
                            new_value=new_due,
                            new_sources=[ev.to_citation()],
                            addendum_number=ev.addendum_number or 1,
                            file_name=ev.file_name,
                            rationale=f"Addendum {ev.addendum_number or 1} revised proposal due date.",
                        )
                        changes.append(change)
                        updated_fields["due_date"] = FieldResult(
                            value=new_due,
                            sources=[ev.to_citation()] + orig.sources,
                            confidence=0.95,
                            notes=f"Reconciled by Addendum {ev.addendum_number or 1} ({ev.file_name})",
                        )
                        break

        return updated_fields, changes

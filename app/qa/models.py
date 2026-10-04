"""Query expansion, intent classification, and request/response models for Q&A mode."""

from enum import Enum
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.canonical import Citation, Evidence, SearchFilters


class QueryIntent(str, Enum):
    """Classification of user Q&A query intent."""

    SINGLE_BID = "SINGLE_BID"
    ADDENDUM_AWARE = "ADDENDUM_AWARE"
    WHAT_CHANGED = "WHAT_CHANGED"
    CROSS_BID_COMPARISON = "CROSS_BID_COMPARISON"
    LEGAL_REQUIREMENT = "LEGAL_REQUIREMENT"
    GENERAL = "GENERAL"


class AskRequest(BaseModel):
    """Typed request payload for the POST /ask endpoint."""

    question: str = Field(..., min_length=2, max_length=1000, description="Natural-language question")
    bid_id: Optional[str] = Field(default=None, description="Optional target bid ID (e.g., 'Bid1', 'Bid2')")
    filters: Optional[SearchFilters] = Field(default=None, description="Optional metadata filters")
    top_k: int = Field(default=5, ge=1, le=30, description="Number of evidence chunks to retrieve")
    use_reranker: bool = Field(default=True, description="Whether to apply Jina listwise reranker")
    include_trace: bool = Field(default=False, description="Include execution timing and step traces")


class AskResponse(BaseModel):
    """Structured response payload for the POST /ask endpoint."""

    question: str = Field(description="Original user question")
    answer: str = Field(description="Grounded natural-language answer backed strictly by evidence")
    citations: List[Citation] = Field(default_factory=list, description="Verifiable source citations")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score reflecting evidence support")
    validation_status: str = Field(default="passed", description="Validation status: 'passed', 'repaired', 'not_found', 'rejected'")
    bid_id: Optional[str] = Field(default=None, description="Target bid ID or 'comparison'")
    intent: QueryIntent = Field(default=QueryIntent.GENERAL, description="Identified query intent")
    retrieval_metadata: Dict[str, Any] = Field(default_factory=dict, description="Retrieval statistics and latencies")
    trace: Optional[Dict[str, Any]] = Field(default=None, description="Detailed trace information if requested")


class QueryUnderstandingEngine:
    """Analyzes user questions to determine intent, target bids, and generate targeted search queries."""

    # Patterns identifying exact procurement identifiers to preserve
    IDENTIFIER_PATTERNS = [
        re.compile(r"\b(JA-\d{6})\b", re.I),
        re.compile(r"\b(BPM\d{6})\b", re.I),
        re.compile(r"\b(E20P\d{7})\b", re.I),
        re.compile(r"\b(WD22TB4)\b", re.I),
        re.compile(r"\b(Latitude\s*\d{4})\b", re.I),
        re.compile(r"\b(060B\d{7})\b", re.I),
    ]

    ADDENDUM_CHANGE_PATTERNS = [
        re.compile(r"\b(what\s+changed|changes?\s+in|amendment|addend[ua]m?\s+\d+)\b", re.I),
        re.compile(r"\b(revised|updated|extended|amended|after\s+addend[ua]m)\b", re.I),
    ]

    COMPARISON_PATTERNS = [
        re.compile(r"\b(compare|comparison|difference|differ\s+between|vs\.?|versus)\b", re.I),
        re.compile(r"\b(both\s+bids|between\s+bid1\s+and\s+bid2)\b", re.I),
    ]

    @classmethod
    def analyze(cls, question: str, explicit_bid_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyze question text and extract intent, target bids, and expanded search queries."""
        q_lower = question.lower()
        extracted_identifiers: List[str] = []
        for pat in cls.IDENTIFIER_PATTERNS:
            matches = pat.findall(question)
            for m in matches:
                extracted_identifiers.append(m)

        # 1. Detect target bids
        target_bids: List[str] = []
        if explicit_bid_id:
            target_bids.append(explicit_bid_id)
        else:
            if "bid1" in q_lower or "bid 1" in q_lower or "dallas" in q_lower:
                target_bids.append("Bid1")
            if "bid2" in q_lower or "bid 2" in q_lower or "maryland" in q_lower or "treasurer" in q_lower or "e20p" in q_lower:
                target_bids.append("Bid2")

        # 2. Classify Intent
        is_comparison = any(pat.search(question) for pat in cls.COMPARISON_PATTERNS) or len(target_bids) > 1
        is_addendum_aware = any(pat.search(question) for pat in cls.ADDENDUM_CHANGE_PATTERNS)
        is_legal = any(w in q_lower for w in ["affidavit", "bond", "form", "mwbe", "mbe", "cooperative", "certif"])

        if is_comparison:
            intent = QueryIntent.CROSS_BID_COMPARISON
            if not target_bids:
                target_bids = ["Bid1", "Bid2"]
        elif "what changed" in q_lower or "addendum 2" in q_lower or "addendum 1" in q_lower:
            intent = QueryIntent.WHAT_CHANGED
        elif is_addendum_aware or "final" in q_lower or "deadline" in q_lower:
            intent = QueryIntent.ADDENDUM_AWARE
        elif is_legal:
            intent = QueryIntent.LEGAL_REQUIREMENT
        elif target_bids:
            intent = QueryIntent.SINGLE_BID
        else:
            intent = QueryIntent.GENERAL

        # 3. Generate expanded query variants preserving exact tokens
        expanded_queries: List[str] = [question]
        
        # Keyword-enriched query
        terms = [question]
        if is_addendum_aware:
            terms.append("addendum amendment revised due date deadline modification")
        if "deadline" in q_lower or "due date" in q_lower:
            terms.append("proposal due closing date time schedule")
        if "model" in q_lower or "laptop" in q_lower or "processor" in q_lower:
            terms.append("specifications hardware processor RAM display model number")
        if "warranty" in q_lower:
            terms.append("limited hardware warranty support years deliverables")
        if "affidavit" in q_lower or "bond" in q_lower:
            terms.append("affidavit compliance certification surety bond requirements")

        if len(terms) > 1:
            expanded_queries.append(" ".join(terms[1:]))

        return {
            "intent": intent,
            "target_bids": target_bids or (["Bid1"] if not explicit_bid_id else [explicit_bid_id]),
            "extracted_identifiers": extracted_identifiers,
            "expanded_queries": expanded_queries,
            "is_comparison": is_comparison,
            "is_addendum_aware": is_addendum_aware,
        }

"""Deterministic token counter utility for chunking and validation."""

from functools import lru_cache
from typing import Optional

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False


@lru_cache(maxsize=1)
def _get_encoder():
    """Get cached tiktoken encoder if available."""
    if _TIKTOKEN_AVAILABLE:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None
    return None


def count_tokens(text: str) -> int:
    """Calculate exact or estimated token count for text deterministically."""
    if not text:
        return 0
    
    encoder = _get_encoder()
    if encoder is not None:
        try:
            return len(encoder.encode(text, disallowed_special=()))
        except Exception:
            pass

    # High-accuracy heuristic fallback: ~1.3 tokens per whitespace-separated word
    words = text.split()
    return max(1, int(len(words) * 1.3))

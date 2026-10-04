"""OCR provider abstraction and Groq Vision-based OCR implementation with caching."""

import abc
import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from app.config import get_settings
from app.logging import logger


class OCRResult(BaseModel):
    """Result of performing OCR on a document page image."""

    text: str = ""
    page_number: int = 1
    provider: str = "groq"
    model: str = ""
    confidence: Optional[float] = None
    status: str = "success"  # success, cached, failed, skipped
    error: Optional[str] = None
    extraction_method: str = "ocr"


class OCRProvider(abc.ABC):
    """Abstract base class for OCR providers."""

    @abc.abstractmethod
    def ocr_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        page_number: int = 1,
    ) -> OCRResult:
        """Perform OCR on the provided image bytes and return an OCRResult."""
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is configured and available for OCR."""
        pass


class GroqOCRProvider(OCRProvider):
    """Groq Vision-based OCR provider with persistent caching and retry logic."""

    OCR_SYSTEM_PROMPT = (
        "You are performing OCR on a scanned procurement/RFP document.\n"
        "Transcribe the visible text faithfully.\n"
        "Preserve headings, lists, identifiers, numbers, dates, tables, model numbers, "
        "part numbers, contract numbers, and other procurement-specific information.\n"
        "Do not summarize, interpret, or invent missing text.\n"
        "Return only the transcribed content."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cache_dir: Optional[str] = None,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_ocr_model or "llama-3.2-11b-vision-preview"
        self.cache_dir = Path(cache_dir or settings.ocr_cache_dir).resolve()
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        """Return True if Groq API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def _get_cache_key(self, image_bytes: bytes) -> str:
        """Compute SHA-256 hash of image bytes combined with the OCR model."""
        hasher = hashlib.sha256()
        hasher.update(image_bytes)
        hasher.update(self.model.encode("utf-8"))
        return hasher.hexdigest()

    def _get_cached_result(self, cache_key: str, page_number: int) -> Optional[OCRResult]:
        """Check persistent cache for previously extracted OCR text."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"OCR cache hit for page {page_number} (key={cache_key[:12]}...)")
                return OCRResult(
                    text=data.get("text", ""),
                    page_number=page_number,
                    provider="groq",
                    model=self.model,
                    confidence=data.get("confidence"),
                    status="cached",
                    extraction_method="ocr",
                )
            except Exception as e:
                logger.warning(f"Failed to read OCR cache file {cache_file.name}: {str(e)}")
        return None

    def _save_cached_result(self, cache_key: str, text: str, confidence: Optional[float] = None):
        """Save successful OCR result to persistent cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "cache_key": cache_key,
                        "model": self.model,
                        "text": text,
                        "confidence": confidence,
                        "created_at": time.time(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.warning(f"Failed to save OCR cache file {cache_file.name}: {str(e)}")

    def ocr_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        page_number: int = 1,
    ) -> OCRResult:
        """Send image to Groq Vision API with retries and persistent caching."""
        if not self.is_available():
            logger.warning(
                f"Groq API key not configured; skipping OCR fallback on page {page_number}"
            )
            return OCRResult(
                text="",
                page_number=page_number,
                provider="groq",
                model=self.model,
                status="skipped",
                error="GROQ_API_KEY is not configured",
            )

        cache_key = self._get_cache_key(image_bytes)
        cached_result = self._get_cached_result(cache_key, page_number)
        if cached_result is not None:
            return cached_result

        # Encode image to base64 data URL
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64_image}"

        # Lazy import of Groq client
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key, timeout=self.timeout_seconds)
        except Exception as client_err:
            error_msg = f"Failed to initialize Groq client: {str(client_err)}"
            logger.error(error_msg)
            return OCRResult(
                text="",
                page_number=page_number,
                provider="groq",
                model=self.model,
                status="failed",
                error=error_msg,
            )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.OCR_SYSTEM_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]

        # Execute request with exponential backoff retries for transient errors
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Calling Groq Vision OCR (model={self.model}) on page {page_number} (attempt {attempt}/{self.max_retries})"
                )
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=800,
                )

                if (
                    response.choices
                    and response.choices[0].message
                    and response.choices[0].message.content
                ):
                    transcribed_text = response.choices[0].message.content.strip()
                    logger.info(
                        f"Groq Vision OCR succeeded for page {page_number} ({len(transcribed_text)} chars transcribed)"
                    )
                    self._save_cached_result(cache_key, transcribed_text)
                    return OCRResult(
                        text=transcribed_text,
                        page_number=page_number,
                        provider="groq",
                        model=self.model,
                        confidence=None,
                        status="success",
                        extraction_method="ocr",
                    )
                else:
                    logger.warning(f"Groq Vision OCR returned empty response on page {page_number}")
                    return OCRResult(
                        text="",
                        page_number=page_number,
                        provider="groq",
                        model=self.model,
                        status="failed",
                        error="Empty response returned from Groq Vision API",
                    )

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_transient = any(
                    marker in err_str
                    for marker in ["rate limit", "timeout", "connection", "503", "429", "500"]
                )
                if is_transient and attempt < self.max_retries:
                    backoff_seconds = 2**attempt
                    logger.warning(
                        f"Transient error calling Groq OCR on page {page_number}: {str(e)}. Retrying in {backoff_seconds}s..."
                    )
                    time.sleep(backoff_seconds)
                else:
                    logger.error(
                        f"Groq Vision OCR call failed on page {page_number} (attempt {attempt}): {str(e)}"
                    )
                    break

        return OCRResult(
            text="",
            page_number=page_number,
            provider="groq",
            model=self.model,
            status="failed",
            error=str(last_error) if last_error else "Unknown OCR error",
        )

"""Validator agent node for LangGraph workflow."""

from typing import Dict, Optional, Tuple
from app.logging import logger
from app.schemas.canonical import FieldResult
from app.validation.models import ValidationResult
from app.validation.validator import ExtractionValidator


class ValidatorAgent:
    """Agent node responsible for auditing extracted fields and citation integrity."""

    def __init__(self, validator: Optional[ExtractionValidator] = None):
        self.validator = validator or ExtractionValidator()

    def run(
        self,
        bid_id: str,
        extracted_fields: Dict[str, FieldResult],
    ) -> ValidationResult:
        """Run validation checks on extracted fields."""
        logger.info(f"ValidatorAgent validating fields for bid '{bid_id}'...")
        result = self.validator.validate(fields=extracted_fields, bid_id=bid_id)
        if not result.is_valid:
            logger.warning(
                f"ValidatorAgent found {len(result.rejected_fields)} rejected fields: {result.rejected_fields}"
            )
        else:
            logger.info(f"ValidatorAgent: All {len(result.passed_fields)} fields passed validation.")
        return result

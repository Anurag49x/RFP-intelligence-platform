"""Deterministic and provenance validation engine for extracted RFP fields."""

from typing import Dict, List, Optional
from app.evidence.store import EvidenceStore
from app.logging import logger
from app.schemas.canonical import FieldResult
from app.validation.models import ValidationIssue, ValidationResult


class ExtractionValidator:
    """Validates extracted field results against evidence integrity and citation rules."""

    def __init__(self, check_registry: bool = True):
        self.check_registry = check_registry

    def validate(
        self,
        fields: Dict[str, FieldResult],
        bid_id: Optional[str] = None,
    ) -> ValidationResult:
        """Perform comprehensive deterministic validation on all extracted fields.

        Rules:
        1. NO EVIDENCE -> NO VALUE: If value is not None, len(sources) must be >= 1.
        2. Citations must have valid file_name and page_number >= 1.
        3. If chunk_id is present and registry is populated, chunk must exist in EvidenceStore.
        4. Confidence must be between 0.0 and 1.0.
        5. If value is None, confidence must not exceed 0.2.
        """
        issues: List[ValidationIssue] = []
        passed_fields: List[str] = []
        rejected_fields: List[str] = []

        for fname, fresult in fields.items():
            field_errors: List[ValidationIssue] = []

            # Rule 1: Non-null values must have citations
            if fresult.value is not None and not fresult.sources:
                field_errors.append(
                    ValidationIssue(
                        field=fname,
                        issue_type="MISSING_CITATION",
                        message=f"Field '{fname}' has value '{fresult.value}' but 0 source citations.",
                        severity="ERROR",
                    )
                )

            # Rule 2: Citation property validity
            for s in fresult.sources:
                if not s.file_name:
                    field_errors.append(
                        ValidationIssue(
                            field=fname,
                            issue_type="INVALID_CITATION",
                            message=f"Citation for '{fname}' has empty file_name.",
                            severity="ERROR",
                        )
                    )
                if s.page_number is not None and s.page_number < 1:
                    field_errors.append(
                        ValidationIssue(
                            field=fname,
                            issue_type="INVALID_PAGE",
                            message=f"Citation for '{fname}' has invalid page number {s.page_number}.",
                            severity="ERROR",
                        )
                    )

                # Rule 3: Registry chunk check if EvidenceStore has chunks registered
                if self.check_registry and s.chunk_id and EvidenceStore.count() > 0:
                    if not EvidenceStore.exists(s.chunk_id):
                        field_errors.append(
                            ValidationIssue(
                                field=fname,
                                issue_type="UNKNOWN_CHUNK",
                                message=f"Cited chunk_id '{s.chunk_id}' not found in EvidenceStore.",
                                severity="ERROR",
                            )
                        )

            # Rule 4: Confidence range
            if fresult.confidence < 0.0 or fresult.confidence > 1.0:
                field_errors.append(
                    ValidationIssue(
                        field=fname,
                        issue_type="INVALID_CONFIDENCE",
                        message=f"Confidence {fresult.confidence} for '{fname}' is outside [0.0, 1.0].",
                        severity="ERROR",
                    )
                )

            # Rule 5: Null values must not claim high confidence
            if fresult.value is None and fresult.confidence > 0.2:
                field_errors.append(
                    ValidationIssue(
                        field=fname,
                        issue_type="INVALID_NULL_CONFIDENCE",
                        message=f"Field '{fname}' is null but reported confidence {fresult.confidence} > 0.2.",
                        severity="WARNING",
                    )
                )

            if any(iss.severity == "ERROR" for iss in field_errors):
                rejected_fields.append(fname)
            else:
                passed_fields.append(fname)

            issues.extend(field_errors)

        is_valid = len(rejected_fields) == 0
        logger.info(
            f"ExtractionValidator: Validated {len(fields)} fields. Passed: {len(passed_fields)}, Rejected: {len(rejected_fields)}"
        )

        return ValidationResult(
            is_valid=is_valid,
            passed_fields=passed_fields,
            rejected_fields=rejected_fields,
            issues=issues,
        )

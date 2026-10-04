"""Data models for field extraction validation and audit."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """Specific error or warning raised during extraction validation."""

    field: str = Field(description="Target field name that failed validation")
    issue_type: str = Field(
        description="Type of validation issue (MISSING_CITATION, UNKNOWN_CHUNK, INVALID_CONFIDENCE, TEXT_UNSUPPORTED, INVALID_FORMAT)"
    )
    message: str = Field(description="Detailed explanation of the validation failure")
    severity: Literal["ERROR", "WARNING"] = Field(
        default="ERROR", description="Severity level of the issue"
    )


class ValidationResult(BaseModel):
    """Aggregated validation result for an extraction run."""

    is_valid: bool = Field(description="True if zero ERROR issues were found")
    passed_fields: List[str] = Field(default_factory=list, description="Fields meeting all validation criteria")
    rejected_fields: List[str] = Field(default_factory=list, description="Fields that failed validation rules")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of all validation issues found")

"""Data models for addendum change tracking and reconciliation."""

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from app.schemas.canonical import Citation


class ChangeType(str, Enum):
    """Classification of changes introduced by an addendum."""

    MODIFICATION = "MODIFICATION"
    CLARIFICATION = "CLARIFICATION"
    ADDITION = "ADDITION"
    REMOVAL = "REMOVAL"
    NO_CHANGE = "NO_CHANGE"


class AddendumChange(BaseModel):
    """Structured record of an amendment or clarification introduced by an addendum."""

    field: str = Field(description="Target field name affected by addendum")
    change_type: ChangeType = Field(description="Type of change")
    original_value: Optional[Any] = Field(default=None, description="Original requirement value before addendum")
    original_sources: List[Citation] = Field(default_factory=list, description="Original source citations")
    new_value: Optional[Any] = Field(default=None, description="Amended value introduced by addendum")
    new_sources: List[Citation] = Field(default_factory=list, description="Addendum source citations")
    addendum_number: int = Field(default=1, description="Sequential addendum number")
    file_name: str = Field(default="", description="Addendum file name")
    rationale: str = Field(default="", description="Explanation of why this field was updated or clarified")

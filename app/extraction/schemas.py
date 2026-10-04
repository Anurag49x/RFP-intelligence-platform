"""Canonical schema models for 20-field structured bid extraction."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.canonical import Citation, FieldResult


class BidOutput(BaseModel):
    """Canonical 20-field structured output model for RFP intelligence extraction."""

    bid_number: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Bid Number",
        title="Bid Number",
    )
    title: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Title",
        title="Title",
    )
    due_date: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Due Date",
        title="Due Date",
    )
    bid_submission_type: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Bid Submission Type",
        title="Bid Submission Type",
    )
    term_of_bid: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Term of Bid",
        title="Term of Bid",
    )
    pre_bid_meeting: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Pre Bid Meeting",
        title="Pre Bid Meeting",
    )
    installation: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Installation",
        title="Installation",
    )
    bid_bond_requirement: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Bid Bond Requirement",
        title="Bid Bond Requirement",
    )
    delivery_date: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Delivery Date",
        title="Delivery Date",
    )
    payment_terms: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Payment Terms",
        title="Payment Terms",
    )
    additional_documentation: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Any Additional Documentation Required",
        title="Any Additional Documentation Required",
    )
    mfg_for_registration: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="MFG for Registration",
        title="MFG for Registration",
    )
    contract_or_cooperative: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Contract or Cooperative to use",
        title="Contract or Cooperative to use",
    )
    model_no: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Model_no",
        title="Model_no",
    )
    part_no: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Part_no",
        title="Part_no",
    )
    product: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Product",
        title="Product",
    )
    contact_info: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="contact_info",
        title="contact_info",
    )
    company_name: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="company_name",
        title="company_name",
    )
    bid_summary: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Bid Summary",
        title="Bid Summary",
    )
    product_specification: FieldResult = Field(
        default_factory=lambda: FieldResult(notes="Not found in documents."),
        serialization_alias="Product Specification",
        title="Product Specification",
    )

    def to_aliased_dict(self) -> Dict[str, Any]:
        """Serialize output mapping snake_case fields to official assignment key names."""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_field_dict(cls, field_results: Dict[str, FieldResult]) -> "BidOutput":
        """Construct BidOutput from a mapping of field names to FieldResults."""
        field_names = cls.model_fields.keys()
        init_kwargs = {}
        for fname in field_names:
            if fname in field_results:
                init_kwargs[fname] = field_results[fname]
        return cls(**init_kwargs)

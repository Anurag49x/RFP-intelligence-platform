"""Field ownership definitions and targeted retrieval query mappings."""

from typing import Dict, List, Set

LOGISTICS_FIELDS: List[str] = [
    "due_date",
    "bid_submission_type",
    "term_of_bid",
    "pre_bid_meeting",
    "installation",
    "delivery_date",
    "payment_terms",
    "contact_info",
]

PRODUCT_FIELDS: List[str] = [
    "mfg_for_registration",
    "model_no",
    "part_no",
    "product",
    "product_specification",
]

LEGAL_FIELDS: List[str] = [
    "bid_bond_requirement",
    "additional_documentation",
    "contract_or_cooperative",
]

ENTITY_FIELDS: List[str] = [
    "bid_number",
    "title",
    "company_name",
    "bid_summary",
]

ALL_20_FIELDS: List[str] = (
    ENTITY_FIELDS + LOGISTICS_FIELDS + PRODUCT_FIELDS + LEGAL_FIELDS
)

FIELD_ALIASES: Dict[str, str] = {
    "bid_number": "Bid Number",
    "title": "Title",
    "due_date": "Due Date",
    "bid_submission_type": "Bid Submission Type",
    "term_of_bid": "Term of Bid",
    "pre_bid_meeting": "Pre Bid Meeting",
    "installation": "Installation",
    "bid_bond_requirement": "Bid Bond Requirement",
    "delivery_date": "Delivery Date",
    "payment_terms": "Payment Terms",
    "additional_documentation": "Any Additional Documentation Required",
    "mfg_for_registration": "MFG for Registration",
    "contract_or_cooperative": "Contract or Cooperative to use",
    "model_no": "Model_no",
    "part_no": "Part_no",
    "product": "Product",
    "contact_info": "contact_info",
    "company_name": "company_name",
    "bid_summary": "Bid Summary",
    "product_specification": "Product Specification",
}

FIELD_TARGETED_QUERIES: Dict[str, List[str]] = {
    "due_date": [
        "bid submission deadline due date closing time",
        "proposal submission due date time",
        "addendum deadline extension due date",
    ],
    "bid_submission_type": [
        "bid submission type electronic portal hard copy delivery email",
        "instructions for bid submission sealed proposal",
    ],
    "term_of_bid": [
        "term of contract proposal length period duration years",
        "contract term effective dates",
    ],
    "pre_bid_meeting": [
        "pre-bid meeting conference schedule date location virtual mandatory",
        "pre-proposal conference date",
    ],
    "installation": [
        "installation required setup deployment services vendor responsibility",
        "inside delivery installation unboxing",
    ],
    "delivery_date": [
        "delivery date schedule timeline days after award receipt of order",
        "delivery address work site required delivery timeframe",
    ],
    "payment_terms": [
        "payment terms invoicing net 30 prompt payment discount",
        "billing instructions payment schedule",
    ],
    "contact_info": [
        "agency point of contact POC phone email buyer procurement contact",
        "contact information questions inquiries",
    ],
    "mfg_for_registration": [
        "manufacturer for registration deal registration OEM authorization",
        "authorized reseller manufacturer partner",
    ],
    "model_no": [
        "laptop computer model number device make proposed model",
        "hardware model specification Latitude",
    ],
    "part_no": [
        "part number SKU dock accessories component part numbers",
        "Thunderbolt dock part number SKU",
    ],
    "product": [
        "product description name hardware device laptops peripherals",
        "computing devices student staff hardware",
    ],
    "product_specification": [
        "product specifications processor RAM storage display operating system",
        "technical specifications minimum requirements hardware",
    ],
    "bid_bond_requirement": [
        "bid bond requirement cashier check surety performance bond percentage",
        "bid security guarantee deposit",
    ],
    "additional_documentation": [
        "additional documentation required affidavits certifications forms disclosures",
        "required submittals compliance guidelines affidavits",
    ],
    "contract_or_cooperative": [
        "contract cooperative purchasing vehicle master contract hardware master contract",
        "interlocal agreement purchasing cooperative contract number",
    ],
    "bid_number": [
        "RFP solicitation bid number sourcing number PORFP number",
        "solicitation identifier bid number",
    ],
    "title": [
        "RFP proposal project title solicitation name",
        "Request for Proposal title description",
    ],
    "company_name": [
        "procuring agency school district government entity department company name",
        "issuing organization Dallas ISD State Treasurer",
    ],
    "bid_summary": [
        "scope of work project overview executive summary procurement purpose",
        "purpose of this RFP proposal summary",
    ],
}

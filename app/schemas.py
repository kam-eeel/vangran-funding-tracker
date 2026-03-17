from typing import TypedDict

RIDING_POSTAL_CODES = (
    "V6H",
    "V6J",
    "V6L",
    "V6M",
    "V6P",
    "V5V",
    "V5W",
    "V5X",
    "V5Y",
    "V5Z"
)

class SourceRecord(TypedDict):
    ref_number: str
    recipient_legal_name: str
    recipient_postal_code: str
    recipient_city: str
    prog_name_en: str
    agreement_value: str
    agreement_start_date: str
    agreement_end_date: str
    owner_org: str
    owner_org_title: str
    recipient_operating_name: str | None
    research_organization_name: str | None
    recipient_country: str | None
    recipient_province: str | None
    federal_riding_name_en: str | None
    federal_riding_number: str | None
    prog_purpose_en: str | None
    agreement_title_en: str | None
    agreement_number: str | None
    foreign_currency_type: str | None
    foreign_currency_value: str | None
    coverage: str | None
    description_en: str | None
    expected_results_en: str | None
    additional_information_en: str | None

OPTIONAL_FIELDS = [
    "recipient_operating_name",
    "research_organization_name",
    "recipient_country",
    "recipient_province",
    "federal_riding_name_en",
    "federal_riding_number",
    "prog_purpose_en",
    "agreement_title_en",
    "agreement_number",
    "foreign_currency_type",
    "foreign_currency_value",
    "coverage",
    "description_en",
    "expected_results_en",
    "additional_information_en",
]
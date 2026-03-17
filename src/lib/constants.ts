export const RIDING_POSTAL_CODES = [
  "V6H", "V6J", "V6L", "V6M", "V6P",
  "V5V", "V5W", "V5X", "V5Y", "V5Z",
] as const;

export const DATA_URL =
  "https://open.canada.ca/data/en/datastore/dump/1d15a62f-5656-49ad-8c88-f40ce689d831";

export const FIELDS = [
  "ref_number",
  "recipient_legal_name",
  "recipient_operating_name",
  "research_organization_name",
  "recipient_country",
  "recipient_province",
  "recipient_city",
  "recipient_postal_code",
  "federal_riding_name_en",
  "federal_riding_number",
  "prog_name_en",
  "prog_purpose_en",
  "agreement_title_en",
  "agreement_number",
  "agreement_value",
  "foreign_currency_type",
  "foreign_currency_value",
  "agreement_start_date",
  "agreement_end_date",
  "coverage",
  "description_en",
  "expected_results_en",
  "additional_information_en",
  "owner_org",
  "owner_org_title",
] as const;

export const OPTIONAL_FIELDS = [
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
] as const;

export type SourceRecord = Record<(typeof FIELDS)[number], string | null>;

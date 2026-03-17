import os
import re
import json
import requests
from pathlib import Path

from app.schemas import RIDING_POSTAL_CODES
from app.schemas import SourceRecord

URL = "https://open.canada.ca/data/en/datastore/dump/1d15a62f-5656-49ad-8c88-f40ce689d831"

FIELDS = [
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
    "owner_org_title"
]

TMP_DIR = "./tmp"

CSV_FILENAME = "dataset_full.csv"
JSON_FILENAME = "vangran_latest.json"

def download_by_postal():
    if not Path(TMP_DIR).exists():
        Path(TMP_DIR).mkdir()
    for fsa in RIDING_POSTAL_CODES:
        params = {
            "q": json.dumps({"recipient_postal_code": f"{fsa}:*"}),
            "plain": "False",
            "language": "simple",
            "sort": "_id asc",
            "filters": "{}",
            "format": "json",
            "fields": ",".join([
                "_id",
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
                "owner_org_title"
            ]),
            "bom": "True",
        }
        try:
            print(f"Downloading data for postal code {fsa}...")

            r = requests.get(URL, stream=True, params=params)
            r.raise_for_status()
            with open(f"{TMP_DIR}/{fsa}.json", "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"Completed download for postal code {fsa}.")
        except requests.HTTPError as e:
            print(f"Download for postal code {fsa} failed. Error: {e}")


def _parse_row(row: list) -> SourceRecord:
    record = {
        field: value for field, value in zip(FIELDS, row)
    }
    return SourceRecord(**record)


def _check_record(record: SourceRecord) -> bool:
    if record["recipient_city"] and not re.match(r"Vancouver", record["recipient_city"], flags=re.IGNORECASE):
        return False
    if record["agreement_end_date"] and int(record["agreement_end_date"].split("-")[0]) < 2021:
        return False
    return True


def collect_records(refresh: bool = False) -> list[SourceRecord]:
    if refresh or not Path(TMP_DIR).exists():
        download_by_postal()
    inputs = os.listdir(TMP_DIR)
    records = []
    for file in inputs:
        with open(f"{TMP_DIR}/{file}", "r", encoding="utf-8-sig") as f:
            js = json.load(f)
            for row in js["records"]:
                record = _parse_row(row)
                if _check_record(record):
                    records.append(record)
    with open(JSON_FILENAME, "w") as f:
        json.dump(records, f, indent=2)
    print(f"Collected {len(records)} records from {len(inputs)} files.")
    return records


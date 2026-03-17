import os
import re
import json
import requests
from pathlib import Path

from app.schemas import RIDING_POSTAL_CODES
from app.schemas import SourceRecord
from app.geocoding import get_coords_from_postal_code, is_in_riding

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
    record["latitude"], record["longitude"] = get_coords_from_postal_code(record["recipient_postal_code"])
    return SourceRecord(**record)


def collect_records(refresh: bool = False) -> list[SourceRecord]:
    if refresh or not Path(TMP_DIR).exists():
        download_by_postal()
    inputs = os.listdir(TMP_DIR)
    records = []
    n_files = len(inputs)
    coord_filter = date_filter = 0
    collected = total_records = 0
    for file in inputs:
        print(f"Parsing records from {file}...")
        with open(f"{TMP_DIR}/{file}", "r", encoding="utf-8-sig") as f:
            js = json.load(f)
            total = len(js["records"])
            total_records += total
            ct = 0
            for row in js["records"]:
                record = _parse_row(row)
                if not is_in_riding(record["latitude"], record["longitude"]):
                    coord_filter += 1
                    # continue # temporary for testing, to actually see everything when i build the map view. just need to build the db first.
                if record["agreement_end_date"] and int(record["agreement_end_date"].split("-")[0]) < 2021:
                    date_filter += 1
                    continue
                records.append(record)
                ct += 1
        print(f"Collected {ct}/{total} records from {file}.")
        collected += ct
    print(f"\nParsing complete! {collected} records collected out of {total_records} total records found in {n_files} files."
          f"\nFilter stats: {coord_filter} (outside riding) + {date_filter} (pre-taleeb) = {coord_filter + date_filter}/{total_records} rejected.")

    with open(JSON_FILENAME, "w") as f:
        json.dump(records, f, indent=2)
    print(f"Collected {len(records)} records from {len(inputs)} files.")
    return records


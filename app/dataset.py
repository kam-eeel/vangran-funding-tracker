from __future__ import annotations

import os
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

def download_by_postal() -> None:
    if not Path(TMP_DIR).exists():
        Path(TMP_DIR).mkdir()
    for fsa in RIDING_POSTAL_CODES:
        dest = Path(TMP_DIR) / f"{fsa}.json"
        if dest.exists():
            print(f"Skipping {fsa} — already downloaded.")
            continue
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


class CollectResult:
    """Result of collect_records including new postal code cache entries."""
    __slots__ = ("records", "new_cache_entries")

    def __init__(self) -> None:
        self.records: list[SourceRecord] = []
        self.new_cache_entries: dict[str, tuple[float, float, bool]] = {}


def collect_records(
    postal_code_cache: dict[str, tuple[float, float, bool]] | None = None,
) -> CollectResult:
    """Download, parse, geocode, and filter records.

    *postal_code_cache* maps postal codes to ``(lat, lng, in_riding)``.
    Cache hits with ``in_riding=False`` skip immediately.  Cache hits with
    ``in_riding=True`` reuse cached coords.  Cache misses geocode via the
    API and populate ``result.new_cache_entries`` for the caller to persist.
    """
    download_by_postal()
    cache = postal_code_cache or {}
    inputs = os.listdir(TMP_DIR)
    result = CollectResult()
    seen: set[tuple[str, str, str]] = set()
    n_files = len(inputs)
    cached_outside = coord_filter = date_filter = duplicates = 0
    collected = total_records = 0
    for file in inputs:
        print(f"Parsing records from {file}...")
        with open(f"{TMP_DIR}/{file}", "r", encoding="utf-8-sig") as f:
            js = json.load(f)
            total = len(js["records"])
            total_records += total
            ct = 0
            for row in js["records"]:
                record: dict[str, str | float | None] = {
                    field: value for field, value in zip(FIELDS, row)
                }
                postal_code = record["recipient_postal_code"]
                assert isinstance(postal_code, str)

                key = (str(record["ref_number"]), postal_code, str(record.get("agreement_start_date", "")))
                if key in seen:
                    duplicates += 1
                    continue
                seen.add(key)

                if postal_code in cache:
                    lat, lng, in_riding_flag = cache[postal_code]
                    if not in_riding_flag:
                        cached_outside += 1
                        continue
                    record["latitude"] = lat
                    record["longitude"] = lng
                else:
                    lat, lng = get_coords_from_postal_code(postal_code)
                    record["latitude"] = lat
                    record["longitude"] = lng
                    in_riding_flag = is_in_riding(lat, lng)
                    cache[postal_code] = (lat, lng, in_riding_flag)
                    result.new_cache_entries[postal_code] = (lat, lng, in_riding_flag)
                    if not in_riding_flag:
                        cached_outside += 1
                        continue

                end_date = record["agreement_end_date"]
                if end_date and isinstance(end_date, str) and int(end_date.split("-")[0]) < 2021:
                    date_filter += 1
                    continue
                result.records.append(SourceRecord(**record))  # type: ignore[arg-type]
                ct += 1
        print(f"Collected {ct}/{total} records from {file}.")
        collected += ct
    rejected_total = cached_outside + coord_filter + date_filter + duplicates
    print(
        f"\nParsing complete! {collected} records collected out of "
        f"{total_records} total records found in {n_files} files."
        f"\nFilter stats: {duplicates} (duplicates) + "
        f"{cached_outside} (cached outside riding) + "
        f"{coord_filter} (outside riding) + {date_filter} (pre-2021) "
        f"= {rejected_total}/{total_records} rejected."
    )

    with open(JSON_FILENAME, "w") as f:
        json.dump(result.records, f, indent=2)
    print(f"Collected {len(result.records)} records from {len(inputs)} files.")
    return result


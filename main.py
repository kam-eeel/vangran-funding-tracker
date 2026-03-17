from __future__ import annotations

import os
import sys
import logging
from datetime import date
from typing import TypedDict

from app.db import Database, RecordRepo
from app.schemas import OPTIONAL_FIELDS, SourceRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _RecordKwargs(TypedDict):
    ref_n: str
    recipient_name: str
    postal_code: str
    program_name: str
    amount: float
    start_date: date
    end_date: date
    department: str
    additional_info: str


def _build_record_kwargs(record: SourceRecord) -> _RecordKwargs:
    """Extract the common fields from a parsed source record into repo kwargs."""
    additional_info = ""
    start: str = record["agreement_start_date"]
    end_raw: str | None = record.get("agreement_end_date")
    end: str = end_raw if end_raw is not None else start
    for field in OPTIONAL_FIELDS:
        val = record.get(field)  # type: ignore[literal-required]
        if val:
            additional_info += f"{field}: {val}\n"
    owner_org: str = record["owner_org"]
    return _RecordKwargs(
        ref_n=record["ref_number"],
        recipient_name=record["recipient_legal_name"],
        postal_code=record["recipient_postal_code"],
        program_name=record["prog_name_en"],
        amount=float(record["agreement_value"]),
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end),
        department=f"{record['owner_org_title']} - {owner_org.upper()}",
        additional_info=additional_info,
    )


def _collect_and_upsert(repo: RecordRepo) -> dict[str, int]:
    """Shared logic for initial ingestion and weekly updates.

    1. Load the postal code cache so known postal codes skip geocoding.
    2. Download/parse/geocode/filter via collect_records.
    3. Persist new postal code cache entries.
    4. Upsert accepted records.
    5. Clean up tmp files on success.
    """
    import shutil
    from app import dataset

    postal_code_cache = repo.load_postal_code_cache()
    result = dataset.collect_records(postal_code_cache=postal_code_cache)

    # Persist new postal code cache entries
    if result.new_cache_entries:
        repo.save_postal_code_cache(result.new_cache_entries)
        logger.info("Cached %d new postal code geocoding results", len(result.new_cache_entries))

    counts = {"new": 0, "updated": 0, "unchanged": 0, "errors": 0}
    for record in result.records:
        kwargs = _build_record_kwargs(record)
        try:
            status = repo.upsert(
                latitude=record["latitude"],
                longitude=record["longitude"],
                **kwargs,
            )
            counts[status] += 1
        except Exception as e:
            ref: str = record["ref_number"]
            counts["errors"] += 1
            logger.error("Upsert failed for %s: %s", ref, e)

    # Clean up intermediate files
    if os.path.isdir(dataset.TMP_DIR):
        shutil.rmtree(dataset.TMP_DIR)
    if os.path.exists(dataset.JSON_FILENAME):
        os.remove(dataset.JSON_FILENAME)

    return counts


def run_ingestion(db: Database | None = None) -> None:
    if db is None:
        db = Database()
        db.create_tables()
    repo = RecordRepo(db)
    _collect_and_upsert(repo)


def run_update(db: Database | None = None) -> None:
    """Re-download the dataset and upsert records. Only geocodes new/changed postal codes."""
    from app.notifications import IngestionEvent, notify

    if db is None:
        db = Database()
        db.create_tables()
    repo = RecordRepo(db)

    logger.info("Starting weekly data update...")
    counts = _collect_and_upsert(repo)

    logger.info(
        "Update complete — %d new, %d updated, %d unchanged, %d errors",
        counts["new"], counts["updated"], counts["unchanged"], counts["errors"],
    )

    notify(IngestionEvent(
        new_records=counts["new"],
        updated_records=counts["updated"],
        unchanged_records=counts["unchanged"],
        errors=[],
    ))


def run_server() -> None:
    import uvicorn
    from sqlalchemy import text
    from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-untyped]
    from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
    from app.web import create_app

    app = create_app()

    with app.state.db.session() as s:
        count = s.execute(text("SELECT COUNT(*) FROM records")).scalar()
    if count == 0:
        print("Database is empty — running initial ingestion...")
        run_ingestion(app.state.db)
        print("Ingestion complete.")

    # Schedule weekly update: every Sunday at 6am
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_update,
        trigger=CronTrigger(day_of_week="sun", hour=6),
        kwargs={"db": app.state.db},
        id="weekly_update",
        name="Weekly data update",
    )
    scheduler.start()
    logger.info("Scheduler started — weekly update scheduled for Sundays at 6am")

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        run_ingestion()
    elif len(sys.argv) > 1 and sys.argv[1] == "update":
        run_update()
    else:
        run_server()

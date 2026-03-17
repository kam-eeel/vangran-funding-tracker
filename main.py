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


def run_ingestion(db: Database | None = None) -> None:
    import shutil
    from app import dataset

    if db is None:
        db = Database()
        db.create_tables()
    repo = RecordRepo(db)

    records = dataset.collect_records(refresh=False)

    for record in records:
        kwargs = _build_record_kwargs(record)
        repo.add(
            latitude=record["latitude"],
            longitude=record["longitude"],
            **kwargs,
        )

    # Clean up intermediate files after DB is populated
    if os.path.isdir(dataset.TMP_DIR):
        shutil.rmtree(dataset.TMP_DIR)
    if os.path.exists(dataset.JSON_FILENAME):
        os.remove(dataset.JSON_FILENAME)


def run_update(db: Database | None = None) -> None:
    """Re-download the dataset and upsert records. Only geocodes new/changed postal codes."""
    import shutil
    from app import dataset
    from app.notifications import IngestionEvent, notify

    if db is None:
        db = Database()
        db.create_tables()
    repo = RecordRepo(db)

    logger.info("Starting weekly data update...")
    records = dataset.collect_records(refresh=True)

    counts = {"new": 0, "updated": 0, "unchanged": 0}
    errors: list[str] = []

    for record in records:
        kwargs = _build_record_kwargs(record)
        try:
            result = repo.upsert(
                latitude=record["latitude"],
                longitude=record["longitude"],
                **kwargs,
            )
            counts[result] += 1
        except Exception as e:
            ref: str = record["ref_number"]
            errors.append(f"{ref}: {e}")
            logger.error("Upsert failed for %s: %s", ref, e)

    # Clean up intermediate files
    if os.path.isdir(dataset.TMP_DIR):
        shutil.rmtree(dataset.TMP_DIR)
    if os.path.exists(dataset.JSON_FILENAME):
        os.remove(dataset.JSON_FILENAME)

    logger.info(
        "Update complete — %d new, %d updated, %d unchanged, %d errors",
        counts["new"], counts["updated"], counts["unchanged"], len(errors),
    )

    notify(IngestionEvent(
        new_records=counts["new"],
        updated_records=counts["updated"],
        unchanged_records=counts["unchanged"],
        errors=errors,
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

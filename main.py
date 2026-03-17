import os
import sys
from datetime import date

from app.db import Database, RecordRepo
from app.schemas import OPTIONAL_FIELDS


def run_ingestion(db: Database = None):
    import shutil
    from app import dataset

    if db is None:
        db = Database()
        db.create_tables()
    repo = RecordRepo(db)

    records = dataset.collect_records(refresh=False)

    for record in records:
        additional_info = ""
        start = record.get("agreement_start_date")
        end = record.get("agreement_end_date") if record.get("agreement_end_date") is not None else start
        for field in OPTIONAL_FIELDS:
            if record.get(field):
                additional_info += f"{field}: {record.get(field)}\n"
        repo.add(
            ref_n=record.get("ref_number"),
            recipient_name=record.get("recipient_legal_name"),
            postal_code=record.get("recipient_postal_code"),
            program_name=record.get("prog_name_en"),
            amount=float(record.get("agreement_value")),
            start_date=date.fromisoformat(start),
            end_date=date.fromisoformat(end),
            department=f"{record.get('owner_org_title')} - {record.get('owner_org').upper()}",
            additional_info=additional_info,
        )

    # Clean up intermediate files after DB is populated
    if os.path.isdir(dataset.TMP_DIR):
        shutil.rmtree(dataset.TMP_DIR)
    if os.path.exists(dataset.JSON_FILENAME):
        os.remove(dataset.JSON_FILENAME)


def run_server():
    import uvicorn
    from sqlalchemy import text
    from app.web import create_app

    app = create_app()

    with app.state.db.session() as s:
        count = s.execute(text("SELECT COUNT(*) FROM records")).scalar()
    if count == 0:
        print("Database is empty — running initial ingestion...")
        run_ingestion(app.state.db)
        print("Ingestion complete.")

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        run_ingestion()
    else:
        run_server()

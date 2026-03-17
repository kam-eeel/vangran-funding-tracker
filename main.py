from datetime import date
from app import dataset
from app.db import Database, RecordRepo
from app.schemas import OPTIONAL_FIELDS

db = Database()
db.create_tables()
repo = RecordRepo(db)

records = dataset.collect_records(refresh=False)

for record in records:
    additional_info = ""
    start = record.get("agreement_start_date")
    end = record.get("agreement_end_date") if record.get("agreement_end_date") != None else start
    for field in OPTIONAL_FIELDS:
        if record.get(field):
            additional_info += f"{field}: {record.get(field)}\n"
    repo.add(
        ref_n=record.get("ref_number"),
        recipient_name=record.get("recipient_legal_name"),
        postal_code=record.get("recipient_postal_code"),
        program_name=record.get("prog_name_en"),
        amount=float(record.get("agreement_value")),
        start_date=date.strptime(start, "%Y-%m-%d"),
        end_date=date.strptime(end, "%Y-%m-%d"),
        department=f"{record.get("owner_org_title")} - {record.get("owner_org").upper()}",
        additional_info=additional_info
    )
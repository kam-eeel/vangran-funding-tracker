"""One-off script: re-geocode the 7 postal codes that had bad coordinates.

Usage:
    python -m scripts.fix_bad_coords          # dry-run (prints changes)
    python -m scripts.fix_bad_coords --apply  # commit changes to DB
"""
import sys
from sqlalchemy import select

from app.db import Database
from app.models import Record
from app.geocoding import get_coords_from_postal_code

BAD_POSTAL_CODES = [
    "V6P6M7", "V5Z 1E0", "V5Z 1L8", "V5Z4M4",
    "V6P5X8", "V5X2T9", "V5Y1C4",
]

def main():
    apply = "--apply" in sys.argv
    db = Database()
    updated = nulled = 0

    with db.session() as s:
        for pc in BAD_POSTAL_CODES:
            # Find all records with this postal code (case-insensitive, ignore spaces)
            normalized = pc.replace(" ", "").upper()
            rows = s.execute(
                select(Record).where(
                    Record.postal_code.ilike(f"%{normalized[:3]}%{normalized[3:]}%")
                )
            ).scalars().all()

            if not rows:
                print(f"  {pc}: no records found in DB, skipping")
                continue

            lat, lng = get_coords_from_postal_code(pc)

            for r in rows:
                old = (float(r.latitude) if r.latitude else None,
                       float(r.longitude) if r.longitude else None)
                if lat is None:
                    print(f"  {pc} (id={r.id}): {old} -> NULL (no FSA match)")
                    nulled += 1
                else:
                    print(f"  {pc} (id={r.id}): {old} -> ({lat}, {lng})")
                    updated += 1

                if apply:
                    r.latitude = lat
                    r.longitude = lng

        if not apply:
            print(f"\nDry run: {updated} would update, {nulled} would null. Pass --apply to commit.")
            s.rollback()
        else:
            print(f"\nApplied: {updated} updated, {nulled} nulled.")


if __name__ == "__main__":
    main()

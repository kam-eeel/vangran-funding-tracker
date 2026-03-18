from __future__ import annotations

from datetime import date, datetime
from math import ceil
from typing import Any
from collections.abc import Generator
from sqlalchemy import create_engine, select, func, event, cast, String, case, text
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager

from app.models import Base, Record, PostalCodeCache

import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, url: str | None = None) -> None:
        if url is None:
            db_path = os.environ.get("DB_PATH", "vangran.db")
            url = f"sqlite:///{db_path}"
        self.engine = create_engine(url)
        @event.listens_for(self.engine, "connect")
        def pragmas(dbapi_conn: Any, _: Any) -> None:
            c = dbapi_conn.cursor()
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            c.close()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        s = self.SessionLocal()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

class RecordRepo:
    def __init__(self, db: Database):
        self.db = db

    # Fields compared during upsert to detect changes
    UPSERT_FIELDS = (
        "recipient_name", "postal_code", "program_name", "amount",
        "start_date", "end_date", "department", "additional_info",
    )

    def load_postal_code_cache(self) -> dict[str, tuple[float, float, bool]]:
        """Load all cached geocoding results keyed by postal code."""
        with self.db.session() as s:
            rows = s.execute(
                select(
                    PostalCodeCache.postal_code,
                    PostalCodeCache.latitude,
                    PostalCodeCache.longitude,
                    PostalCodeCache.in_riding,
                )
            ).all()
            return {r[0]: (float(r[1]), float(r[2]), bool(r[3])) for r in rows}

    def save_postal_code_cache(self, entries: dict[str, tuple[float, float, bool]]) -> None:
        """Persist new postal code geocoding results, skipping existing."""
        with self.db.session() as s:
            for postal_code, (lat, lng, in_riding) in entries.items():
                exists = s.execute(
                    select(PostalCodeCache.id).where(
                        PostalCodeCache.postal_code == postal_code,
                    )
                ).scalar_one_or_none()
                if exists is None:
                    s.add(PostalCodeCache(
                        postal_code=postal_code,
                        latitude=lat,
                        longitude=lng,
                        in_riding=in_riding,
                    ))

    def upsert(
        self,
        ref_n: str,
        recipient_name: str,
        postal_code: str,
        latitude: float,
        longitude: float,
        program_name: str,
        amount: float,
        start_date: date,
        end_date: date,
        department: str,
        additional_info: str,
    ) -> str:
        """Upsert a pre-geocoded, pre-filtered record. Returns 'new', 'updated', or 'unchanged'."""
        incoming = {
            "recipient_name": recipient_name,
            "postal_code": postal_code,
            "program_name": program_name,
            "amount": amount,
            "start_date": start_date,
            "end_date": end_date,
            "department": department,
            "additional_info": additional_info,
        }

        with self.db.session() as s:
            existing = s.execute(
                select(Record).where(
                    Record.ref_n == ref_n,
                    Record.postal_code == postal_code,
                    Record.start_date == start_date,
                )
            ).scalars().first()

            if existing is None:
                rcd = Record(
                    ref_n=ref_n, latitude=latitude, longitude=longitude,
                    **incoming,
                )
                s.add(rcd)
                return "new"

            # Compare fields (postal_code & start_date are lookup keys, can't change)
            changed_fields: dict[str, Any] = {}
            for field in self.UPSERT_FIELDS:
                if field in ("postal_code", "start_date"):
                    continue
                old_val: Any = getattr(existing, field)
                new_val: Any = incoming[field]
                if field == "amount":
                    old_val = float(old_val) if old_val is not None else None
                    new_val = float(new_val) if new_val is not None else None
                if old_val != new_val:
                    changed_fields[field] = new_val

            if not changed_fields:
                return "unchanged"

            for field, value in changed_fields.items():
                setattr(existing, field, value)

            existing.last_updated = datetime.now()
            return "updated"

    def deduplicate_records(self) -> int:
        """Remove duplicate rows, keeping the lowest id per (ref_n, postal_code, start_date)."""
        with self.db.session() as s:
            result = s.execute(text(
                "DELETE FROM records WHERE id NOT IN ("
                "  SELECT MIN(id) FROM records GROUP BY ref_n, postal_code, start_date"
                ")"
            ))
            return result.rowcount  # type: ignore[union-attr]

    def get(self, _id: int) -> Record | None:
        with self.db.session() as s:
            return s.get(Record, _id)

    def dashboard(self) -> list[Any]:
        with self.db.session() as s:
            stmt = (
                select(
                    Record.ref_n,
                    Record.recipient_name,
                    Record.postal_code,
                    Record.program_name,
                    Record.amount,
                    Record.start_date,
                    Record.end_date,
                    Record.department,
                    Record.additional_info,
                )
            )
            return list(s.execute(stmt).all())


class RecordQueryService:
    """Read-only query service for the web UI. All values are dynamically
    computed from the database — nothing is hardcoded."""

    SORTABLE_COLUMNS = {
        "ref_n": Record.ref_n,
        "recipient_name": Record.recipient_name,
        "postal_code": Record.postal_code,
        "program_name": Record.program_name,
        "amount": Record.amount,
        "start_date": Record.start_date,
        "end_date": Record.end_date,
        "department": Record.department,
    }

    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _short_department(name: str) -> str:
        """Extract the English department name before the '|' separator."""
        if "|" in name:
            return name.split("|")[0].strip()
        if " - " in name:
            return name.rsplit(" - ", 1)[0].strip()
        return name

    def get_kpis(self) -> dict:
        today = date.today()
        with self.db.session() as s:
            row = s.execute(
                select(
                    func.coalesce(func.sum(Record.amount), 0).label("total_funding"),
                    func.count(Record.id).label("record_count"),
                    func.coalesce(func.avg(Record.amount), 0).label("avg_amount"),
                    func.count(func.distinct(Record.program_name)).label("program_count"),
                    func.count(func.distinct(Record.department)).label("department_count"),
                    func.coalesce(func.sum(case(
                        (Record.end_date < today, Record.amount),
                        else_=0,
                    )), 0).label("funding_delivered"),
                    func.coalesce(func.sum(case(
                        (Record.end_date >= today, Record.amount),
                        else_=0,
                    )), 0).label("funding_committed"),
                )
            ).one()
            return {
                "total_funding": float(row.total_funding),
                "record_count": int(row.record_count),
                "avg_amount": float(row.avg_amount),
                "program_count": int(row.program_count),
                "department_count": int(row.department_count),
                "funding_delivered": float(row.funding_delivered),
                "funding_committed": float(row.funding_committed),
            }

    def _apply_filters(self, stmt, filters: dict):
        """Apply common filter params to a SELECT statement."""
        if filters.get("department"):
            stmt = stmt.where(Record.department == filters["department"])
        if filters.get("program"):
            stmt = stmt.where(Record.program_name == filters["program"])
        if filters.get("postal_code"):
            stmt = stmt.where(func.upper(Record.postal_code).like(f"{filters['postal_code'].upper()}%"))
        if filters.get("start_date_from"):
            stmt = stmt.where(Record.start_date >= filters["start_date_from"])
        if filters.get("start_date_to"):
            stmt = stmt.where(Record.start_date <= filters["start_date_to"])
        if filters.get("end_date_from"):
            stmt = stmt.where(Record.end_date >= filters["end_date_from"])
        if filters.get("end_date_to"):
            stmt = stmt.where(Record.end_date <= filters["end_date_to"])
        if filters.get("amount_min") is not None:
            try:
                stmt = stmt.where(Record.amount >= float(filters["amount_min"]))
            except (ValueError, TypeError):
                pass
        if filters.get("amount_max") is not None:
            try:
                stmt = stmt.where(Record.amount <= float(filters["amount_max"]))
            except (ValueError, TypeError):
                pass
        if filters.get("search"):
            term = f"%{filters['search']}%"
            stmt = stmt.where(
                Record.recipient_name.ilike(term)
                | Record.program_name.ilike(term)
                | Record.ref_n.ilike(term)
            )
        return stmt

    def get_funding_by_department(self, limit: int = 10, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        with self.db.session() as s:
            stmt = select(
                Record.department.label("name"),
                func.sum(Record.amount).label("total"),
                func.count(Record.id).label("count"),
            ).group_by(Record.department).order_by(func.sum(Record.amount).desc())
            stmt = self._apply_filters(stmt, filters)
            if limit:
                stmt = stmt.limit(limit)
            rows = s.execute(stmt).all()
            return [
                {
                    "name": r.name,
                    "short_name": self._short_department(r.name),
                    "total": float(r.total),
                    "count": int(r.count),  # pyright: ignore[reportArgumentType]
                }
                for r in rows
            ]

    def get_funding_by_program(self, limit: int = 10, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        with self.db.session() as s:
            stmt = select(
                Record.program_name.label("name"),
                func.sum(Record.amount).label("total"),
                func.count(Record.id).label("count"),
            ).group_by(Record.program_name).order_by(func.sum(Record.amount).desc())
            stmt = self._apply_filters(stmt, filters)
            if limit:
                stmt = stmt.limit(limit)
            rows = s.execute(stmt).all()

            # Compute "Other" only when using a limit
            if limit:
                total_stmt = select(func.coalesce(func.sum(Record.amount), 0))
                total_stmt = self._apply_filters(total_stmt, filters)
                total_all_val = float(str(s.execute(total_stmt).scalar() or 0))
                top_total = sum(float(r.total) for r in rows)
                other_total = total_all_val - top_total

                count_stmt = select(func.count(Record.id))
                count_stmt = self._apply_filters(count_stmt, filters)
                all_count_val = int(s.execute(count_stmt).scalar() or 0)
                top_count = sum(int(getattr(r, "count")) for r in rows)
                other_count = all_count_val - top_count
            else:
                other_total = 0
                other_count = 0

            result = [
                {"name": r.name, "total": float(r.total), "count": int(r.count)}  # pyright: ignore[reportArgumentType]
                for r in rows
            ]
            if other_total > 0:
                result.append({"name": "Other", "total": other_total, "count": other_count})
            return result

    def get_funding_by_postal_code(self, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        fsa = func.upper(func.substr(Record.postal_code, 1, 3)).label("fsa")
        with self.db.session() as s:
            stmt = select(
                fsa,
                func.sum(Record.amount).label("total"),
                func.count(Record.id).label("count"),
            ).group_by(fsa).order_by(func.sum(Record.amount).desc())
            stmt = self._apply_filters(stmt, filters)
            rows = s.execute(stmt).all()
            return [
                {"fsa": r.fsa, "total": float(r.total), "count": int(getattr(r, "count"))}
                for r in rows
            ]

    def get_funding_timeline(self, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        year_expr = func.substr(cast(Record.start_date, String), 1, 4).label("year")
        with self.db.session() as s:
            stmt = select(
                year_expr,
                func.sum(Record.amount).label("total"),
                func.count(Record.id).label("count"),
            ).group_by(year_expr).order_by(year_expr)
            stmt = self._apply_filters(stmt, filters)
            rows = s.execute(stmt).all()
            return [
                {"year": r.year, "total": float(r.total), "count": int(r.count)}  # pyright: ignore[reportArgumentType]
                for r in rows
            ]

    def get_filter_options(self) -> dict:
        with self.db.session() as s:
            departments = [
                r[0] for r in s.execute(
                    select(Record.department).distinct().order_by(Record.department)
                ).all()
            ]
            programs = [
                r[0] for r in s.execute(
                    select(Record.program_name).distinct().order_by(Record.program_name)
                ).all() if r[0]
            ]
            fsa = func.upper(func.substr(Record.postal_code, 1, 3))
            postal_codes = [
                r[0] for r in s.execute(
                    select(fsa.label("fsa")).distinct().order_by(fsa)
                ).all()
            ]
            date_range = s.execute(
                select(
                    func.min(Record.start_date),
                    func.max(Record.start_date),
                )
            ).one()
            amount_range = s.execute(
                select(
                    func.min(Record.amount),
                    func.max(Record.amount),
                )
            ).one()
            return {
                "departments": departments,
                "programs": programs,
                "postal_codes": postal_codes,
                "min_date": str(date_range[0]) if date_range[0] else "",
                "max_date": str(date_range[1]) if date_range[1] else "",
                "min_amount": float(amount_range[0]) if amount_range[0] else 0,
                "max_amount": float(amount_range[1]) if amount_range[1] else 0,
            }

    def get_last_updated(self) -> str | None:
        with self.db.session() as s:
            result = s.execute(select(func.max(Record.last_updated))).scalar()
            return result.strftime("%-d %B %Y") if result else None

    def get_record_by_id(self, record_id: int) -> dict | None:
        with self.db.session() as s:
            r = s.get(Record, record_id)
            if r is None:
                return None
            return {
                "id": r.id,
                "ref_n": r.ref_n,
                "recipient_name": r.recipient_name,
                "postal_code": r.postal_code,
                "program_name": r.program_name,
                "amount": float(str(r.amount)) if r.amount is not None else None,
                "start_date": str(r.start_date) if r.start_date else None,
                "end_date": str(r.end_date) if r.end_date else None,
                "department": r.department,
                "additional_info": r.additional_info or "",
            }

    def get_map_points(self, filters: dict | None = None) -> list[dict]:
        """Return all geocoded records as lightweight map points."""
        filters = filters or {}
        with self.db.session() as s:
            stmt = select(
                Record.id,
                Record.recipient_name,
                Record.amount,
                Record.postal_code,
                Record.department,
                Record.latitude,
                Record.longitude,
            ).where(
                Record.latitude.is_not(None),
                Record.longitude.is_not(None),
            )
            stmt = self._apply_filters(stmt, filters)
            rows = s.execute(stmt).all()
            return [
                {
                    "id": r.id,
                    "lat": float(r.latitude),
                    "lng": float(r.longitude),
                    "recipient_name": r.recipient_name,
                    "amount": float(str(r.amount)) if r.amount is not None else None,
                    "postal_code": r.postal_code,
                    "department": r.department,
                }
                for r in rows
            ]

    def search_records(
        self,
        filters: dict | None = None,
        sort: str = "amount",
        direction: str = "desc",
        page: int = 1,
        per_page: int = 50,
    ) -> dict:
        filters = filters or {}
        stmt = select(Record)

        # Apply filters dynamically
        if filters.get("department"):
            stmt = stmt.where(Record.department == filters["department"])
        if filters.get("program"):
            stmt = stmt.where(Record.program_name == filters["program"])
        if filters.get("postal_code"):
            stmt = stmt.where(func.upper(Record.postal_code).like(f"{filters['postal_code'].upper()}%"))
        if filters.get("start_date_from"):
            stmt = stmt.where(Record.start_date >= filters["start_date_from"])
        if filters.get("start_date_to"):
            stmt = stmt.where(Record.start_date <= filters["start_date_to"])
        if filters.get("end_date_from"):
            stmt = stmt.where(Record.end_date >= filters["end_date_from"])
        if filters.get("end_date_to"):
            stmt = stmt.where(Record.end_date <= filters["end_date_to"])
        if filters.get("amount_min") is not None:
            try:
                stmt = stmt.where(Record.amount >= float(filters["amount_min"]))
            except (ValueError, TypeError):
                pass
        if filters.get("amount_max") is not None:
            try:
                stmt = stmt.where(Record.amount <= float(filters["amount_max"]))
            except (ValueError, TypeError):
                pass
        if filters.get("search"):
            term = f"%{filters['search']}%"
            stmt = stmt.where(
                Record.recipient_name.ilike(term)
                | Record.program_name.ilike(term)
                | Record.ref_n.ilike(term)
            )

        # Sort — validated against allowlist
        sort_col = self.SORTABLE_COLUMNS.get(sort, Record.amount)
        if direction == "asc":
            stmt = stmt.order_by(sort_col.asc())
        else:
            stmt = stmt.order_by(sort_col.desc())

        with self.db.session() as s:
            # Count total matching records (same WHERE, no LIMIT)
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = s.execute(count_stmt).scalar() or 0

            # Paginate
            pages = max(1, ceil(total / per_page))
            page = max(1, min(page, pages))
            offset = (page - 1) * per_page
            rows = s.execute(stmt.limit(per_page).offset(offset)).scalars().all()

            # Convert to dicts while session is open to avoid DetachedInstanceError
            records = [
                {
                    "id": r.id,
                    "ref_n": r.ref_n,
                    "recipient_name": r.recipient_name,
                    "postal_code": r.postal_code,
                    "program_name": r.program_name,
                    "amount": float(str(r.amount)) if r.amount is not None else None,
                    "start_date": str(r.start_date) if r.start_date else None,
                    "end_date": str(r.end_date) if r.end_date else None,
                    "department": r.department,
                }
                for r in rows
            ]

            return {
                "records": records,
                "total": total,
                "page": page,
                "pages": pages,
                "per_page": per_page,
            }
from datetime import date
from math import ceil
from sqlalchemy import create_engine, select, func, event, cast, String, case
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from contextlib import contextmanager

from app.models import Base, Record

import os

class Database:
    def __init__(self, url: str = None):
        if url is None:
            db_path = os.environ.get("DB_PATH", "vangran.db")
            url = f"sqlite:///{db_path}"
        self.engine = create_engine(url)
        @event.listens_for(self.engine, "connect")
        def pragmas(dbapi_conn, _):
            c = dbapi_conn.cursor()
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            c.close()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self):
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

    def add(
        self,
        ref_n: str,
        recipient_name: str,
        postal_code: str,
        program_name: str,
        amount: float,
        start_date: date,
        end_date: date,
        department: str,
        additional_info: str
    ):
        with self.db.session() as s:
            rcd = Record(
                ref_n=ref_n,
                recipient_name=recipient_name,
                postal_code=postal_code,
                program_name=program_name,
                amount=amount,
                start_date=start_date,
                end_date=end_date,
                department=department,
                additional_info=additional_info
            )
            s.add(rcd)
            s.flush()
            return rcd.ref_n

    def get(self, _id: int):
        with self.db.session() as s:
            return s.get(Record, _id)

    def dashboard(self):
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
            return s.execute(stmt).all()


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

    def get_map_records(self, filters: dict | None = None) -> list[dict]:
        """Return lightweight records for map plotting (id, name, postal_code, amount)."""
        filters = filters or {}
        with self.db.session() as s:
            stmt = select(
                Record.id,
                Record.recipient_name,
                Record.postal_code,
                Record.amount,
            )
            stmt = self._apply_filters(stmt, filters)
            rows = s.execute(stmt).all()
            return [
                {
                    "id": row.id,
                    "recipient_name": row.recipient_name,
                    "postal_code": row.postal_code,
                    "amount": float(str(row.amount)) if row.amount is not None else 0,
                }
                for row in rows
            ]

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
                    "count": int(r.count),
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
                {"name": r.name, "total": float(r.total), "count": int(r.count)}
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
                {"year": r.year, "total": float(r.total), "count": int(r.count)}
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
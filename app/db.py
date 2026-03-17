from datetime import date
from sqlalchemy import create_engine, select, func, event
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from contextlib import contextmanager

from app.models import Base, Record

class Database:
    def __init__(self, url: str = "sqlite:///vangran.db"):
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
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Index, String, Text, Numeric, Date, UniqueConstraint, func
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column
)

# Base class — all models inherit from this
class Base(DeclarativeBase):
    pass

class Record(Base):
    __tablename__ = "records"
    __table_args__ = (
        UniqueConstraint("ref_n", "postal_code", "start_date", name="uq_record_identity"),
        Index("ix_records_department", "department"),
        Index("ix_records_program", "program_name"),
        Index("ix_records_postal", "postal_code"),
        Index("ix_records_amount", "amount"),
        Index("ix_records_start_date", "start_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ref_n: Mapped[str] = mapped_column(String)
    recipient_name: Mapped[str] = mapped_column(Text)
    postal_code: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Numeric)
    longitude: Mapped[float] = mapped_column(Numeric)
    program_name: Mapped[Optional[str]] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Numeric)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    department: Mapped[str] = mapped_column(Text)
    additional_info: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<Record(ref={self.ref_n!r},"\
               f"recipient={self.recipient_name},"\
               f"amount={self.amount},"\
               f"start_date={self.start_date},"\
               f"end_date={self.end_date},"\
               f"department={self.department!r})>"


class RejectedRecord(Base):
    """Records that were rejected during ingestion (e.g. outside riding).

    Checked before any geocoding or upsert work to avoid redundant API calls.
    """
    __tablename__ = "rejected_records"
    __table_args__ = (
        UniqueConstraint("ref_n", "postal_code", "start_date", name="uq_rejected_identity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ref_n: Mapped[str] = mapped_column(String)
    postal_code: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
from datetime import date, datetime
from typing import Optional
from sqlalchemy import ForeignKey, Float, Index, Text, Numeric, Date, func
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)

# Base class — all models inherit from this
class Base(DeclarativeBase):
    pass

class Record(Base):
    __tablename__ = "records"
    __table_args__ = (
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
    program_name: Mapped[Optional[str]] = mapped_column(Text)
    amount: Mapped[Numeric] = mapped_column(Numeric)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    department: Mapped[str] = mapped_column(Text)
    additional_info: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(server_default=func.now())

    location: Mapped[Optional["RecordLocation"]] = relationship(back_populates="record", uselist=False)

    def __repr__(self):
        return f"<Record(ref={self.ref_n!r},"\
               f"recipient={self.recipient_name},"\
               f"amount={self.amount},"\
               f"start_date={self.start_date},"\
               f"end_date={self.end_date},"\
               f"department={self.department!r})>"


class RecordLocation(Base):
    __tablename__ = "record_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), unique=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    record: Mapped["Record"] = relationship(back_populates="location")
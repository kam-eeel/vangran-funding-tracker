from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Text, Numeric, Date, func
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column
)

# Base class — all models inherit from this
class Base(DeclarativeBase):
    pass

class Record(Base):
    __tablename__ = "records"

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

    def __repr__(self):
        return f"<Record(ref={self.ref_n!r},"\
               f"recipient={self.recipient_name},"\
               f"amount={self.amount},"\
               f"start_date={self.start_date},"\
               f"end_date={self.end_date},"\
               f"department={self.department!r})>"
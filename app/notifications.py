from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class IngestionEvent:
    """Data class for ingestion results."""
    new_records: int
    updated_records: int
    unchanged_records: int
    errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


def notify(event: IngestionEvent) -> None:
    """Stub for future notification dispatch. Does nothing yet."""
    pass

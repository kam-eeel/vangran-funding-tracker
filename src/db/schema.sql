CREATE TABLE IF NOT EXISTS records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_n TEXT NOT NULL,
  recipient_name TEXT NOT NULL,
  postal_code TEXT NOT NULL,
  program_name TEXT,
  amount REAL NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT,
  department TEXT NOT NULL,
  additional_info TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_updated TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_records_ref_n ON records(ref_n);
CREATE INDEX IF NOT EXISTS ix_records_department ON records(department);
CREATE INDEX IF NOT EXISTS ix_records_program ON records(program_name);
CREATE INDEX IF NOT EXISTS ix_records_postal ON records(postal_code);
CREATE INDEX IF NOT EXISTS ix_records_amount ON records(amount);
CREATE INDEX IF NOT EXISTS ix_records_start_date ON records(start_date);

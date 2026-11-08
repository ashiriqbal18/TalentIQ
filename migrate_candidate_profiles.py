
import sqlite3
from pathlib import Path
from datetime import datetime

from config import DATABASE_DIR

database_path = DATABASE_DIR / "talentiq.db"

if not database_path.exists():
    raise FileNotFoundError(
        f"Database not found: {database_path}"
    )

# Create a safe backup first
backup_path = DATABASE_DIR / (
    "talentiq_profile_backup_"
    + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    + ".db"
)

with sqlite3.connect(database_path) as source:
    with sqlite3.connect(backup_path) as backup:
        source.backup(backup)

print("Backup created:", backup_path)

# Add the new column if missing
with sqlite3.connect(database_path) as connection:

    connection.execute("PRAGMA foreign_keys = ON")

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table'"
        )
    }

    if not {"users", "candidates"}.issubset(tables):
        raise RuntimeError(
            "Required users or candidates table missing."
        )

    existing_columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(candidates)"
        )
    }

    if "user_id" not in existing_columns:

        connection.execute(
            "ALTER TABLE candidates "
            "ADD COLUMN user_id INTEGER REFERENCES users(id)"
        )

        print("Added column: candidates.user_id")

    else:
        print("Column already exists: user_id")

    # Enforce one candidate profile per account
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "uq_candidates_user_id "
        "ON candidates(user_id)"
    )

    connection.commit()

print("Candidate profile migration completed!")

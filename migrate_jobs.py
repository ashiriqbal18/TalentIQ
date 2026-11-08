
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATABASE_DIR


database_path = DATABASE_DIR / "talentiq.db"

if not database_path.is_file():
    raise FileNotFoundError(
        f"Database not found: {database_path}"
    )

# Create a database backup before changes
backup_path = DATABASE_DIR / (
    "talentiq_backup_"
    + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    + ".db"
)

with sqlite3.connect(database_path) as source:
    with sqlite3.connect(backup_path) as backup:
        source.backup(backup)

print("Backup created:", backup_path)

new_columns = {
    "company": "VARCHAR(150)",
    "location": "VARCHAR(150)",
    "work_type": "VARCHAR(30)",
    "salary_min": "INTEGER",
    "salary_max": "INTEGER",
    "posted_by": "INTEGER REFERENCES users(id)"
}

with sqlite3.connect(database_path) as connection:

    existing_tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table'"
        )
    }

    if "jobs" not in existing_tables:
        raise RuntimeError("jobs table does not exist")

    if "users" not in existing_tables:
        raise RuntimeError("users table does not exist")

    existing_columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(jobs)"
        )
    }

    for column, column_type in new_columns.items():

        if column not in existing_columns:

            connection.execute(
                f"ALTER TABLE jobs "
                f"ADD COLUMN {column} {column_type}"
            )

            print("Added column:", column)

        else:
            print("Already exists:", column)

    connection.commit()

print("Job database migration completed!")

"""SQLite engine and session factory used by the local application."""

import os
from pathlib import Path

from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import sessionmaker

DATABASE_PATH = Path(os.environ.get("SKILLPULSE_DATABASE_PATH", Path(__file__).resolve().parents[2] / "skillpulse.db"))
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = URL.create("sqlite", database=str(DATABASE_PATH))

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(connection, _connection_record) -> None:
    """SQLite leaves foreign-key enforcement off unless enabled per connection."""
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

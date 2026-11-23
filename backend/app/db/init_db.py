"""Create the initial SQLite tables. Run from backend with `python -m app.db.init_db`."""

from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401 - importing registers model tables with Base


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    print(f"Initialized SQLite database at {engine.url.database}")


if __name__ == "__main__":
    initialize_database()

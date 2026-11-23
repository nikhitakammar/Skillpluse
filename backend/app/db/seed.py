"""Load generated CSV records into SQLite. Run from backend with `python -m app.db.seed`."""

from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app import models

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic"


def as_date(value):
    if pd.isna(value):
        return None
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def records(filename: str) -> list[dict]:
    return pd.read_csv(DATA_DIR / filename).to_dict(orient="records")


def load_rows(session: Session, model, filename: str, date_columns=(), bool_columns=()) -> None:
    for row in records(filename):
        for column in date_columns:
            row[column] = as_date(row[column])
        for column in bool_columns:
            row[column] = bool(row[column])
        session.merge(model(**row))


def seed_database() -> None:
    required_files = [
        "batches.csv", "students.csv", "assessments.csv", "assessment_results.csv",
        "attendance_records.csv", "assignments.csv", "assignment_submissions.csv", "support_outcomes.csv",
    ]
    missing = [filename for filename in required_files if not (DATA_DIR / filename).exists()]
    if missing:
        raise FileNotFoundError(
            f"Synthetic CSVs are missing: {', '.join(missing)}. "
            "Generate them first with `python -m app.db.generate_synthetic_data`."
        )

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        load_rows(session, models.Batch, "batches.csv", date_columns=("start_date", "end_date"))
        session.flush()
        load_rows(session, models.Student, "students.csv", date_columns=("enrollment_date",), bool_columns=("is_active",))
        session.flush()
        load_rows(session, models.Assessment, "assessments.csv", date_columns=("assessment_date",))
        session.flush()
        load_rows(session, models.AssessmentResult, "assessment_results.csv")
        session.flush()
        load_rows(session, models.AttendanceRecord, "attendance_records.csv", date_columns=("session_date",))
        session.flush()
        load_rows(session, models.Assignment, "assignments.csv", date_columns=("assigned_date", "due_date"))
        session.flush()
        load_rows(session, models.AssignmentSubmission, "assignment_submissions.csv", date_columns=("submitted_at",))
        session.flush()
        load_rows(session, models.SupportOutcome, "support_outcomes.csv", date_columns=("snapshot_date", "outcome_date"), bool_columns=("needs_support",))
        session.commit()
        print(f"Seeded {session.query(models.Student).count()} synthetic students into {engine.url.database}")


if __name__ == "__main__":
    seed_database()

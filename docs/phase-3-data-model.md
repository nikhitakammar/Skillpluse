# Phase 3: Data model and synthetic dataset

## Relational design

The SQLite database stores one kind of record per table. Foreign keys preserve the links between batches, learners, assessments and activity records. Unique constraints prevent duplicate assessment results, attendance sessions or assignment submissions for the same learner.

| Table | Purpose |
| --- | --- |
| `batches` | Training cohort, programme, dates, status and data origin. |
| `students` | Fictional learner identity and batch membership. |
| `assessments` | Assessment date, skill area and maximum score. |
| `assessment_results` | A learner's score for an assessment. |
| `attendance_records` | One present, late or absent record per learner and session date. |
| `assignments` | Assignment instructions, skill area and due date. |
| `assignment_submissions` | Learner submission date and optional score; no date means not submitted. |
| `support_outcomes` | A synthetic follow-up label recorded after a historical snapshot. |

`model_snapshots.csv` is a purpose-built training table, not a replacement for the normalized operational tables. Each row summarizes historical scores, attendance and assignment completion as of `snapshot_date`; its synthetic support label and `outcome_date` come later. Future model code must only use the four historical feature columns plus the label column. Dates, IDs and data-origin markers are metadata.

## Generate and load the demo data

From `backend/`:

```powershell
python -m app.db.generate_synthetic_data
python -m app.db.init_db
python -m app.db.seed
```

The generator uses a fixed NumPy seed, so running it again recreates the same CSV contents. The seed command uses SQLAlchemy `merge`, so running it again updates matching IDs rather than duplicating rows. The local SQLite file is `backend/skillpulse.db` and is ignored by Git; generated CSVs are kept in `data/synthetic/`.

## Module map

- `backend/app/models/models.py` defines the database tables and integrity rules.
- `backend/app/db/base.py` provides the shared SQLAlchemy declarative base.
- `backend/app/db/session.py` configures the SQLite connection and enforces foreign keys.
- `backend/app/db/generate_synthetic_data.py` creates reproducible fictional CSV data.
- `backend/app/db/init_db.py` creates the local tables.
- `backend/app/db/seed.py` loads CSV rows into SQLite in foreign-key order.
- `data/synthetic/README.md` documents the demo-data boundaries and feature/label timing.

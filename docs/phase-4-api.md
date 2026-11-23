# Phase 4: Backend API

The API uses FastAPI request/response schemas, a per-request SQLAlchemy session, and the SQLite database created in Phase 3. Run it from `backend/` with `python -m uvicorn app.main:app --reload`; interactive documentation is available at `http://127.0.0.1:8000/docs`.

## Routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Health check. |
| `GET` | `/api/batches`, `/api/batches/{batch_id}` | Browse training batches. |
| `GET` | `/api/students` | Search/filter by `search`, `batch_id`, and `active`; supports `limit` (1 to 100) and `offset`. |
| `POST` | `/api/students` | Add a learner to an existing batch. New records are marked `manual`. |
| `GET` | `/api/students/{student_id}` | Learner details, up to 12 recent results, attendance and assignment completion rates. |
| `GET` | `/api/students/{student_id}/recommendations` | Rule-based practice suggestions for assessed skills below the review benchmark; insufficient history returns no suggestions. |
| `PATCH` | `/api/students/{student_id}` | Change the learner name or active status; records are retained. |
| `GET` | `/api/assessments?batch_id=...` | Browse assessments, optionally by batch. |
| `POST` | `/api/assessments` | Add an assessment to an existing batch. |
| `POST` | `/api/assessments/{assessment_id}/results` | Record one learner's score for an assessment. |
| `POST` | `/api/assessments/{assessment_id}/results/import` | Validate and atomically import a UTF-8 CSV with `student_id,score` columns (maximum 2 MB and 1,000 rows). Blank score cells are skipped. |
| `GET` | `/api/analytics/overview` | Summary metrics, optionally filtered by `batch_id`. |
| `GET` | `/api/analytics/performance-trend` | Average assessment percentage by assessment date. |
| `GET` | `/api/analytics/skill-gaps` | Skill-area averages and learners below `benchmark` (default 70%). |
| `GET` | `/api/analytics/batch-comparison` | Summary metrics by batch. |

## Metric definitions and boundaries

- Assessment scores are normalized to percentages using each assessment's `max_score`.
- Attendance counts `present` as 1, `late` as 0.5, and `absent` as 0.
- Assignment completion means a submission date is recorded; it does not distinguish early from late work.
- The skill-gap route is a descriptive benchmark calculation, not a prediction. No support labels or model predictions are returned by these endpoints.
- Student and assessment creation validate batch membership and dates. Score entry rejects cross-batch students, scores above the assessment maximum, and duplicate results.
- Score CSV imports validate every populated row before writing; any bad ID, batch, score, or duplicate rejects the entire file. Scores are never silently overwritten.
- These local demo endpoints do not yet provide authentication, authorization or production deployment protections. CSV imports are documented above; keep the deployment local and use synthetic data only.

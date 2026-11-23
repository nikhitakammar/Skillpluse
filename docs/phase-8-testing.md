# Phase 8: Testing and debugging

## Repeatable checks

Run the frontend checks from `frontend/`:

```powershell
npm test
npm run build
```

Run the backend checks from `backend/`:

```powershell
python -m unittest discover -s tests -v
```

Backend tests use only Python's standard `unittest` runner, plus the API/ML packages already listed in `requirements.txt`. They use an in-memory SQLite database for endpoint tests, so they do not modify `skillpulse.db`.

## Coverage

- API health and batch responses
- Learner list/detail aggregates, normalized assessment scores, trends, and attendance
- Assessment result counts and normalized averages
- Assessment CSV import transactionality, score limits, duplicate detection, and batch validation
- Assessment creation date-range validation
- Request validation and missing-batch errors
- Explicit insufficient-data prediction behavior
- Learner-specific practice suggestions and sparse-history handling
- ML feature allowlist and future-label/identifier exclusion
- Logistic Regression stratified holdout sizes, confusion matrix and precision/recall/F1 outputs
- K-Means cluster count and cluster-size totals
- Frontend mapping of API snake_case responses, plus existing search, filtering, pagination, and CSV checks

## Findings fixed during this phase

The new frontend API service test uncovered a dashboard integration defect: per-batch trends and skill gaps were unpacked as separate arrays even though the API requests returned paired objects. The aggregation now flattens the paired results correctly. Dashboard pages also display `N/A` when a score or metric has no recorded data.

## Current verification result

Frontend: 10 tests pass and Vite production build passes. Backend: 12 tests pass using `unittest`. The installed Starlette TestClient emits a deprecation warning about its optional HTTP client; this does not affect test results. No browser-driven visual acceptance test is included yet.

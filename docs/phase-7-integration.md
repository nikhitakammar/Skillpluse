# Phase 7: Frontend and API integration

The Vite app requests dashboard records from FastAPI through `/api`. During development, Vite proxies those requests to `http://127.0.0.1:8000`; set `VITE_API_BASE_URL` in `frontend/.env` to use a different API origin. Copy `.env.example` as a starting point.

The dashboard loads batches, paginated learner records and metrics, assessments, analytics, skill gaps, and model evaluation. Learner profiles load their assessment history, support estimate, and learning cluster when opened. The support estimate is a trainer-assist signal: it must not drive placement or certification decisions.

When the API is unreachable the app keeps the existing synthetic snapshot available, labels it as offline demo data, and offers a retry. When connected, the API badge and notice still identify the seeded records and model as synthetic demonstration data.

## Local run

From `backend`, start the API with `uvicorn app.main:app --reload`. In another terminal, from `frontend`, run `npm run dev`. Open `http://localhost:5173`.

## Verification

Frontend selector tests pass (`npm test`) and the production build passes (`npm run build`). API smoke checks returned HTTP 200 for health, batches, learner list/detail, assessments, overview analytics, performance trend, skill gaps, and model metrics against the seeded SQLite database. The backend does not currently include pytest, so the smoke checks used FastAPI's TestClient directly.

# Skill Pluse

Training Performance & Skill Gap Intelligence Platform.

## Run as a local Docker demonstration

Install Docker Desktop or Docker Engine with the Compose plugin, then run from
the project root:

```powershell
docker compose up --build -d
```

Open `http://localhost:8080`. The API health check is at
`http://localhost:8000/api/health`. SQLite data and trained synthetic model
artifacts persist in the `skillpulse_data` named volume. See
[`docs/phase-9-deployment.md`](docs/phase-9-deployment.md) for startup behavior
and deployment limits.

The dashboard now requires a sign-in. Admins manage trainer and student
accounts, while API role checks protect the underlying data. This remains a
synthetic-data demonstration; see the deployment guide for the controls needed
before using real learner data or opening it to the public internet.

## Demonstration and architecture

- [Five-minute demonstration guide](docs/demo-guide.md) — startup, walkthrough, talk track, supported features and demo boundaries.
- [Architecture overview](docs/architecture.md) — components, data flow and AI/ML limits.
- [Phase 9 deployment instructions](docs/phase-9-deployment.md) — Compose setup and persistence.
- [Phase 8 test instructions](docs/phase-8-testing.md) — repeatable frontend and backend checks.

## Project structure

See [the authentication guide](docs/authentication.md) for account setup and roles.

- `frontend/` contains the React and Vite dashboard.
- `backend/` contains the FastAPI, SQLAlchemy and ML services.
- `data/synthetic/` contains the fictional training records and model snapshots.
- `docs/` contains phase notes, architecture and demonstration instructions.

## Run locally

### Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.start
```

Create the first administrator with `python -m app.auth.bootstrap_admin` on a
new local database. Then `python -m app.start` initializes the schema, seeds synthetic rows if the
database is empty, checks the model artifacts and launches the API. The
frontend runs at `http://127.0.0.1:5173`. The API runs at
`http://127.0.0.1:8000`; its health check is `/api/health` and interactive API
documentation is at `/docs`.

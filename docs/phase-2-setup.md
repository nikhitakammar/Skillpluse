# Phase 2: Local setup

Skill Pluse is split into a React/Vite frontend and a FastAPI backend. They run as two local development servers. The starter dashboard still shows labeled empty states; the Phase 4 API now serves the seeded student records and descriptive analytics for the later frontend-integration phase.

## Frontend

Open PowerShell in `frontend/` and run:

```powershell
npm.cmd install
npm.cmd run dev
```

Vite prints the local URL (normally `http://localhost:5173`). `npm.cmd` works around this Windows environment's PowerShell script policy. To create a production bundle, run `npm.cmd run build`.

## Backend

Open another PowerShell window in `backend/` and create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.db.init_db
.\.venv\Scripts\python.exe -m app.db.seed
.\.venv\Scripts\python.exe -m app.ml.train
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The CSV files in `data/synthetic/` are included in the project. To regenerate them before initializing the database, run `python -m app.db.generate_synthetic_data` from `backend/`.

The API runs at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/api/health` for the health response and `http://127.0.0.1:8000/docs` for the interactive API documentation. Training creates ignored local model artifacts under `backend/artifacts/`.

## Important starter files

- `frontend/src/App.jsx` contains the initial dashboard shell and empty states.
- `frontend/src/styles/global.css` contains the shared responsive styling.
- `frontend/vite.config.js` configures Vite and the local development port.
- `backend/app/main.py` creates the FastAPI app and its health route.
- `backend/app/api/` contains the student, assessment, batch, and analytics endpoints.
- `backend/app/schemas/` defines validated API request and response shapes.
- `backend/app/ml/train.py` trains the demonstration support model and learner clusters.
- `backend/requirements.txt` lists the backend's initial runtime dependencies.
- `frontend/package.json` lists the frontend's dependencies and commands; `package-lock.json` records the resolved versions.

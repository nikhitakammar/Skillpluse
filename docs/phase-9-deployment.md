# Phase 9: Deployment preparation

## Local container demonstration

The Compose setup builds the React client and serves it with Nginx, which
forwards `/api/` requests to FastAPI. SQLite data and model artifacts live in
the `skillpulse_data` volume. The published ports bind to localhost for a
local demonstration.

```powershell
docker compose up --build -d
```

Open `http://localhost:8080`. The API health endpoint is
`http://localhost:8000/api/health`. The first start creates the SQLite schema,
seeds synthetic rows only when the database is empty, and creates the initial
admin if the bootstrap variables are configured.

For a local first run, create a `.env` file in the project root with:

```dotenv
SKILLPULSE_BOOTSTRAP_ADMIN_USERNAME=your-admin-name
SKILLPULSE_BOOTSTRAP_ADMIN_PASSWORD=use-a-unique-password-of-12-or-more-characters
```

Then run Compose and sign in with those credentials. Keep `.env` private; it is
ignored by Git. Remove the bootstrap password from the environment after the
first successful start. Alternatively, without bootstrap variables, create an
admin interactively with `python -m app.auth.bootstrap_admin` in the backend
environment.

## Public deployment status

Authentication and role checks are implemented, but this Compose configuration
is still intentionally local-only: published ports bind to `127.0.0.1`, and it
has not been verified on a public hosting provider. A public demo needs a host
with persistent disk for SQLite, HTTPS, a strong persistent
`SKILLPULSE_JWT_SECRET`, and a securely configured initial admin. Set
`SKILLPULSE_ENVIRONMENT=production`; startup will fail if the JWT secret or
initial admin credentials are missing when no admin account exists. Keep the
service behind HTTPS and do not expose the API's internal port directly.

This application is a synthetic-data demonstration, not yet a reviewed
production service for real learner records. Before real-data use, add and
review backups, account recovery, login rate limiting, audit logging, data
retention controls, and privacy/security obligations relevant to your region.

## Verification status

Backend and frontend tests and the frontend production build pass. Docker
Compose could not be run in this workspace because the Docker CLI is
unavailable. See `authentication.md` for account setup and role behavior.

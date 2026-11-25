# Authentication and account access

Skill Pluse uses username and password sign-in. Passwords are stored as Argon2
hashes. Successful sign-in returns a one-hour bearer token held in browser
session storage. Sign out clears that browser session. The API checks each
request against the active account, so deactivating an account takes effect on
its next request.

## First admin

For local development, start from `backend/` after installing requirements and
run:

```powershell
python -m app.auth.bootstrap_admin
```

This prompts for a username and a password of at least 12 characters. For a
container host, configure `SKILLPULSE_BOOTSTRAP_ADMIN_USERNAME` and
`SKILLPULSE_BOOTSTRAP_ADMIN_PASSWORD` for the first startup, then remove the
bootstrap password from the deployment environment. Do not use a shared or
reused password.

## Roles and access

- **Admin:** create and deactivate accounts, assign trainer access, and view all
  manager data.
- **Trainer:** read only records for individually assigned learners and
  subjects. A Python assignment, for example, grants access to that learner's
  Python performance rather than their other subjects.
- **Student:** view only their linked profile, assessment history, practice
  suggestions, and assignments for their batch.

There is no public sign-up. Admins create accounts from **User access**. For a
trainer, the admin also creates learner/subject assignments on that page.
Removing an assignment revokes its access on the trainer's next API request.
Student accounts must be linked to one learner record. Account creation and
activation are protected by admin-only API checks; trainer screens are
read-only.

Trainer predictions and global model evaluation are admin-only until a
subject-scoped model is available. Learner support predictions are advisory
signals and must not make placement or certification decisions.

The login endpoint is public by design; the remaining data endpoints require
an authenticated role. The API uses a temporary signing secret in local demo
mode if none is configured, which invalidates tokens when the process restarts.
For deployment set a strong persistent `SKILLPULSE_JWT_SECRET` and
`SKILLPULSE_ENVIRONMENT=production`. Never commit secrets to source control.

For current deployment limits and the additional work needed before real-data
use, see [Phase 9 deployment preparation](phase-9-deployment.md).

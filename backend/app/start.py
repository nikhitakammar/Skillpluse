"""Initialize a demo installation and start the API server."""

import uvicorn
import logging
import os
from uuid import uuid4
from sqlalchemy import func, select

from app.db.init_db import initialize_database
from app.db.seed import seed_database
from app.db.session import SessionLocal
from app.ml.inference import (
    ModelUnavailable,
    get_cluster_bundle,
    get_cluster_metrics,
    get_support_bundle,
    get_support_metrics,
)
from app.ml.train import train_models
from app.models import Batch, UserAccount
from app.security.auth import hash_password

logger = logging.getLogger(__name__)


def prepare_demo_installation() -> None:
    """Create schema, seed only an empty database, and ensure model artifacts exist."""
    initialize_database()
    with SessionLocal() as session:
        batch_count = session.scalar(select(func.count()).select_from(Batch)) or 0
    if batch_count == 0:
        seed_database()

    bootstrap_username = os.environ.get("SKILLPULSE_BOOTSTRAP_ADMIN_USERNAME", "").strip().casefold()
    bootstrap_password = os.environ.get("SKILLPULSE_BOOTSTRAP_ADMIN_PASSWORD", "")
    if (bootstrap_username or bootstrap_password) and (len(bootstrap_username) < 3 or len(bootstrap_password) < 12):
        raise RuntimeError("Configure both bootstrap admin values; the username needs 3+ characters and password needs 12+")
    with SessionLocal() as session:
        admin_exists = session.scalar(select(UserAccount.user_id).where(UserAccount.role == "admin")) is not None
        if not admin_exists:
            if bootstrap_username and len(bootstrap_password) >= 12:
                existing = session.scalar(select(UserAccount).where(UserAccount.username == bootstrap_username))
                if existing is not None:
                    raise RuntimeError("Bootstrap admin username already belongs to a non-admin account")
                session.add(UserAccount(
                    user_id=str(uuid4()),
                    username=bootstrap_username,
                    password_hash=hash_password(bootstrap_password),
                    role="admin",
                    student_id=None,
                    is_active=True,
                ))
                session.commit()
                logger.info("Created the initial admin account from environment configuration")
            elif os.environ.get("SKILLPULSE_ENVIRONMENT", "demo").casefold() == "production":
                raise RuntimeError("Set SKILLPULSE_BOOTSTRAP_ADMIN_USERNAME and a 12+ character SKILLPULSE_BOOTSTRAP_ADMIN_PASSWORD before first production startup")
            else:
                logger.warning("No admin account exists. Create one with `python -m app.auth.bootstrap_admin` before signing in.")

    try:
        get_support_bundle()
        get_cluster_bundle()
        get_support_metrics()
        get_cluster_metrics()
    except (ModelUnavailable, FileNotFoundError):
        train_models()


if __name__ == "__main__":
    prepare_demo_installation()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)

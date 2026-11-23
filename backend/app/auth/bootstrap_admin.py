"""Create the first admin account interactively for a local installation."""

from getpass import getpass
from uuid import uuid4

from sqlalchemy import select

from app.db.init_db import initialize_database
from app.db.session import SessionLocal
from app.models import UserAccount
from app.security.auth import hash_password


def main() -> None:
    initialize_database()
    with SessionLocal() as db:
        if db.scalar(select(UserAccount.user_id).where(UserAccount.role == "admin")):
            raise SystemExit("An admin account already exists. Ask an administrator to create or reset accounts.")
        username = input("Admin username: ").strip().casefold()
        password = getpass("Admin password (at least 12 characters): ")
        confirmation = getpass("Confirm admin password: ")
        if len(username) < 3 or len(username) > 40:
            raise SystemExit("Username must be 3 to 40 characters.")
        if any(not (char.isalnum() or char in "._-") for char in username):
            raise SystemExit("Username may contain letters, numbers, dots, underscores and hyphens.")
        if len(password) < 12 or len(password) > 128:
            raise SystemExit("Password must be 12 to 128 characters.")
        if password != confirmation:
            raise SystemExit("Passwords did not match.")
        if db.scalar(select(UserAccount.user_id).where(UserAccount.username == username)):
            raise SystemExit("Username is already in use.")
        db.add(UserAccount(
            user_id=str(uuid4()),
            username=username,
            password_hash=hash_password(password),
            role="admin",
            student_id=None,
            is_active=True,
        ))
        db.commit()
        print(f"Admin account '{username}' created. Keep the password private.")


if __name__ == "__main__":
    main()

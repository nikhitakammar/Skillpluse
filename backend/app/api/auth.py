"""Login, current-user and administrator account-management endpoints."""

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Assessment, Student, TrainerSubject, UserAccount
from app.schemas.auth import LoginRequest, LoginResponse, UserCreate, UserRead, UserStatusPatch
from app.security.auth import (
    ACCESS_TOKEN_SECONDS,
    DUMMY_PASSWORD_HASH,
    create_access_token,
    current_user,
    hash_password,
    require_roles,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


def serialize_user(account: UserAccount, db: Session) -> UserRead:
    subject = None
    if account.role == "trainer":
        subject = db.scalar(select(TrainerSubject.skill_area).where(TrainerSubject.trainer_user_id == account.user_id))
    return UserRead(
        user_id=account.user_id,
        username=account.username,
        role=account.role,
        student_id=account.student_id,
        subject=subject,
        is_active=account.is_active,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    username = payload.username.strip().casefold()
    user = db.scalar(select(UserAccount).where(UserAccount.username == username))
    stored_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_is_valid = verify_password(payload.password, stored_hash)
    if user is None or not user.is_active or not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username or password is incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return LoginResponse(
        access_token=create_access_token(user.user_id),
        expires_in=ACCESS_TOKEN_SECONDS,
        user=serialize_user(user, db),
    )


@router.get("/me", response_model=UserRead)
def who_am_i(user: UserAccount = Depends(current_user), db: Session = Depends(get_db)) -> UserRead:
    return serialize_user(user, db)


@router.get("/users", response_model=list[UserRead])
def list_users(
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    return [serialize_user(account, db) for account in db.scalars(select(UserAccount).order_by(UserAccount.username))]


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> UserRead:
    if db.scalar(select(UserAccount.user_id).where(UserAccount.username == payload.username)):
        raise HTTPException(status_code=409, detail="Username is already in use")
    if payload.role == "student":
        student = db.get(Student, payload.student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student record not found")
        if db.scalar(select(UserAccount.user_id).where(UserAccount.student_id == payload.student_id)):
            raise HTTPException(status_code=409, detail="This student already has a login account")
    subject = None
    if payload.role == "trainer":
        subject = db.scalar(
            select(Assessment.skill_area).where(Assessment.skill_area.ilike(payload.subject.strip())).limit(1)
        )
        if subject is None:
            raise HTTPException(status_code=422, detail="Select a subject that is offered by a training batch")

    account = UserAccount(
        user_id=str(uuid4()),
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        student_id=payload.student_id,
        is_active=True,
    )
    db.add(account)
    try:
        # Flush the parent account first so SQLite can validate the trainer subject foreign key.
        db.flush()
        if subject:
            db.add(TrainerSubject(assignment_id=str(uuid4()), trainer_user_id=account.user_id, skill_area=subject))
        db.commit()
    except IntegrityError as error:
        db.rollback()
        message = str(error.orig).casefold()
        if "user_accounts.username" in message:
            detail = "That username is already in use. Choose a different username."
        elif "user_accounts.student_id" in message:
            detail = "This learner already has a student account."
        elif "trainer_subjects" in message:
            detail = "The trainer account could not be linked to that subject. Refresh the page and try again."
        else:
            detail = "The account could not be created. Refresh the page and try again."
        raise HTTPException(status_code=409, detail=detail) from None
    db.refresh(account)
    return serialize_user(account, db)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user_status(
    user_id: str,
    payload: UserStatusPatch,
    admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> UserRead:
    account = db.get(UserAccount, user_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.user_id == admin.user_id and not payload.is_active:
        raise HTTPException(status_code=422, detail="You cannot deactivate your own account")
    account.is_active = payload.is_active
    db.commit()
    db.refresh(account)
    return serialize_user(account, db)

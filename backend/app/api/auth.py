"""Login, current-user and administrator account-management endpoints."""

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Student, UserAccount
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
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def who_am_i(user: UserAccount = Depends(current_user)) -> UserAccount:
    return user


@router.get("/users", response_model=list[UserRead])
def list_users(
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[UserAccount]:
    return list(db.scalars(select(UserAccount).order_by(UserAccount.username)))


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> UserAccount:
    if db.scalar(select(UserAccount.user_id).where(UserAccount.username == payload.username)):
        raise HTTPException(status_code=409, detail="Username is already in use")
    if payload.role == "student":
        student = db.get(Student, payload.student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student record not found")
        if db.scalar(select(UserAccount.user_id).where(UserAccount.student_id == payload.student_id)):
            raise HTTPException(status_code=409, detail="This student already has a login account")

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
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or student account is already in use") from None
    db.refresh(account)
    return account


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user_status(
    user_id: str,
    payload: UserStatusPatch,
    admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> UserAccount:
    account = db.get(UserAccount, user_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.user_id == admin.user_id and not payload.is_active:
        raise HTTPException(status_code=422, detail="You cannot deactivate your own account")
    account.is_active = payload.is_active
    db.commit()
    db.refresh(account)
    return account

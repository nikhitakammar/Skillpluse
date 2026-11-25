"""Admin-only management of trainer access to learner subjects."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Assessment, Student, TrainerStudentSubject, UserAccount
from app.schemas.trainer_scopes import TrainerStudentSubjectCreate, TrainerStudentSubjectRead
from app.security.auth import require_roles

router = APIRouter(prefix="/trainer-scopes", tags=["trainer access"])


def serialize_scope(scope: TrainerStudentSubject, trainer: UserAccount, student: Student) -> dict:
    return {
        "scope_id": scope.scope_id,
        "trainer_user_id": scope.trainer_user_id,
        "trainer_username": trainer.username,
        "student_id": scope.student_id,
        "student_name": student.full_name,
        "skill_area": scope.skill_area,
    }


@router.get("", response_model=list[TrainerStudentSubjectRead])
def list_trainer_scopes(
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(
        select(TrainerStudentSubject, UserAccount, Student)
        .join(UserAccount, UserAccount.user_id == TrainerStudentSubject.trainer_user_id)
        .join(Student, Student.student_id == TrainerStudentSubject.student_id)
        .order_by(UserAccount.username, Student.full_name, TrainerStudentSubject.skill_area)
    ).all()
    return [serialize_scope(scope, trainer, student) for scope, trainer, student in rows]


@router.get("/mine", response_model=list[TrainerStudentSubjectRead])
def list_my_trainer_scopes(
    trainer: UserAccount = Depends(require_roles("trainer")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return only the learner/subject assignments for the signed-in trainer."""
    rows = db.execute(
        select(TrainerStudentSubject, UserAccount, Student)
        .join(UserAccount, UserAccount.user_id == TrainerStudentSubject.trainer_user_id)
        .join(Student, Student.student_id == TrainerStudentSubject.student_id)
        .where(TrainerStudentSubject.trainer_user_id == trainer.user_id)
        .order_by(TrainerStudentSubject.skill_area, Student.full_name, Student.student_id)
    ).all()
    return [serialize_scope(scope, owner, student) for scope, owner, student in rows]


@router.post("", response_model=TrainerStudentSubjectRead, status_code=status.HTTP_201_CREATED)
def create_trainer_scope(
    payload: TrainerStudentSubjectCreate,
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    trainer = db.get(UserAccount, payload.trainer_user_id)
    if trainer is None or trainer.role != "trainer":
        raise HTTPException(status_code=404, detail="Trainer account not found")
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Learner record not found")
    subject = db.scalar(
        select(Assessment.skill_area)
        .where(
            Assessment.batch_id == student.batch_id,
            func.lower(Assessment.skill_area) == payload.skill_area.casefold(),
        )
        .limit(1)
    )
    if subject is None:
        raise HTTPException(status_code=422, detail="That subject has no assessment in this learner's batch")

    scope = TrainerStudentSubject(
        scope_id=str(uuid4()),
        trainer_user_id=trainer.user_id,
        student_id=student.student_id,
        skill_area=subject,
    )
    db.add(scope)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This trainer already has access to that learner and subject") from None
    db.refresh(scope)
    return serialize_scope(scope, trainer, student)


@router.delete("/{scope_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trainer_scope(
    scope_id: str,
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> None:
    scope = db.get(TrainerStudentSubject, scope_id)
    if scope is None:
        raise HTTPException(status_code=404, detail="Trainer assignment not found")
    db.delete(scope)
    db.commit()

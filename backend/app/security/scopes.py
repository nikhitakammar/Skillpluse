"""Reusable authorization helpers for subject-based trainer access."""

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Assessment, Student, TrainerSubject, UserAccount


def trainer_subjects(user: UserAccount):
    return select(func.lower(TrainerSubject.skill_area)).where(TrainerSubject.trainer_user_id == user.user_id)


def trainer_student_scope(query, user: UserAccount, student_column):
    """Limit a trainer to learners in batches that offer their subject."""
    if user.role != "trainer":
        return query
    assigned_students = (
        select(Student.student_id)
        .join(Assessment, Assessment.batch_id == Student.batch_id)
        .where(func.lower(Assessment.skill_area).in_(trainer_subjects(user)))
        .distinct()
    )
    return query.where(student_column.in_(assigned_students))


def trainer_skill_scope(query, user: UserAccount, student_column, skill_column):
    """Limit assessment/assignment rows to the trainer's subject."""
    if user.role != "trainer":
        return query
    return query.where(func.lower(skill_column).in_(trainer_subjects(user)))


def trainer_batch_skill_scope(query, user: UserAccount, batch_column, skill_column):
    """Limit batch-level records to the trainer's subject."""
    if user.role != "trainer":
        return query
    return query.where(func.lower(skill_column).in_(trainer_subjects(user)))


def trainer_batch_ids(db: Session, user: UserAccount) -> set[str] | None:
    if user.role != "trainer":
        return None
    query = select(Assessment.batch_id).where(func.lower(Assessment.skill_area).in_(trainer_subjects(user))).distinct()
    return set(db.scalars(query).all())


def student_skill_access(db: Session, user: UserAccount, student_id: str) -> set[str] | None:
    """Authorize a profile request and return its allowed subject names.

    None means the caller may access all subjects for this student; a set is the
    exact subject allowlist for a trainer.
    """
    if user.role == "admin":
        return None
    if user.role == "student":
        if user.student_id != student_id:
            raise HTTPException(status_code=403, detail="Student accounts can only access their own records")
        return None
    if user.role == "trainer":
        learner = db.get(Student, student_id)
        if learner is None:
            raise HTTPException(status_code=404, detail="Student not found")
        skills = set(db.scalars(
            select(Assessment.skill_area).where(
                Assessment.batch_id == learner.batch_id,
                func.lower(Assessment.skill_area).in_(trainer_subjects(user)),
            ).distinct()
        ).all())
        if not skills:
            raise HTTPException(status_code=403, detail="This learner is not in a batch for your subject")
        return skills
    raise HTTPException(status_code=403, detail="Your role cannot access learner records")

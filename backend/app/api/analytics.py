"""Descriptive analytics based only on recorded training activity."""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import (
    Assessment,
    AssessmentResult,
    Assignment,
    AssignmentSubmission,
    AttendanceRecord,
    Batch,
    Student,
    TrainerSubject,
    UserAccount,
)
from app.schemas.analytics import (
    BatchComparison,
    OverviewSummary,
    PerformanceTrendPoint,
    SkillGap,
)
from app.security.auth import require_roles
from app.security.scopes import trainer_skill_scope, trainer_student_scope

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_roles("admin", "trainer"))])


def check_batch(db: Session, batch_id: str | None) -> None:
    if batch_id and db.get(Batch, batch_id) is None:
        raise HTTPException(status_code=404, detail="Batch not found")


def score_average(db: Session, batch_id: str | None, user: UserAccount) -> float | None:
    query = select(func.avg(AssessmentResult.score / Assessment.max_score * 100)).join(
        Assessment, Assessment.assessment_id == AssessmentResult.assessment_id
    )
    if batch_id:
        query = query.where(Assessment.batch_id == batch_id)
    query = trainer_skill_scope(query, user, AssessmentResult.student_id, Assessment.skill_area)
    value = db.scalar(query)
    return round(float(value), 2) if value is not None else None


def attendance_percentage(db: Session, batch_id: str | None, user: UserAccount) -> float | None:
    query = select(
        func.sum(case((AttendanceRecord.status == "present", 1.0), (AttendanceRecord.status == "late", 0.5), else_=0.0)),
        func.count(AttendanceRecord.attendance_id),
    ).join(Student, Student.student_id == AttendanceRecord.student_id)
    if batch_id:
        query = query.where(Student.batch_id == batch_id)
    query = trainer_student_scope(query, user, AttendanceRecord.student_id)
    attended, total = db.execute(query).one()
    return round(float(attended) / total * 100, 2) if total else None


def assignment_completion_percentage(db: Session, batch_id: str | None, user: UserAccount) -> float | None:
    query = select(
        func.sum(case((AssignmentSubmission.submitted_at.is_not(None), 1), else_=0)),
        func.count(AssignmentSubmission.submission_id),
    ).join(Student, Student.student_id == AssignmentSubmission.student_id).join(
        Assignment, Assignment.assignment_id == AssignmentSubmission.assignment_id
    )
    if batch_id:
        query = query.where(Student.batch_id == batch_id)
    query = trainer_skill_scope(query, user, AssignmentSubmission.student_id, Assignment.skill_area)
    submitted, total = db.execute(query).one()
    return round(float(submitted) / total * 100, 2) if total else None


@router.get("/overview", response_model=OverviewSummary)
def overview(
    batch_id: str | None = Query(default=None, max_length=20),
    user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> OverviewSummary:
    check_batch(db, batch_id)
    learners_query = select(func.count(Student.student_id)).where(Student.is_active.is_(True))
    if batch_id:
        learners_query = learners_query.where(Student.batch_id == batch_id)
    learners_query = trainer_student_scope(learners_query, user, Student.student_id)
    total_batches_query = select(func.count(Batch.batch_id))
    if batch_id:
        total_batches_query = total_batches_query.where(Batch.batch_id == batch_id)
    if user.role == "trainer":
        total_batches_query = (
            select(func.count(func.distinct(Student.batch_id)))
            .join(Assessment, Assessment.batch_id == Student.batch_id)
            .join(TrainerSubject, func.lower(TrainerSubject.skill_area) == func.lower(Assessment.skill_area))
            .where(TrainerSubject.trainer_user_id == user.user_id)
        )
        if batch_id:
            total_batches_query = total_batches_query.where(Student.batch_id == batch_id)
    return OverviewSummary(
        active_learners=db.scalar(learners_query) or 0,
        total_batches=db.scalar(total_batches_query) or 0,
        average_score=score_average(db, batch_id, user),
        attendance_rate=attendance_percentage(db, batch_id, user),
        assignment_completion_rate=assignment_completion_percentage(db, batch_id, user),
    )


@router.get("/performance-trend", response_model=list[PerformanceTrendPoint])
def performance_trend(
    batch_id: str | None = Query(default=None, max_length=20),
    user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> list[PerformanceTrendPoint]:
    check_batch(db, batch_id)
    query = select(
        Assessment.assessment_date,
        func.avg(AssessmentResult.score / Assessment.max_score * 100),
    ).join(AssessmentResult, AssessmentResult.assessment_id == Assessment.assessment_id)
    if batch_id:
        query = query.where(Assessment.batch_id == batch_id)
    query = trainer_skill_scope(query, user, AssessmentResult.student_id, Assessment.skill_area)
    query = query.group_by(Assessment.assessment_date).order_by(Assessment.assessment_date)
    return [
        PerformanceTrendPoint(assessment_date=assessment_date, average_score=round(float(average), 2))
        for assessment_date, average in db.execute(query)
    ]


@router.get("/skill-gaps", response_model=list[SkillGap])
def skill_gaps(
    batch_id: str | None = Query(default=None, max_length=20),
    benchmark: float = Query(default=70, ge=0, le=100),
    user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> list[SkillGap]:
    check_batch(db, batch_id)
    query = select(
        AssessmentResult.student_id,
        Assessment.skill_area,
        func.avg(AssessmentResult.score / Assessment.max_score * 100),
    ).join(Assessment, Assessment.assessment_id == AssessmentResult.assessment_id)
    if batch_id:
        query = query.where(Assessment.batch_id == batch_id)
    query = trainer_skill_scope(query, user, AssessmentResult.student_id, Assessment.skill_area)
    query = query.group_by(AssessmentResult.student_id, Assessment.skill_area)

    by_skill: dict[str, list[float]] = defaultdict(list)
    for _student_id, skill_area, average in db.execute(query):
        by_skill[skill_area].append(float(average))
    return [
        SkillGap(
            skill_area=skill,
            average_score=round(sum(scores) / len(scores), 2),
            learners_below_benchmark=sum(score < benchmark for score in scores),
            benchmark=benchmark,
        )
        for skill, scores in sorted(by_skill.items())
    ]


@router.get("/batch-comparison", response_model=list[BatchComparison])
def batch_comparison(
    user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> list[BatchComparison]:
    batch_query = select(Batch)
    if user.role == "trainer":
        assigned_batches = select(Assessment.batch_id).join(
            TrainerSubject, func.lower(TrainerSubject.skill_area) == func.lower(Assessment.skill_area)
        ).where(TrainerSubject.trainer_user_id == user.user_id)
        batch_query = batch_query.where(Batch.batch_id.in_(assigned_batches))
    batches = db.scalars(batch_query.order_by(Batch.name)).all()
    summaries = []
    for batch in batches:
        learner_count_query = select(func.count(Student.student_id)).where(
            Student.batch_id == batch.batch_id, Student.is_active.is_(True)
        )
        learner_count_query = trainer_student_scope(learner_count_query, user, Student.student_id)
        summaries.append(
            BatchComparison(
                batch_id=batch.batch_id,
                name=batch.name,
                active_learners=db.scalar(learner_count_query) or 0,
                average_score=score_average(db, batch.batch_id, user),
                attendance_rate=attendance_percentage(db, batch.batch_id, user),
                assignment_completion_rate=assignment_completion_percentage(db, batch.batch_id, user),
            )
        )
    return summaries

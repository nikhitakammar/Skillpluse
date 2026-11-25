"""Student search and basic management endpoints."""

from uuid import uuid4
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
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
from app.schemas.students import (
    StudentAssignmentRead,
    StudentCreate,
    StudentDetail,
    StudentListItem,
    StudentPage,
    StudentPatch,
    StudentRead,
    StudentScore,
)
from app.security.auth import current_user, require_roles
from app.security.scopes import student_skill_access, trainer_skill_scope, trainer_student_scope

router = APIRouter(prefix="/students", tags=["students"])


def activity_metrics(db: Session, student_ids: list[str], user: UserAccount, skill_area: str | None = None) -> dict[str, dict[str, float | None]]:
    """Compute list/detail metrics in bulk so the roster avoids per-student queries."""
    score_by_student_date: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    score_query = (
        select(AssessmentResult.student_id, Assessment.assessment_date, AssessmentResult.score, Assessment.max_score)
        .join(Assessment, Assessment.assessment_id == AssessmentResult.assessment_id)
        .where(AssessmentResult.student_id.in_(student_ids))
        .order_by(Assessment.assessment_date)
    )
    score_query = trainer_skill_scope(score_query, user, AssessmentResult.student_id, Assessment.skill_area)
    if skill_area:
        score_query = score_query.where(func.lower(Assessment.skill_area) == skill_area.casefold())
    score_rows = db.execute(score_query).all() if student_ids else []
    all_scores: dict[str, list[float]] = defaultdict(list)
    for student_id, assessment_date, score, max_score in score_rows:
        percentage = float(score) / float(max_score) * 100
        score_by_student_date[student_id][assessment_date].append(percentage)
        all_scores[student_id].append(percentage)

    attendance_by_student: dict[str, list[str]] = defaultdict(list)
    attendance_rows = db.execute(
        select(AttendanceRecord.student_id, AttendanceRecord.status)
        .where(AttendanceRecord.student_id.in_(student_ids))
    ).all() if student_ids else []
    for student_id, attendance_status in attendance_rows:
        attendance_by_student[student_id].append(attendance_status)

    submissions_by_student: dict[str, list] = defaultdict(list)
    submission_query = (
        select(AssignmentSubmission.student_id, AssignmentSubmission.submitted_at)
        .join(Assignment, Assignment.assignment_id == AssignmentSubmission.assignment_id)
        .where(AssignmentSubmission.student_id.in_(student_ids))
    )
    submission_query = trainer_skill_scope(submission_query, user, AssignmentSubmission.student_id, Assignment.skill_area)
    if skill_area:
        submission_query = submission_query.where(func.lower(Assignment.skill_area) == skill_area.casefold())
    submission_rows = db.execute(submission_query).all() if student_ids else []
    for student_id, submitted_at in submission_rows:
        submissions_by_student[student_id].append(submitted_at)

    metrics = {}
    for student_id in student_ids:
        date_scores = score_by_student_date[student_id]
        dates = sorted(date_scores)
        trend = None
        if len(dates) >= 2:
            first_average = sum(date_scores[dates[0]]) / len(date_scores[dates[0]])
            latest_average = sum(date_scores[dates[-1]]) / len(date_scores[dates[-1]])
            trend = round(latest_average - first_average, 2)
        attendance = attendance_by_student[student_id]
        submissions = submissions_by_student[student_id]
        metrics[student_id] = {
            "average_score": round(sum(all_scores[student_id]) / len(all_scores[student_id]), 2) if all_scores[student_id] else None,
            "score_trend": trend,
            "attendance_rate": round((attendance.count("present") + 0.5 * attendance.count("late")) / len(attendance) * 100, 2) if attendance else None,
            "assignment_completion_rate": round(sum(value is not None for value in submissions) / len(submissions) * 100, 2) if submissions else None,
        }
    return metrics


@router.get("", response_model=StudentPage)
def list_students(
    search: str | None = Query(default=None, max_length=120),
    batch_id: str | None = Query(default=None, max_length=20),
    skill_area: str | None = Query(default=None, max_length=80),
    active: bool | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> StudentPage:
    query = select(Student)
    query = trainer_student_scope(query, user, Student.student_id)
    if skill_area and user.role == "trainer":
        subject_is_assigned = db.scalar(select(TrainerSubject.assignment_id).where(
            TrainerSubject.trainer_user_id == user.user_id,
            func.lower(TrainerSubject.skill_area) == skill_area.casefold(),
        ))
        if subject_is_assigned is None:
            raise HTTPException(status_code=403, detail="This trainer is not assigned to that subject")
    if batch_id:
        if db.get(Batch, batch_id) is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        query = query.where(Student.batch_id == batch_id)
    if active is not None:
        query = query.where(Student.is_active == active)
    if search and search.strip():
        query = query.where(Student.full_name.ilike(f"%{search.strip()}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    students = db.scalars(query.order_by(Student.full_name, Student.student_id).offset(offset).limit(limit)).all()
    activity = activity_metrics(db, [student.student_id for student in students], user, skill_area)
    items = [
        {**StudentRead.model_validate(student).model_dump(), **activity[student.student_id]}
        for student in students
    ]
    return StudentPage(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Student:
    batch = db.get(Batch, payload.batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    if not batch.start_date <= payload.enrollment_date <= batch.end_date:
        raise HTTPException(status_code=422, detail="Enrollment date must fall within the batch dates")

    student = Student(
        student_id=f"STU-{uuid4().hex[:8].upper()}",
        batch_id=payload.batch_id,
        full_name=payload.full_name.strip(),
        enrollment_date=payload.enrollment_date,
        is_active=True,
        data_origin="manual",
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentDetail)
def get_student(
    student_id: str,
    skill_area: str | None = Query(default=None, max_length=80),
    user: UserAccount = Depends(current_user),
    db: Session = Depends(get_db),
) -> StudentDetail:
    allowed_skills = student_skill_access(db, user, student_id)
    if skill_area and allowed_skills is not None and skill_area.casefold() not in {item.casefold() for item in allowed_skills}:
        raise HTTPException(status_code=403, detail="This trainer is not assigned to that learner's subject")
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    result_query = (
        select(AssessmentResult, Assessment)
        .join(Assessment, Assessment.assessment_id == AssessmentResult.assessment_id)
        .where(AssessmentResult.student_id == student_id)
        .order_by(Assessment.assessment_date.desc(), Assessment.title)
        .limit(12)
    )
    if allowed_skills is not None:
        result_query = result_query.where(Assessment.skill_area.in_(allowed_skills))
    if skill_area:
        result_query = result_query.where(func.lower(Assessment.skill_area) == skill_area.casefold())
    results = db.execute(result_query).all()
    scores = [
        StudentScore(
            assessment_id=assessment.assessment_id,
            title=assessment.title,
            skill_area=assessment.skill_area,
            assessment_date=assessment.assessment_date,
            score=result.score,
            max_score=assessment.max_score,
            score_percent=round(result.score / assessment.max_score * 100, 2),
        )
        for result, assessment in results
    ]

    activity = activity_metrics(db, [student_id], user, skill_area)[student_id]

    return StudentDetail(
        student=StudentRead.model_validate(student),
        recent_assessments=scores,
        average_score=activity["average_score"],
        score_trend=activity["score_trend"],
        attendance_rate=activity["attendance_rate"],
        assignment_completion_rate=activity["assignment_completion_rate"],
    )


@router.patch("/{student_id}", response_model=StudentRead)
def update_student(
    student_id: str,
    payload: StudentPatch,
    _admin: UserAccount = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one field to update")
    if "full_name" in changes:
        if changes["full_name"] is None:
            raise HTTPException(status_code=422, detail="full_name cannot be null")
        student.full_name = changes["full_name"].strip()
    if "is_active" in changes:
        if changes["is_active"] is None:
            raise HTTPException(status_code=422, detail="is_active cannot be null")
        student.is_active = changes["is_active"]
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}/assignments", response_model=list[StudentAssignmentRead])
def list_student_assignments(
    student_id: str,
    user: UserAccount = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    allowed_skills = student_skill_access(db, user, student_id)
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    query = (
        select(Assignment, AssignmentSubmission)
        .outerjoin(
            AssignmentSubmission,
            (AssignmentSubmission.assignment_id == Assignment.assignment_id)
            & (AssignmentSubmission.student_id == student_id),
        )
        .where(Assignment.batch_id == student.batch_id)
        .order_by(Assignment.due_date, Assignment.title)
    )
    if allowed_skills is not None:
        query = query.where(Assignment.skill_area.in_(allowed_skills))

    from datetime import date

    today = date.today()
    result = []
    for assignment, submission in db.execute(query):
        status_label = "submitted" if submission and submission.submitted_at else "overdue" if assignment.due_date < today else "pending"
        result.append({
            "assignment_id": assignment.assignment_id,
            "title": assignment.title,
            "skill_area": assignment.skill_area,
            "assigned_date": assignment.assigned_date,
            "due_date": assignment.due_date,
            "submitted_at": submission.submitted_at if submission else None,
            "score": submission.score if submission else None,
            "status": status_label,
        })
    return result

"""Attendance summaries and per-learner session marking."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import AttendanceRecord, Student, UserAccount
from app.schemas.attendance import AttendanceMark, AttendanceRecordRead, AttendanceSummaryRead
from app.security.auth import current_user, require_roles
from app.security.scopes import student_skill_access, trainer_student_scope

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/summary", response_model=list[AttendanceSummaryRead])
def attendance_summary(
    batch_id: str | None = Query(default=None, max_length=20),
    user: UserAccount = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(Student)
    if user.role == "student":
        query = query.where(Student.student_id == user.student_id)
    else:
        query = trainer_student_scope(query, user, Student.student_id)
    if batch_id:
        query = query.where(Student.batch_id == batch_id)
    learners = db.scalars(query.order_by(Student.full_name)).all()
    learner_ids = [learner.student_id for learner in learners]
    records = db.execute(
        select(AttendanceRecord.student_id, AttendanceRecord.status)
        .where(AttendanceRecord.student_id.in_(learner_ids))
    ).all() if learner_ids else []
    totals = {student_id: {"present": 0, "late": 0, "absent": 0} for student_id in learner_ids}
    for student_id, status in records:
        totals[student_id][status] += 1
    return [
        {
            "student_id": learner.student_id,
            "full_name": learner.full_name,
            "batch_id": learner.batch_id,
            "present_count": totals[learner.student_id]["present"],
            "late_count": totals[learner.student_id]["late"],
            "absent_count": totals[learner.student_id]["absent"],
            "attendance_rate": round(
                (totals[learner.student_id]["present"] + .5 * totals[learner.student_id]["late"])
                / sum(totals[learner.student_id].values()) * 100, 2
            ) if sum(totals[learner.student_id].values()) else None,
        }
        for learner in learners
    ]


@router.put("/{student_id}", response_model=AttendanceRecordRead)
def mark_attendance(
    student_id: str,
    payload: AttendanceMark,
    _user: UserAccount = Depends(require_roles("admin", "trainer")),
    db: Session = Depends(get_db),
) -> AttendanceRecord:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Learner not found")
    student_skill_access(db, _user, student_id)
    record = db.scalar(select(AttendanceRecord).where(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.session_date == payload.session_date,
    ))
    if record is None:
        record = AttendanceRecord(
            attendance_id=f"ATT-{uuid4().hex[:12].upper()}",
            student_id=student_id,
            session_date=payload.session_date,
            status=payload.status,
        )
        db.add(record)
    else:
        record.status = payload.status
    db.commit()
    db.refresh(record)
    return record

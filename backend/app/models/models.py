"""Relational records used by training management and future analytics."""

from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Batch(Base):
    __tablename__ = "batches"

    batch_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    program: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    data_origin: Mapped[str] = mapped_column(String(30), nullable=False, default="synthetic_demo")


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.batch_id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    enrollment_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_origin: Mapped[str] = mapped_column(String(30), nullable=False, default="synthetic_demo")


class UserAccount(Base):
    __tablename__ = "user_accounts"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'trainer', 'student')", name="ck_user_role"),
    )

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.student_id"), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Assessment(Base):
    __tablename__ = "assessments"

    assessment_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.batch_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    skill_area: Mapped[str] = mapped_column(String(80), nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=100)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)


class AssessmentResult(Base):
    __tablename__ = "assessment_results"
    __table_args__ = (
        UniqueConstraint("student_id", "assessment_id", name="uq_result_student_assessment"),
        CheckConstraint("score >= 0", name="ck_result_score_nonnegative"),
    )

    result_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), nullable=False, index=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.assessment_id"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "session_date", name="uq_attendance_student_session"),
        CheckConstraint("status IN ('present', 'late', 'absent')", name="ck_attendance_status"),
    )

    attendance_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), nullable=False, index=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)


class Assignment(Base):
    __tablename__ = "assignments"

    assignment_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.batch_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    skill_area: Mapped[str] = mapped_column(String(80), nullable=False)
    assigned_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint("student_id", "assignment_id", name="uq_submission_student_assignment"),
        CheckConstraint("score IS NULL OR score >= 0", name="ck_submission_score_nonnegative"),
    )

    submission_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), nullable=False, index=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_id"), nullable=False, index=True)
    submitted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)


class SupportOutcome(Base):
    """Synthetic follow-up label recorded after a learner feature snapshot."""

    __tablename__ = "support_outcomes"
    __table_args__ = (CheckConstraint("needs_support IN (0, 1)", name="ck_support_outcome_binary"),)

    outcome_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    outcome_date: Mapped[date] = mapped_column(Date, nullable=False)
    needs_support: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_origin: Mapped[str] = mapped_column(String(30), nullable=False, default="synthetic_demo")

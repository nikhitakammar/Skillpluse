"""Attendance review and marking payloads."""

from datetime import date

from pydantic import BaseModel, Field


class AttendanceSummaryRead(BaseModel):
    student_id: str
    full_name: str
    batch_id: str
    present_count: int
    late_count: int
    absent_count: int
    attendance_rate: float | None


class AttendanceMark(BaseModel):
    session_date: date
    status: str = Field(pattern="^(present|late|absent)$")


class AttendanceRecordRead(AttendanceMark):
    attendance_id: str
    student_id: str


"""Student API request and response models."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StudentCreate(BaseModel):
    batch_id: str = Field(min_length=1, max_length=20)
    full_name: str = Field(min_length=2, max_length=120)
    enrollment_date: date

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Name must contain at least two non-space characters")
        return cleaned


class StudentPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Name must contain at least two non-space characters")
        return cleaned


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: str
    batch_id: str
    full_name: str
    enrollment_date: date
    is_active: bool
    data_origin: str


class StudentPage(BaseModel):
    items: list["StudentListItem"]
    total: int
    limit: int
    offset: int


class StudentListItem(StudentRead):
    average_score: float | None
    score_trend: float | None
    attendance_rate: float | None
    assignment_completion_rate: float | None


class StudentScore(BaseModel):
    assessment_id: str
    title: str
    skill_area: str
    assessment_date: date
    score: float
    max_score: float
    score_percent: float


class StudentDetail(BaseModel):
    student: StudentRead
    recent_assessments: list[StudentScore]
    average_score: float | None
    score_trend: float | None
    attendance_rate: float | None
    assignment_completion_rate: float | None


class StudentAssignmentRead(BaseModel):
    assignment_id: str
    title: str
    skill_area: str
    assigned_date: date
    due_date: date
    submitted_at: date | None
    score: float | None
    status: str

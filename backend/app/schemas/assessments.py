"""Assessment API request and response models."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssessmentCreate(BaseModel):
    batch_id: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=2, max_length=120)
    skill_area: str = Field(min_length=1, max_length=80)
    max_score: float = Field(default=100, gt=0, le=10000)
    assessment_date: date

    @field_validator("title", "skill_area")
    @classmethod
    def trim_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assessment_id: str
    batch_id: str
    title: str
    skill_area: str
    max_score: float
    assessment_date: date


class AssessmentSummary(AssessmentRead):
    average_score: float | None
    results_recorded: int
    learner_count: int


class ResultCreate(BaseModel):
    student_id: str = Field(min_length=1, max_length=20)
    score: float = Field(ge=0)


class ResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    result_id: str
    student_id: str
    assessment_id: str
    score: float


class ResultImportSummary(BaseModel):
    assessment_id: str
    imported_count: int
    skipped_blank_scores: int

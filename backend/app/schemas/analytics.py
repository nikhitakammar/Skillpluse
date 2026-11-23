"""Response models for descriptive analytics."""

from datetime import date

from pydantic import BaseModel


class OverviewSummary(BaseModel):
    active_learners: int
    total_batches: int
    average_score: float | None
    attendance_rate: float | None
    assignment_completion_rate: float | None


class PerformanceTrendPoint(BaseModel):
    assessment_date: date
    average_score: float


class SkillGap(BaseModel):
    skill_area: str
    average_score: float
    learners_below_benchmark: int
    benchmark: float


class BatchComparison(BaseModel):
    batch_id: str
    name: str
    active_learners: int
    average_score: float | None
    attendance_rate: float | None
    assignment_completion_rate: float | None

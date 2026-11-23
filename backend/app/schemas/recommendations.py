"""Trainer-reviewed, score-based practice recommendation responses."""

from typing import Literal

from pydantic import BaseModel


class SkillRecommendation(BaseModel):
    skill_area: str
    average_score: float
    assessment_count: int
    benchmark: float
    suggestion: str
    reason: str


class StudentRecommendations(BaseModel):
    student_id: str
    status: Literal["ready", "insufficient_data"]
    benchmark: float
    recommendations: list[SkillRecommendation]
    message: str
    notice: str

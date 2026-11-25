"""Admin-managed trainer-to-student subject access schemas."""

from pydantic import BaseModel, Field, field_validator


class TrainerStudentSubjectCreate(BaseModel):
    trainer_user_id: str = Field(min_length=1, max_length=36)
    student_id: str = Field(min_length=1, max_length=20)
    skill_area: str = Field(min_length=1, max_length=80)

    @field_validator("skill_area")
    @classmethod
    def trim_skill_area(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Subject cannot be blank")
        return cleaned


class TrainerStudentSubjectRead(BaseModel):
    scope_id: str
    trainer_user_id: str
    trainer_username: str
    student_id: str
    student_name: str
    skill_area: str

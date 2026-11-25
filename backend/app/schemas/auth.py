"""Authentication and account-management request/response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Role = Literal["admin", "trainer", "student"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=12, max_length=128)
    role: Role
    student_id: str | None = Field(default=None, min_length=1, max_length=20)
    subject: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        cleaned = value.strip().casefold()
        if not cleaned or any(not (char.isalnum() or char in "._-") for char in cleaned):
            raise ValueError("Username may contain letters, numbers, dots, underscores and hyphens")
        return cleaned

    @model_validator(mode="after")
    def validate_student_link(self):
        if self.role == "student" and not self.student_id:
            raise ValueError("Student accounts must be linked to a student record")
        if self.role != "student" and self.student_id:
            raise ValueError("Only student accounts may be linked to a student record")
        if self.role == "trainer" and not self.subject:
            raise ValueError("Trainer accounts must be assigned a subject")
        if self.role != "trainer" and self.subject:
            raise ValueError("Only trainer accounts may be assigned a subject")
        return self


class UserStatusPatch(BaseModel):
    is_active: bool


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    role: Role
    student_id: str | None
    subject: str | None = None
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserRead

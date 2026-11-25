"""Validation models for recorded training classes."""

from datetime import date

from pydantic import BaseModel, Field, HttpUrl


class RecordingCreate(BaseModel):
    batch_id: str = Field(min_length=1, max_length=20)
    skill_area: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=3, max_length=160)
    recorded_on: date
    duration_minutes: int = Field(ge=1, le=600)
    recording_url: HttpUrl
    is_published: bool = True


class RecordingRead(BaseModel):
    recording_id: str
    batch_id: str
    skill_area: str
    title: str
    recorded_on: date
    duration_minutes: int
    recording_url: str
    is_published: bool
    data_origin: str

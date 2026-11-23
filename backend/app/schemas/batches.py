"""Batch API response models."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    name: str
    program: str
    start_date: date
    end_date: date
    status: str
    data_origin: str

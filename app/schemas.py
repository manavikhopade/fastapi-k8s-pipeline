"""Pydantic request/response schemas."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CheckInCreate(BaseModel):
    date: date
    workout_type: str
    duration_minutes: int = 0
    did_cooldown: bool = False
    protein_grams: int = 0
    notes: str | None = None


class CheckInOut(CheckInCreate):
    id: int
    created_at: datetime

    # allow building this response straight from a SQLAlchemy ORM object
    model_config = ConfigDict(from_attributes=True)

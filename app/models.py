"""SQLAlchemy ORM models."""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, func

from app.database import Base


class CheckIn(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    workout_type = Column(String, nullable=False)  # cycling / badminton / strength / cardio / rest
    duration_minutes = Column(Integer, nullable=False, default=0)
    did_cooldown = Column(Boolean, nullable=False, default=False)
    protein_grams = Column(Integer, nullable=False, default=0)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

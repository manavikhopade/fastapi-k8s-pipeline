"""Database operations for check-ins."""
from datetime import date

from sqlalchemy.orm import Session

from app import models, schemas


def create_checkin(db: Session, data: schemas.CheckInCreate) -> models.CheckIn:
    obj = models.CheckIn(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_checkins(
    db: Session, start: date | None = None, end: date | None = None
) -> list[models.CheckIn]:
    query = db.query(models.CheckIn)
    if start:
        query = query.filter(models.CheckIn.date >= start)
    if end:
        query = query.filter(models.CheckIn.date <= end)
    return query.order_by(models.CheckIn.date.desc()).all()


def get_checkin(db: Session, checkin_id: int) -> models.CheckIn | None:
    return db.query(models.CheckIn).filter(models.CheckIn.id == checkin_id).first()

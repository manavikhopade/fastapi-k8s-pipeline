"""Weekly / monthly aggregation over check-ins.

Plain Python aggregation (no heavy libs). Used by the /analysis endpoints and,
later, by the scheduled CronJob.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app import models


def _summarize(rows: list[models.CheckIn]) -> dict:
    if not rows:
        return {
            "entries": 0,
            "active_days": 0,
            "total_minutes": 0,
            "avg_protein": 0,
            "cooldown_rate": 0.0,
            "by_type": {},
        }
    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r.workout_type] = by_type.get(r.workout_type, 0) + r.duration_minutes
    return {
        "entries": len(rows),
        "active_days": len({r.date for r in rows}),
        "total_minutes": sum(r.duration_minutes for r in rows),
        "avg_protein": round(sum(r.protein_grams for r in rows) / len(rows), 1),
        "cooldown_rate": round(sum(1 for r in rows if r.did_cooldown) / len(rows), 2),
        "by_type": by_type,
    }


def _rows_between(db: Session, start: date, end: date) -> list[models.CheckIn]:
    return (
        db.query(models.CheckIn)
        .filter(models.CheckIn.date >= start, models.CheckIn.date <= end)
        .all()
    )


def weekly(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    start = today - timedelta(days=today.weekday())  # Monday of this week
    end = start + timedelta(days=6)
    return {"period": "week", "start": str(start), "end": str(end), **_summarize(_rows_between(db, start, end))}


def monthly(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    start = today.replace(day=1)
    next_month = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    end = next_month - timedelta(days=1)
    return {"period": "month", "start": str(start), "end": str(end), **_summarize(_rows_between(db, start, end))}

"""FastAPI application: daily fitness check-in API.

Run locally (no Docker):
    uv sync
    uv run uvicorn app.main:app --reload
Then open http://localhost:8000/docs
"""
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import analysis, crud, schemas
from app.database import Base, engine, get_db

# Create tables on startup (fine for this project; a real app would use migrations).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FitCheck",
    description="Daily fitness check-in API with weekly/monthly analysis.",
    version="0.1.0",
)


@app.get("/health", tags=["meta"])
def health(db: Session = Depends(get_db)):
    """Liveness/readiness probe — also confirms the DB is reachable."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/checkins", response_model=schemas.CheckInOut, status_code=201, tags=["checkins"])
def create_checkin(payload: schemas.CheckInCreate, db: Session = Depends(get_db)):
    return crud.create_checkin(db, payload)


@app.get("/checkins", response_model=list[schemas.CheckInOut], tags=["checkins"])
def list_checkins(
    from_: date | None = Query(None, alias="from"),
    to: date | None = None,
    db: Session = Depends(get_db),
):
    return crud.list_checkins(db, from_, to)


@app.get("/checkins/{checkin_id}", response_model=schemas.CheckInOut, tags=["checkins"])
def get_checkin(checkin_id: int, db: Session = Depends(get_db)):
    obj = crud.get_checkin(db, checkin_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="check-in not found")
    return obj


@app.get("/analysis/weekly", tags=["analysis"])
def analysis_weekly(db: Session = Depends(get_db)):
    return analysis.weekly(db)


@app.get("/analysis/monthly", tags=["analysis"])
def analysis_monthly(db: Session = Depends(get_db)):
    return analysis.monthly(db)

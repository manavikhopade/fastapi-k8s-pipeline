"""API tests for FitCheck — pytest + FastAPI's TestClient.  Run: uv run pytest -v"""
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# --- isolated in-memory SQLite just for tests (never the real DB) ---
engine = create_engine(
    "sqlite://",                                 # in-memory database
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,                        # keep one connection so data survives across calls
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)            # build the tables in the test DB


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db   # swap the DB for tests only
client = TestClient(app)                             # fake client that calls the app directly


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_checkin():
    resp = client.post("/checkins", json={
        "date": "2026-08-18", "workout_type": "cycling",
        "duration_minutes": 45, "did_cooldown": True, "protein_grams": 80,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["workout_type"] == "cycling"
    assert body["id"] > 0                 # the DB assigned an id
    assert "created_at" in body


def test_list_checkins():
    resp = client.get("/checkins")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1          # includes the one created above


def test_get_missing_checkin_returns_404():
    resp = client.get("/checkins/99999")
    assert resp.status_code == 404


def test_weekly_analysis():
    today = date.today().isoformat()
    client.post("/checkins", json={
        "date": today, "workout_type": "badminton",
        "duration_minutes": 60, "did_cooldown": False, "protein_grams": 70,
    })
    resp = client.get("/analysis/weekly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "week"
    assert data["entries"] >= 1
    assert data["total_minutes"] >= 60

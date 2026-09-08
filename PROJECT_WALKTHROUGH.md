# Phase 1: Building the FastAPI Application

## Overview

**Goal:** Build a REST API that accepts daily fitness check-ins and provides weekly/monthly analysis.

**Outcome:** A working FastAPI application that stores check-ins in SQLite and returns aggregated stats.

**Time:** ~2 hours (including testing)

---

## What We Built

A **fitness check-in REST API** with these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Liveness probe (is the app running?) |
| `/checkins` | POST | Create a new check-in |
| `/checkins` | GET | List all check-ins (with optional date filter) |
| `/checkins/{id}` | GET | Get a specific check-in |
| `/analysis/weekly` | GET | Weekly aggregation (total minutes, avg protein, etc.) |
| `/analysis/monthly` | GET | Monthly aggregation |

### Example: Creating a Check-In

```bash
curl -X POST http://localhost:8000/checkins \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-09-09",
    "workout_type": "cycling",
    "duration_minutes": 60,
    "did_cooldown": true,
    "protein_grams": 90,
    "notes": "morning ride"
  }'

# Response (201 Created):
{
  "id": 1,
  "date": "2026-09-09",
  "workout_type": "cycling",
  "duration_minutes": 60,
  "did_cooldown": true,
  "protein_grams": 90,
  "notes": "morning ride",
  "created_at": "2026-09-08T22:42:12.364595Z"
}
```

### Example: Weekly Analysis

```bash
curl http://localhost:8000/analysis/weekly

# Response:
{
  "period": "week",
  "start": "2026-09-07",
  "end": "2026-09-13",
  "entries": 3,
  "active_days": 2,
  "total_minutes": 165,
  "avg_protein": 88.3,
  "cooldown_rate": 1.0,
  "by_type": {
    "cycling": 120,
    "strength": 45
  }
}
```

---

## What is FastAPI?

### Definition

FastAPI is a **modern Python web framework** for building REST APIs quickly.

### Key Characteristics

| Feature | Explanation |
|---------|-------------|
| **Modern** | Uses Python 3.6+ async/await syntax |
| **Fast** | Async means concurrent requests; auto-docs generation saves time |
| **Easy** | Minimal boilerplate; intuitive routing |
| **Type hints** | Uses Python type hints for validation (e.g., `duration_minutes: int`) |
| **Auto docs** | Generates Swagger UI at `/docs` automatically |

### The Stack

```
Browser/Client
    ↓ (HTTP request)
    ↓
uvicorn (web server)
    ↓ (receives request, passes to app)
    ↓
FastAPI app (your routes)
    ↓ (processes, queries database)
    ↓
SQLAlchemy (ORM)
    ↓ (translates Python to SQL)
    ↓
SQLite (database)
    ↓ (stores data in fitcheck.db file)
```

### How FastAPI Handles a Request

```python
@app.post("/checkins", response_model=schemas.CheckInOut, status_code=201)
def create_checkin(payload: schemas.CheckInCreate, db: Session = Depends(get_db)):
    return crud.create_checkin(db, payload)
```

**Breakdown:**
- `@app.post(...)` — "Listen for POST requests to /checkins"
- `payload: schemas.CheckInCreate` — "Validate incoming JSON against this schema"
- `db: Session = Depends(get_db)` — "Inject a database session (dependency injection)"
- `return crud.create_checkin(...)` — "Call the CRUD function to save it"

FastAPI automatically:
1. ✅ Validates the JSON against `schemas.CheckInCreate`
2. ✅ Returns 400 if validation fails
3. ✅ Returns 201 on success
4. ✅ Generates Swagger docs from this endpoint

---

## What is SQLite?

### Definition

SQLite is a **lightweight, file-based SQL database** — no server needed.

### Key Characteristics

| Feature | Explanation |
|---------|-------------|
| **File-based** | Data stored in one file (`fitcheck.db`) |
| **Embedded** | No separate server process |
| **Zero setup** | Works out of the box; Python has it built-in |
| **For local dev** | Perfect for development; not for production (single file, concurrent access issues) |

### SQLite vs PostgreSQL

| Aspect | SQLite | PostgreSQL |
|--------|--------|-----------|
| Setup | None | Needs server (or Docker) |
| File size | Small (one file) | Larger (full database) |
| Concurrency | Poor (file-based locks) | Excellent (server-based) |
| Use case | Local dev, testing | Production, multi-user |
| In Docker | Risky (data on container filesystem) | Safe (data on volume) |

### How We Used SQLite in Phase 1

```python
# app/database.py
DATABASE_URL = "sqlite:///./fitcheck.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite-specific config
)
```

**Result:** When you run the app, a file `fitcheck.db` is created in the project root with all tables.

**In Phase 2b, we upgraded to PostgreSQL** because Docker containers need persistent storage (volumes), and SQLite doesn't handle that well.

---

## Technology Stack (Phase 1)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI | Web framework |
| **Web Server** | uvicorn | Runs the FastAPI app |
| **ORM** | SQLAlchemy | Python ↔ Database translator |
| **Database** | SQLite | Data storage |
| **Validation** | Pydantic | JSON schema validation |
| **Testing** | pytest | Unit tests |
| **Dependency Mgmt** | uv | Python package manager (like npm) |

### Why These Choices?

- **FastAPI:** Industry standard for Python APIs; minimal code; built-in validation
- **SQLAlchemy:** Database-agnostic (switch SQLite → PostgreSQL without app code changes)
- **Pydantic:** Automatic JSON validation; generates API docs
- **pytest:** Standard Python testing; integrates with FastAPI's `TestClient`
- **uv:** Fast, modern Python package manager (faster than pip)

---

## File Structure (Phase 1)

```
app/
├── __init__.py           # Makes 'app' a Python package
├── main.py               # Route handlers (@app.get, @app.post)
├── models.py             # SQLAlchemy ORM models (database tables)
├── schemas.py            # Pydantic models (JSON validation)
├── database.py           # SQLAlchemy setup (engine, session)
├── crud.py               # Create, Read, Update, Delete functions
└── analysis.py           # Weekly/monthly aggregation logic

tests/
└── test_api.py           # API endpoint tests

pyproject.toml            # Dependencies (like package.json)
uv.lock                   # Locked versions (like package-lock.json)
fitcheck.db              # SQLite database file (created at runtime)
```

### Job of Each File

| File | Job | Example |
|------|-----|---------|
| `main.py` | **Waiter** — receives requests, routes them | `@app.post("/checkins")` defines the endpoint |
| `schemas.py` | **Order form** — validates request/response structure | `CheckInCreate` defines what fields are required |
| `models.py` | **Table blueprint** — defines database schema | `CheckIn` model has columns: id, date, workout_type, etc. |
| `database.py` | **Connection pool** — manages database connection | Creates SQLAlchemy engine and session |
| `crud.py` | **Kitchen** — the only file that touches the database | `create_checkin(db, payload)` does the INSERT |
| `analysis.py` | **Accountant** — calculates stats | `weekly(db)` does GROUP BY and SUM |

---

## Commands Used in Phase 1

### Setup

```bash
# Install dependencies
uv sync

# This creates a .venv folder with all packages
```

**What it does:** Reads `pyproject.toml`, downloads packages, creates `.venv/lib/python3.12/site-packages/`

---

### Running the App Locally

```bash
uv run uvicorn app.main:app --reload
```

**Breakdown:**
- `uv run` — "Use packages from this project"
- `uvicorn` — The web server
- `app.main:app` — "In file `app/main.py`, find the variable `app`"
- `--reload` — "Restart when code changes" (dev only)

**Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Access the app:**
- API: http://localhost:8000/checkins
- Auto-docs: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc

---

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=app
```

**Output:**
```
tests/test_api.py::test_create_checkin PASSED
tests/test_api.py::test_list_checkins PASSED
tests/test_api.py::test_analysis_weekly PASSED
========== 5 passed in 2.51s ==========
```

**What's being tested:**
- ✅ Can create a check-in (POST /checkins)
- ✅ Can list check-ins (GET /checkins)
- ✅ Can get weekly analysis (GET /analysis/weekly)
- ✅ Health check works (GET /health)
- ✅ Data persists (create → query → verify)

---

### Adding Dependencies

```bash
# Add a new package
uv add psycopg2-binary

# This updates pyproject.toml and uv.lock
```

**Why uv add instead of pip install?**
- Creates lockfile (reproducible environments)
- Works like `npm install` (familiar pattern)

---

## How SQLAlchemy Works (Brief Overview)

### The Problem It Solves

You need to write SQL queries, but SQL is string-based and error-prone:

```sql
-- Raw SQL (risky: string manipulation, SQL injection)
INSERT INTO checkins (date, workout_type, duration_minutes) 
VALUES ('2026-09-09', 'cycling', 60);
```

### The SQLAlchemy Solution

```python
# Python ORM (safe: type-checked, auto-escaped)
db.add(CheckIn(date="2026-09-09", workout_type="cycling", duration_minutes=60))
db.commit()
```

**SQLAlchemy translates Python → SQL automatically.**

### The Three Layers

```
Your Python code
    ↓
SQLAlchemy ORM (app/models.py)
    ↓ (translates Python objects to SQL)
    ↓
SQL database (SQLite in Phase 1)
```

**Example:**

```python
# Python (what you write)
checkins = db.query(CheckIn).filter(CheckIn.date == "2026-09-09").all()

# SQLAlchemy translates to:
SELECT * FROM checkins WHERE date = '2026-09-09';

# Database executes, returns rows
# SQLAlchemy converts rows back to Python objects
```

---

## Key Concepts (Interview Prep)

### 1. REST API

**REST = Representational State Transfer**

```
GET /checkins               → Retrieve all check-ins
GET /checkins/1             → Retrieve check-in with ID 1
POST /checkins              → Create a new check-in
PUT /checkins/1             → Update check-in 1
DELETE /checkins/1          → Delete check-in 1
```

**Key principle:** Use HTTP methods (GET, POST, PUT, DELETE) to express intent.

### 2. Status Codes

```
200 OK                      → Request succeeded
201 Created                 → Resource created successfully
400 Bad Request             → Invalid input (validation failed)
404 Not Found               → Resource doesn't exist
500 Internal Server Error   → Server error
```

### 3. Request/Response Format

```
Request:
POST /checkins HTTP/1.1
Content-Type: application/json

{
  "date": "2026-09-09",
  "workout_type": "cycling",
  ...
}

Response:
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": 1,
  "date": "2026-09-09",
  ...
}
```

### 4. Validation with Pydantic

```python
# This schema validates the request
class CheckInCreate(BaseModel):
    date: date              # Must be a date
    workout_type: str       # Must be a string
    duration_minutes: int   # Must be an integer
    did_cooldown: bool      # Must be a boolean
    protein_grams: int      # Must be an integer
    notes: Optional[str]    # Optional string

# If someone sends:
{
  "date": "not-a-date",  # ❌ Invalid
  "workout_type": "cycling",
  ...
}

# Pydantic rejects it: "date must be a valid date"
# FastAPI returns 400 Bad Request
```

---

## Phase 1 Checklist (What We Completed)

- ✅ Defined database schema (models.py)
- ✅ Built API endpoints (main.py)
- ✅ Implemented validation (schemas.py)
- ✅ Wrote CRUD operations (crud.py)
- ✅ Implemented analysis logic (analysis.py)
- ✅ Wrote unit tests (tests/test_api.py)
- ✅ App runs locally: `uv run uvicorn app.main:app --reload`
- ✅ All tests pass: `uv run pytest tests/ -v`
- ✅ API docs available at `/docs`

---

## Next: Phase 2 (Containerization)

Phase 1 works locally. But:
- ❌ Only works on your machine
- ❌ Requires Python 3.12 installed
- ❌ Database is a local file

**Phase 2 solves this:** Package the app in a Docker container so it runs identically anywhere (laptop, Codespaces, Kubernetes, cloud).

---

## Interview Question: Explain Phase 1

**Typical question:** "Walk me through how your fitness app works."

**Good answer:**
> "Phase 1 is the core application. We built a FastAPI REST API that accepts POST requests to create fitness check-ins. Each check-in is validated with Pydantic schemas, stored in SQLite via SQLAlchemy ORM, and retrieved with GET endpoints. The app also provides aggregated analysis endpoints (weekly/monthly) that use SQL GROUP BY to calculate stats like total workout minutes and average protein intake. We tested it with pytest and ran it locally with uvicorn."

---

## Revision Checklist

Before moving to Phase 2, you should be able to answer:

- [ ] What is FastAPI? (Python web framework, modern, type-checked)
- [ ] What is SQLite? (File-based database, good for dev, not production)
- [ ] What does SQLAlchemy do? (Translates Python objects to SQL)
- [ ] What is Pydantic? (Validates JSON, generates docs)
- [ ] What are the 6 main files and their jobs?
- [ ] How do you run the app? (`uv run uvicorn app.main:app --reload`)
- [ ] How do you run tests? (`uv run pytest tests/ -v`)
- [ ] How do you access the API docs? (http://localhost:8000/docs)
- [ ] What status codes do we use? (201 for created, 400 for validation error, etc.)
- [ ] Why SQLite in Phase 1? (Zero setup, good for local dev)

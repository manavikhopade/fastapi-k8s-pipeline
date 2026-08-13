"""Database engine + session setup.

Reads the connection string from the DATABASE_URL env var. Defaults to a local
SQLite file so the app runs with zero setup (no Docker/Postgres needed). In
Docker Compose / Kubernetes, DATABASE_URL is set to a PostgreSQL URL instead —
the rest of the code is identical.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fitcheck.db")

# SQLite needs this flag when used with FastAPI's threaded server; Postgres does not.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

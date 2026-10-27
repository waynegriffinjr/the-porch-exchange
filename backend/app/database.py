# /app/database.py
# Module 5 Project — Database setup
#
import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./needs.db")


def migrate_legacy_tasks_storage() -> None:
    """One-time upgrade: reuse a legacy taskmanager.db and rename its tasks table to needs."""
    if DATABASE_URL.startswith("sqlite:///"):
        new_path = Path(DATABASE_URL.removeprefix("sqlite:///"))
        old_path = new_path.with_name("taskmanager.db")
        if not new_path.exists() and old_path.exists():
            old_path.rename(new_path)


migrate_legacy_tasks_storage()

# Creates a SQLAlchemy engine for the database connection
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=True,  # Set to True for SQL query logging
)

# Creates a SQLAlchemy engine for the database connection
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base shared by all SQLAlchemy models."""

    pass


def rename_legacy_tasks_table() -> None:
    """Rename a pre-existing `tasks` table to `needs`, keeping its rows."""
    tables = inspect(engine).get_table_names()
    if "tasks" in tables and "needs" not in tables:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE tasks RENAME TO needs"))


def get_db() -> Generator[Session, None, None]:
    """Provides a DB session per request lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

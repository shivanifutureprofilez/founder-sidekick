import os
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Convert legacy postgres:// URI to postgresql:// for SQLAlchemy compatibility
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass

if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not set. Cannot establish database session.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> dict:
    """
    Safely check database connectivity.
    Returns status dict without exposing sensitive credentials.
    """
    if not DATABASE_URL or engine is None:
        return {"connected": False, "error": "DATABASE_URL environment variable is not set"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"connected": True, "error": None}
    except Exception as e:
        return {"connected": False, "error": f"Database connection failed: {type(e).__name__}"}

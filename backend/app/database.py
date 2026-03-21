"""
Database Configuration and Session Management
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from contextlib import contextmanager

from app.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,  # Disable SQL query logging
    pool_pre_ping=True,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
# Using custom naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Ensures session is closed after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database session.
    Useful for background tasks or scripts.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    from app.models import (  # noqa: F401
        base, user, role, business, branch, waybill, pickup, dropoff,
        warehouse, dispatch, delivery, tracking, product, inventory,
        vendor, agent, order, lead, accounting, notification, audit
    )
    Base.metadata.create_all(bind=engine)


def reset_db():
    """Reset database - drop and recreate all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    init_db()

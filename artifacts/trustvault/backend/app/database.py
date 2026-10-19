"""Database engine and request-scoped SQLAlchemy sessions."""

from functools import lru_cache
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import sqlalchemy_database_url


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        sqlalchemy_database_url(),
        pool_pre_ping=True,
    )


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        autoflush=False,
    )


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()

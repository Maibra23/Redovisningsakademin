"""Database engine and sessions.

The address comes from DATABASE_URL: first the environment, then Streamlit
secrets, else a local SQLite file. Tables are created with create_all when
the engine is first built.
"""

import os
from functools import lru_cache

import streamlit as st
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ra.paths import repo_root
from ra.storage.models import Base

URL_KEY = "DATABASE_URL"
LOCAL_DB_NAME = "ra_local.db"
POSTGRES_DRIVER_PREFIX = "postgresql+psycopg://"
PLAIN_POSTGRES_PREFIXES = ("postgresql://", "postgres://")
POOL_SIZE = 2
POOL_MAX_OVERFLOW = 2
POOL_RECYCLE_SECONDS = 300


def database_url() -> str:
    """The configured address, or the local SQLite file when none is set."""
    url = os.environ.get(URL_KEY)
    if not url:
        try:
            url = st.secrets.get(URL_KEY)
        except FileNotFoundError:
            url = None
    return normalise_url(url) if url else f"sqlite:///{repo_root() / LOCAL_DB_NAME}"


def normalise_url(url: str) -> str:
    """Point a plain PostgreSQL address (as Supabase shows it) at the psycopg driver."""
    for prefix in PLAIN_POSTGRES_PREFIXES:
        if url.startswith(prefix):
            return POSTGRES_DRIVER_PREFIX + url.removeprefix(prefix)
    return url


def _build_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        return create_engine(url)
    # Supabase's transaction pooler cannot keep prepared statements between
    # transactions, so psycopg must not prepare them (prepare_threshold=None).
    return create_engine(
        url,
        pool_size=POOL_SIZE,
        max_overflow=POOL_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=POOL_RECYCLE_SECONDS,
        connect_args={"prepare_threshold": None},
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """One engine per process; creates missing tables on first use."""
    engine = _build_engine(database_url())
    Base.metadata.create_all(engine)
    return engine


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(get_engine(), expire_on_commit=False)


def new_session() -> Session:
    """A new session; use as ``with new_session() as s, s.begin(): ...``."""
    return _session_factory()()

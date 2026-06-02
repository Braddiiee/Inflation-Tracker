"""
Connection management and database initialization.

Creates the SQLite engine, enables foreign keys, builds schema + indexes,
and provides a session context manager with automatic commit/rollback.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.exceptions import DatabaseError
from src.models import Base, Category, PriceLog, Product, Store

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "tracker.db"

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_database_url(db_path: Path | None = None) -> str:
    """Build a SQLite URL for the given file path (defaults to data/tracker.db)."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.resolve().as_posix()}"


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    """SQLite requires PRAGMA foreign_keys=ON per connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine(db_path: Path | None = None, *, echo: bool = False) -> Engine:
    """
    Return a singleton SQLAlchemy engine for the app.
    Re-uses the same engine after first call unless reset_engine() is used (tests).
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(db_path),
            echo=echo,
            future=True,
        )
        event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
    return _engine


def get_session_factory(db_path: Path | None = None) -> sessionmaker[Session]:
    """Return a sessionmaker bound to the shared engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(db_path),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def reset_engine() -> None:
    """Dispose engine and session factory (for tests or path changes)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def get_session(db_path: Path | None = None) -> Generator[Session, None, None]:
    """
    Context manager yielding a SQLAlchemy Session.

    Commits on success, rolls back on any exception, always closes the session.
    """
    session = get_session_factory(db_path)()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Database transaction failed")
        raise DatabaseError(str(exc)) from exc
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(db_path: Path | None = None, *, drop_existing: bool = False) -> None:
    """
    Create all tables and indexes defined on ORM models.

    If drop_existing is True, drops every table first (destructive; for dev/tests only).
    """
    engine = get_engine(db_path)
    try:
        if drop_existing:
            Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        _apply_migrations(engine)
        logger.info("Database initialized at %s", db_path or DEFAULT_DB_PATH)
    except SQLAlchemyError as exc:
        raise DatabaseError(f"Failed to initialize database: {exc}") from exc


def _apply_migrations(engine: Engine) -> None:
    """Add columns introduced after initial deploy (safe for existing SQLite files)."""
    inspector = inspect(engine)
    if not inspector.has_table("price_logs"):
        return
    columns = {col["name"] for col in inspector.get_columns("price_logs")}
    if "notes" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE price_logs ADD COLUMN notes TEXT"))


def seed_sample_data(db_path: Path | None = None) -> None:
    """
    Insert demo rows illustrating shrinkflation (1 kg vs 0.5 kg rice).

    Safe to call once after init_db; skips if price_logs already has rows.
    """
    with get_session(db_path) as session:
        if session.query(PriceLog).count() > 0:
            return

        staples = Category(category_name="Staples")
        session.add(staples)
        session.flush()

        rice = Product(product_name="Rice (Parboiled)", category_id=staples.category_id)
        store = Store(store_name="Local Market A")
        session.add_all([rice, store])
        session.flush()

        session.add_all(
            [
                PriceLog(
                    product_id=rice.product_id,
                    store_id=store.store_id,
                    price_total=500.0,
                    quantity=1.0,
                    unit_type="kg",
                    date_recorded="2026-05-01",
                ),
                PriceLog(
                    product_id=rice.product_id,
                    store_id=store.store_id,
                    price_total=280.0,
                    quantity=0.5,
                    unit_type="kg",
                    date_recorded="2026-05-08",
                ),
            ]
        )


def health_check(db_path: Path | None = None) -> bool:
    """Return True if the database file is reachable and responds to SELECT 1."""
    try:
        engine = get_engine(db_path)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False

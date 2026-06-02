"""
Data Access Layer facade.

Re-exports connection helpers, initialization, and repository classes so the UI
and analytics layers import from a single module without touching SQL directly.
"""

from src.database import (
    DEFAULT_DB_PATH,
    get_database_url,
    get_engine,
    get_session,
    health_check,
    init_db,
    reset_engine,
    seed_sample_data,
)
from src.exceptions import DatabaseError, NotFoundError, ValidationError
from src.repositories import (
    CategoryRepository,
    PriceLogRepository,
    ProductRepository,
    StoreRepository,
)

__all__ = [
    "DEFAULT_DB_PATH",
    "CategoryRepository",
    "DatabaseError",
    "NotFoundError",
    "PriceLogRepository",
    "ProductRepository",
    "StoreRepository",
    "ValidationError",
    "get_database_url",
    "get_engine",
    "get_session",
    "health_check",
    "init_db",
    "reset_engine",
    "seed_sample_data",
]

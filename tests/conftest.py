"""
Shared pytest fixtures for the Grocery Inflation Tracker test suite.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.database import init_db, reset_engine
from src.data_processor import records_to_dataframe
from src.entry_service import PriceEntryInput, save_price_entry
from src.record_service import PriceRecordRow


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Empty initialized SQLite database (isolated per test)."""
    path = tmp_path / "tracker_test.db"
    reset_engine()
    init_db(path)
    yield path
    reset_engine()


@pytest.fixture
def populated_db(db_path: Path) -> Path:
    """Database with a small multi-item basket for analytics and records tests."""
    entries = [
        PriceEntryInput(
            item_name="Rice (Parboiled)",
            store_name="Local Market A",
            category_name="Staples",
            price_total=500,
            date_recorded=date(2026, 5, 1),
            quantity=1,
            unit_type="kg",
        ),
        PriceEntryInput(
            item_name="Rice (Parboiled)",
            store_name="Local Market A",
            category_name="Staples",
            price_total=280,
            date_recorded=date(2026, 5, 8),
            quantity=0.5,
            unit_type="kg",
        ),
        PriceEntryInput(
            item_name="Milk",
            store_name="Shop B",
            category_name="Dairy",
            price_total=10,
            date_recorded=date(2026, 5, 5),
            quantity=1,
            unit_type="l",
        ),
        PriceEntryInput(
            item_name="Milk",
            store_name="Shop B",
            category_name="Dairy",
            price_total=12,
            date_recorded=date(2026, 5, 20),
            quantity=1,
            unit_type="l",
        ),
    ]
    for entry in entries:
        save_price_entry(entry, db_path=db_path)
    return db_path


def make_row(
    log_id: int,
    item: str,
    store: str,
    category: str,
    price_total: float,
    quantity: float,
    unit: str,
    dt: str,
    notes: str | None = None,
) -> PriceRecordRow:
    """Factory for in-memory PriceRecordRow instances."""
    return PriceRecordRow(
        log_id=log_id,
        item_name=item,
        store_name=store,
        category_name=category,
        price_total=price_total,
        quantity=quantity,
        unit_type=unit,
        date_recorded=dt,
        notes=notes,
        unit_price=price_total / quantity,
    )


@pytest.fixture
def sample_analytics_df() -> pd.DataFrame:
    """DataFrame matching populated_db shrinkflation + milk trend."""
    rows = [
        make_row(1, "Rice", "Market A", "Staples", 500, 1, "kg", "2026-05-01"),
        make_row(2, "Rice", "Market A", "Staples", 280, 0.5, "kg", "2026-05-08"),
        make_row(3, "Milk", "Shop B", "Dairy", 10, 1, "l", "2026-05-05"),
        make_row(4, "Milk", "Shop B", "Dairy", 12, 1, "l", "2026-05-20"),
        make_row(5, "Bread", "Shop B", "Bakery", 50, 1, "unit", "2026-05-01"),
        make_row(6, "Bread", "Shop B", "Bakery", 46, 1, "unit", "2026-05-25"),
    ]
    return records_to_dataframe(rows)

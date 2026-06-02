"""Tests for record list, search, sort, pagination, update, and delete."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.database import init_db, reset_engine
from src.entry_service import PriceEntryInput, save_price_entry
from src.exceptions import NotFoundError
from src.record_service import (
    delete_record,
    get_record,
    list_records,
    update_record,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "records.db"
    reset_engine()
    init_db(path)
    yield path
    reset_engine()


def _seed(db_path: Path) -> None:
    save_price_entry(
        PriceEntryInput(
            item_name="Rice",
            store_name="Market A",
            category_name="Staples",
            price_total=500,
            date_recorded=date(2026, 5, 1),
            quantity=1,
            unit_type="kg",
        ),
        db_path=db_path,
    )
    save_price_entry(
        PriceEntryInput(
            item_name="Milk",
            store_name="Shop B",
            category_name="Dairy",
            price_total=12,
            date_recorded=date(2026, 5, 10),
            notes="organic",
            quantity=1,
            unit_type="l",
        ),
        db_path=db_path,
    )


def test_search_filters_rows(db_path: Path) -> None:
    _seed(db_path)
    result = list_records(search="milk", db_path=db_path)
    assert result.total == 1
    assert result.rows[0].item_name == "Milk"


def test_sort_by_price(db_path: Path) -> None:
    _seed(db_path)
    result = list_records(sort_by="price_total", sort_order="asc", db_path=db_path)
    assert result.rows[0].price_total < result.rows[1].price_total


def test_pagination(db_path: Path) -> None:
    _seed(db_path)
    all_rows = list_records(page=1, page_size=50, db_path=db_path)
    assert all_rows.total >= 2, "seed should insert at least two records"

    page1 = list_records(page=1, page_size=1, db_path=db_path)
    page2 = list_records(page=2, page_size=1, db_path=db_path)
    assert page1.total == all_rows.total
    assert len(page1.rows) == 1
    assert len(page2.rows) == 1
    assert page1.rows[0].log_id != page2.rows[0].log_id


def test_update_record(db_path: Path) -> None:
    _seed(db_path)
    first = list_records(db_path=db_path).rows[0]
    updated = update_record(
        first.log_id,
        PriceEntryInput(
            item_name=first.item_name,
            store_name=first.store_name,
            category_name=first.category_name,
            price_total=99.0,
            date_recorded=first.date_recorded,
            quantity=first.quantity,
            unit_type=first.unit_type,
        ),
        db_path=db_path,
    )
    assert updated.price_total == 99.0


def test_delete_record(db_path: Path) -> None:
    _seed(db_path)
    log_id = list_records(db_path=db_path).rows[0].log_id
    delete_record(log_id, db_path=db_path)
    with pytest.raises(NotFoundError):
        get_record(log_id, db_path=db_path)

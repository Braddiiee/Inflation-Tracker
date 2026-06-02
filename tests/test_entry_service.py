"""Tests for Add Price Entry business logic."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.database import get_session, init_db, reset_engine
from src.entry_service import (
    PriceEntryInput,
    list_category_names,
    save_price_entry,
    validate_entry_form,
)
from src.exceptions import ValidationError
from src.repositories import PriceLogRepository


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "entry.db"
    reset_engine()
    init_db(path)
    yield path
    reset_engine()


def test_validate_rejects_empty_item(db_path: Path) -> None:
    errors = validate_entry_form(
        PriceEntryInput(
            item_name="  ",
            store_name="Shop",
            category_name="Staples",
            price_total=10,
            date_recorded=date(2026, 5, 1),
        )
    )
    assert "item_name" in errors


def test_save_with_notes(db_path: Path) -> None:
    result = save_price_entry(
        PriceEntryInput(
            item_name="Milk",
            store_name="Shop A",
            category_name="Dairy",
            price_total=12.5,
            date_recorded=date(2026, 5, 15),
            notes="  On sale  ",
            quantity=1,
            unit_type="l",
        ),
        db_path=db_path,
    )
    assert result.log_id > 0

    with get_session(db_path) as session:
        log = PriceLogRepository(session).get_by_id(result.log_id)
    assert log.notes == "On sale"


def test_save_rejects_duplicate_category_mismatch(db_path: Path) -> None:
    save_price_entry(
        PriceEntryInput(
            item_name="Bread",
            store_name="Shop",
            category_name="Bakery",
            price_total=5,
            date_recorded=date(2026, 5, 1),
        ),
        db_path=db_path,
    )
    with pytest.raises(ValidationError):
        save_price_entry(
            PriceEntryInput(
                item_name="Bread",
                store_name="Shop",
                category_name="Snacks",
                price_total=6,
                date_recorded=date(2026, 5, 2),
            ),
            db_path=db_path,
        )


def test_list_categories_after_save(db_path: Path) -> None:
    save_price_entry(
        PriceEntryInput(
            item_name="Eggs",
            store_name="Market",
            category_name="Dairy",
            price_total=8,
            date_recorded=date(2026, 5, 1),
        ),
        db_path=db_path,
    )
    assert "Dairy" in list_category_names(db_path)

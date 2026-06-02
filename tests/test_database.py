"""Tests for database initialization, validation, and repository CRUD."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.integration]

from src.database import get_session, init_db, reset_engine, seed_sample_data
from src.exceptions import NotFoundError, ValidationError
from src.repositories import (
    CategoryRepository,
    PriceLogRepository,
    ProductRepository,
    StoreRepository,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    reset_engine()
    init_db(path)
    yield path
    reset_engine()


def test_init_and_seed(db_path: Path) -> None:
    seed_sample_data(db_path)
    with get_session(db_path) as session:
        logs = PriceLogRepository(session).list_all()
    assert len(logs) == 2
    assert logs[0].price_total / logs[0].quantity == pytest.approx(560.0)


def test_reject_negative_price(db_path: Path) -> None:
    with get_session(db_path) as session:
        cat = CategoryRepository(session).create("Dairy")
        prod = ProductRepository(session).create("Milk", cat.category_id)
        store = StoreRepository(session).create("Shop B")
        with pytest.raises(ValidationError):
            PriceLogRepository(session).create(
                prod.product_id,
                store.store_id,
                price_total=-1,
                quantity=1,
                unit_type="l",
                date_recorded="2026-05-01",
            )


def test_reject_future_date(db_path: Path) -> None:
    future = (date.today() + timedelta(days=1)).isoformat()
    with get_session(db_path) as session:
        cat = CategoryRepository(session).create("Snacks")
        prod = ProductRepository(session).create("Chips", cat.category_id)
        store = StoreRepository(session).create("Shop C")
        with pytest.raises(ValidationError):
            PriceLogRepository(session).create(
                prod.product_id,
                store.store_id,
                price_total=10,
                quantity=1,
                unit_type="unit",
                date_recorded=future,
            )


def test_unique_product_name(db_path) -> None:
    with get_session(db_path) as session:
        cat = CategoryRepository(session).create("Staples")
        ProductRepository(session).create("Rice", cat.category_id)

    with pytest.raises(ValidationError):
        with get_session(db_path) as session:
            cat = CategoryRepository(session).get_by_name("Staples")
            assert cat is not None
            ProductRepository(session).create("Rice", cat.category_id)


def test_insert_price_record_by_name(db_path: Path) -> None:
    with get_session(db_path) as session:
        log = PriceLogRepository(session).insert_price_record(
            product_name="Bread",
            category_name="Bakery",
            store_name="Market X",
            price_total=120,
            quantity=1,
            unit_type="unit",
            date_recorded="2026-05-10",
        )
        assert log.log_id is not None


def test_delete_not_found(db_path: Path) -> None:
    with get_session(db_path) as session:
        with pytest.raises(NotFoundError):
            CategoryRepository(session).get_by_id(9999)

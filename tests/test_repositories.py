"""Unit tests — repository layer (src/repositories.py)."""

from __future__ import annotations

from datetime import date

import pytest

from src.database import get_session
from src.exceptions import NotFoundError, ValidationError
from src.repositories import (
    CategoryRepository,
    PriceLogRepository,
    ProductRepository,
    StoreRepository,
)

pytestmark = pytest.mark.unit


class TestCategoryRepository:
    def test_create_and_list(self, db_path) -> None:
        with get_session(db_path) as session:
            repo = CategoryRepository(session)
            repo.create("Staples")
            names = [c.category_name for c in repo.list_all()]
        assert "Staples" in names

    def test_get_or_create_idempotent(self, db_path) -> None:
        with get_session(db_path) as session:
            repo = CategoryRepository(session)
            a = repo.get_or_create("Dairy")
            b = repo.get_or_create("Dairy")
        assert a.category_id == b.category_id


class TestProductRepository:
    def test_requires_valid_category(self, db_path) -> None:
        with get_session(db_path) as session:
            with pytest.raises(NotFoundError):
                ProductRepository(session).create("Ghost", category_id=9999)


class TestPriceLogRepository:
    def test_list_enriched_loads_relations(self, db_path) -> None:
        with get_session(db_path) as session:
            PriceLogRepository(session).insert_price_record(
                product_name="Tea",
                category_name="Beverages",
                store_name="Mart",
                price_total=5,
                quantity=1,
                unit_type="unit",
                date_recorded=date(2026, 5, 1),
            )
            logs = PriceLogRepository(session).list_enriched()
        assert len(logs) == 1
        assert logs[0].product.category.category_name == "Beverages"

    def test_update_price_record(self, db_path) -> None:
        with get_session(db_path) as session:
            repo = PriceLogRepository(session)
            log = repo.insert_price_record(
                product_name="Sugar",
                category_name="Staples",
                store_name="Mart",
                price_total=20,
                quantity=1,
                unit_type="kg",
                date_recorded=date(2026, 5, 1),
            )
            updated = repo.update_price_record(
                log.log_id,
                product_name="Sugar",
                category_name="Staples",
                store_name="Mart",
                price_total=22,
                quantity=1,
                unit_type="kg",
                date_recorded=date(2026, 5, 10),
            )
        assert updated.price_total == 22

    def test_delete_removes_log(self, db_path) -> None:
        with get_session(db_path) as session:
            repo = PriceLogRepository(session)
            log = repo.insert_price_record(
                product_name="Salt",
                category_name="Staples",
                store_name="Mart",
                price_total=3,
                quantity=1,
                unit_type="unit",
                date_recorded=date(2026, 5, 1),
            )
            repo.delete(log.log_id)
            with pytest.raises(NotFoundError):
                repo.get_by_id(log.log_id)

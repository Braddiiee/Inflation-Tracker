"""Tests for dashboard KPI calculations."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_processor import (
    basket_cost_change,
    compute_dashboard_metrics,
    records_to_dataframe,
)
from src.record_service import PriceRecordRow


def _row(
    log_id: int,
    item: str,
    store: str,
    category: str,
    price_total: float,
    quantity: float,
    unit: str,
    dt: str,
) -> PriceRecordRow:
    return PriceRecordRow(
        log_id=log_id,
        item_name=item,
        store_name=store,
        category_name=category,
        price_total=price_total,
        quantity=quantity,
        unit_type=unit,
        date_recorded=dt,
        notes=None,
        unit_price=price_total / quantity,
    )


@pytest.fixture
def dashboard_df() -> pd.DataFrame:
    rows = [
        _row(1, "Rice", "Market A", "Staples", 100, 1, "kg", "2026-05-01"),
        _row(2, "Milk", "Market A", "Dairy", 50, 1, "l", "2026-05-01"),
        _row(3, "Rice", "Market A", "Staples", 110, 1, "kg", "2026-05-20"),
        _row(4, "Milk", "Market A", "Dairy", 55, 1, "l", "2026-05-20"),
        _row(5, "Bread", "Market A", "Bakery", 40, 1, "unit", "2026-05-25"),
    ]
    return records_to_dataframe(rows)


def test_current_basket_cost(dashboard_df: pd.DataFrame) -> None:
    metrics = compute_dashboard_metrics(dashboard_df)
    assert metrics.current_basket_cost == pytest.approx(205.0)  # 110+55+40


def test_highest_and_lowest_items(dashboard_df: pd.DataFrame) -> None:
    metrics = compute_dashboard_metrics(dashboard_df)
    assert metrics.highest_inflation_item is not None
    assert metrics.highest_inflation_item.item_name == "Rice"
    assert metrics.highest_inflation_item.percentage_change == pytest.approx(10.0)


def test_weekly_change_structure(dashboard_df: pd.DataFrame) -> None:
    ref = dashboard_df["date_recorded"].max()
    change = basket_cost_change(dashboard_df, days=7, reference_date=ref)
    assert change.current_cost is not None

"""
Analytics engine tests — worked examples matching docs/ANALYTICS.md.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.data_processor import (
    AnalyticsSummary,
    average_price,
    average_unit_price,
    basket_cost,
    basket_cost_for_month,
    compute_analytics_summary,
    highest_decrease,
    highest_increase,
    item_price_changes,
    load_analytics_dataframe,
    median_price,
    monthly_inflation_estimate,
    percentage_change,
    price_difference,
    records_to_dataframe,
)
from src.database import init_db, reset_engine
from src.entry_service import PriceEntryInput, save_price_entry
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
    unit_price = price_total / quantity
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
        unit_price=unit_price,
    )


# --- Pure formula examples (docs section 1–4) ---


def test_price_difference_rice_example() -> None:
    """Rice 500/kg → 560/kg → ΔP = +60."""
    assert price_difference(500.0, 560.0) == pytest.approx(60.0)


def test_percentage_change_rice_example() -> None:
    """(560 − 500) / 500 × 100 = +12%."""
    assert percentage_change(500.0, 560.0) == pytest.approx(12.0)


def test_percentage_change_zero_base_returns_none() -> None:
    assert percentage_change(0.0, 100.0) is None


def test_average_and_median_example() -> None:
    """Unit prices [500, 560, 12] → mean 357.33, median 500."""
    prices = [500.0, 560.0, 12.0]
    assert average_price(prices) == pytest.approx(357.333333, rel=1e-4)
    assert median_price(prices) == pytest.approx(500.0)


# --- Basket & extremes (docs section 5–7) ---


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Rice shrinkflation + milk + bread decrease."""
    rows = [
        _row(1, "Rice", "Market A", "Staples", 500.0, 1.0, "kg", "2026-05-01"),
        _row(2, "Rice", "Market A", "Staples", 280.0, 0.5, "kg", "2026-05-08"),
        _row(3, "Milk", "Shop B", "Dairy", 10.0, 1.0, "l", "2026-05-05"),
        _row(4, "Milk", "Shop B", "Dairy", 12.0, 1.0, "l", "2026-05-20"),
        _row(5, "Bread", "Shop B", "Bakery", 50.0, 1.0, "unit", "2026-05-01"),
        _row(6, "Bread", "Shop B", "Bakery", 46.0, 1.0, "unit", "2026-05-25"),
    ]
    return records_to_dataframe(rows)


def test_basket_cost_latest(sample_df: pd.DataFrame) -> None:
    """Latest shelf prices: Rice 280 + Milk 12 + Bread 46 = 338."""
    assert basket_cost(sample_df) == pytest.approx(338.0)


def test_highest_increase_is_rice(sample_df: pd.DataFrame) -> None:
    """Rice unit price 500 → 560 (+12%) is the largest rise."""
    inc = highest_increase(sample_df)
    assert inc is not None
    assert inc.item_name == "Rice"
    assert inc.percentage_change == pytest.approx(12.0)


def test_highest_decrease_is_bread(sample_df: pd.DataFrame) -> None:
    """Bread unit price 50 → 46 (−8%)."""
    dec = highest_decrease(sample_df)
    assert dec is not None
    assert dec.item_name == "Bread"
    assert dec.percentage_change == pytest.approx(-8.0)


def test_item_price_changes_count(sample_df: pd.DataFrame) -> None:
    changes = item_price_changes(sample_df)
    assert len(changes) == 3


# --- Monthly inflation (docs section 8) ---


@pytest.fixture
def two_month_df() -> pd.DataFrame:
    rows = [
        _row(1, "Rice", "Market A", "Staples", 100.0, 1.0, "kg", "2026-04-15"),
        _row(2, "Milk", "Market A", "Dairy", 170.0, 1.0, "l", "2026-04-20"),
        _row(3, "Rice", "Market A", "Staples", 110.0, 1.0, "kg", "2026-05-10"),
        _row(4, "Milk", "Market A", "Dairy", 182.0, 1.0, "l", "2026-05-15"),
    ]
    return records_to_dataframe(rows)


def test_basket_cost_per_month(two_month_df: pd.DataFrame) -> None:
    assert basket_cost_for_month(two_month_df, "2026-04") == pytest.approx(270.0)
    assert basket_cost_for_month(two_month_df, "2026-05") == pytest.approx(292.0)


def test_monthly_inflation_mom(two_month_df: pd.DataFrame) -> None:
    """(292 − 270) / 270 × 100 ≈ +8.15%."""
    rows = monthly_inflation_estimate(two_month_df)
    assert len(rows) == 1
    assert rows[0].basket_cost == pytest.approx(292.0)
    assert rows[0].previous_basket_cost == pytest.approx(270.0)
    assert rows[0].inflation_pct == pytest.approx(8.148148, rel=1e-4)


def test_analytics_summary_bundle(sample_df: pd.DataFrame) -> None:
    summary: AnalyticsSummary = compute_analytics_summary(sample_df)
    assert summary.observation_count == 6
    assert summary.item_count == 3
    assert summary.average_unit_price is not None
    assert summary.basket_cost_latest == pytest.approx(338.0)
    assert summary.highest_increase is not None
    assert len(summary.monthly_inflation) >= 0


def test_empty_dataframe_returns_none_metrics() -> None:
    df = records_to_dataframe([])
    assert average_unit_price(df) is None
    assert basket_cost(df) is None
    assert highest_increase(df) is None
    summary = compute_analytics_summary(df)
    assert summary.observation_count == 0


# --- Integration with SQLite ---


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "analytics.db"
    reset_engine()
    init_db(path)
    save_price_entry(
        PriceEntryInput(
            item_name="Rice (Parboiled)",
            store_name="Local Market A",
            category_name="Staples",
            price_total=500,
            date_recorded=date(2026, 5, 1),
            quantity=1,
            unit_type="kg",
        ),
        db_path=path,
    )
    save_price_entry(
        PriceEntryInput(
            item_name="Rice (Parboiled)",
            store_name="Local Market A",
            category_name="Staples",
            price_total=280,
            date_recorded=date(2026, 5, 8),
            quantity=0.5,
            unit_type="kg",
        ),
        db_path=path,
    )
    yield path
    reset_engine()


def test_load_from_database(db_path: Path) -> None:
    df = load_analytics_dataframe(db_path)
    assert len(df) == 2
    inc = highest_increase(df)
    assert inc is not None
    assert inc.percentage_change == pytest.approx(12.0)

"""Tests for Plotly chart builders."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.charts import (
    basket_cost_timeseries,
    build_basket_cost_chart,
    build_inflation_trend_chart,
    build_price_trend_chart,
    build_store_comparison_chart,
)
from src.data_processor import records_to_dataframe
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
def chart_df() -> pd.DataFrame:
    rows = [
        _row(1, "Rice", "Market A", "Staples", 500, 1, "kg", "2026-04-15"),
        _row(2, "Rice", "Market B", "Staples", 480, 1, "kg", "2026-04-20"),
        _row(3, "Rice", "Market A", "Staples", 560, 1, "kg", "2026-05-10"),
        _row(4, "Milk", "Market A", "Dairy", 170, 1, "l", "2026-04-20"),
        _row(5, "Milk", "Market A", "Dairy", 182, 1, "l", "2026-05-15"),
    ]
    return records_to_dataframe(rows)


def test_price_trend_returns_figure(chart_df: pd.DataFrame) -> None:
    fig = build_price_trend_chart(chart_df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1


def test_basket_timeseries(chart_df: pd.DataFrame) -> None:
    ts = basket_cost_timeseries(chart_df)
    assert len(ts) >= 1
    assert "basket_cost" in ts.columns


def test_basket_cost_monthly(chart_df: pd.DataFrame) -> None:
    fig = build_basket_cost_chart(chart_df, mode="monthly")
    assert len(fig.data) == 1


def test_store_comparison(chart_df: pd.DataFrame) -> None:
    fig = build_store_comparison_chart(chart_df, item_name="Rice")
    assert fig.data[0].type == "bar"


def test_inflation_chart_two_months(chart_df: pd.DataFrame) -> None:
    fig = build_inflation_trend_chart(chart_df)
    assert len(fig.data) >= 1


def test_empty_dataframe_empty_state() -> None:
    fig = build_price_trend_chart(records_to_dataframe([]))
    assert len(fig.layout.annotations) > 0

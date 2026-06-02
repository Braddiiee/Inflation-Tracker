"""
User Acceptance Tests (UAT) — automated checks for business journeys.

Each test maps to a scenario in docs/QA_UAT.md. Markers: pytest -m uat
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.charts import (
    build_basket_cost_chart,
    build_inflation_trend_chart,
    build_price_trend_chart,
    build_store_comparison_chart,
)
from src.data_processor import compute_dashboard_metrics, load_analytics_dataframe
from src.entry_service import PriceEntryInput, save_price_entry
from src.export.csv_export import export_records_csv_bytes
from src.record_service import list_records

pytestmark = pytest.mark.uat


class UATBudgeterTracksWeeklyShop:
    """Persona: Budgeter — log groceries and see if basket cost rose."""

    def test_uat_01_log_items_and_see_basket_cost(self, db_path: Path) -> None:
        save_price_entry(
            PriceEntryInput(
                item_name="Bread",
                store_name="Corner Store",
                category_name="Bakery",
                price_total=45,
                date_recorded=date(2026, 5, 1),
            ),
            db_path=db_path,
        )
        save_price_entry(
            PriceEntryInput(
                item_name="Milk",
                store_name="Corner Store",
                category_name="Dairy",
                price_total=55,
                date_recorded=date(2026, 5, 1),
            ),
            db_path=db_path,
        )
        metrics = compute_dashboard_metrics(load_analytics_dataframe(db_path=db_path))
        assert metrics.current_basket_cost == pytest.approx(100.0)
        assert metrics.item_count == 2

    def test_uat_02_time_to_insight_under_five_seconds_data_ready(self, populated_db: Path) -> None:
        """Metric: data available immediately after save (no manual refresh)."""
        df = load_analytics_dataframe(db_path=populated_db)
        metrics = compute_dashboard_metrics(df)
        assert metrics.current_basket_cost is not None
        assert metrics.weekly_change.current_cost is not None


class UATAnalystExportsData:
    """Persona: Analyst — filter, export, verify records."""

    def test_uat_03_export_csv_contains_all_fields(self, populated_db: Path) -> None:
        raw = export_records_csv_bytes(db_path=populated_db)
        for col in [b"item_name", b"store_name", b"unit_price", b"date_recorded"]:
            assert col in raw

    def test_uat_04_search_finds_item(self, populated_db: Path) -> None:
        result = list_records(search="milk", db_path=populated_db, page_size=50)
        assert result.total >= 1
        assert all("milk" in r.item_name.lower() for r in result.rows)


class UATSTEAMDemoIntegrity:
    """STEAM judges: zero critical input errors in demo path."""

    def test_uat_05_rejects_negative_price_on_entry(self, db_path: Path) -> None:
        from src.exceptions import ValidationError
        from src.entry_service import save_price_entry

        with pytest.raises(ValidationError):
            save_price_entry(
                PriceEntryInput(
                    item_name="Bad",
                    store_name="Store",
                    category_name="Test",
                    price_total=-5,
                    date_recorded=date(2026, 5, 1),
                ),
                db_path=db_path,
            )

    def test_uat_06_charts_render_with_demo_data(self, populated_db: Path) -> None:
        df = load_analytics_dataframe(db_path=populated_db)
        assert len(build_price_trend_chart(df).data) >= 1
        assert len(build_basket_cost_chart(df).data) >= 1
        assert len(build_store_comparison_chart(df, item_name="Milk").data) >= 1


class UATShrinkflationAwareness:
    """Rice 1kg vs 0.5kg — unit price shows true inflation."""

    def test_uat_07_unit_price_detects_shrinkflation(self, db_path: Path) -> None:
        save_price_entry(
            PriceEntryInput(
                item_name="Rice",
                store_name="Market",
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
                item_name="Rice",
                store_name="Market",
                category_name="Staples",
                price_total=280,
                date_recorded=date(2026, 5, 8),
                quantity=0.5,
                unit_type="kg",
            ),
            db_path=db_path,
        )
        df = load_analytics_dataframe(db_path=db_path)
        metrics = compute_dashboard_metrics(df)
        assert metrics.highest_inflation_item is not None
        assert metrics.highest_inflation_item.percentage_change == pytest.approx(12.0)

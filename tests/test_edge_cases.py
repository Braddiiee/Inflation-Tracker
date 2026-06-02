"""
Edge-case and failure-mode tests.

See docs/QA_EDGE_CASES.md for the full catalog.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.backup.database_backup import create_backup
from src.charts import build_inflation_trend_chart, build_price_trend_chart
from src.data_processor import (
    basket_cost,
    compute_dashboard_metrics,
    filter_dataframe,
    highest_decrease,
    highest_increase,
    load_analytics_dataframe,
    monthly_inflation_estimate,
    percentage_change,
    records_to_dataframe,
)
from src.database import init_db, reset_engine
from src.exceptions import DatabaseError, ValidationError
from src.export.pdf_report import generate_pdf_report_bytes
from src.import_data.csv_import import import_records_from_csv
from src.record_service import list_records

pytestmark = pytest.mark.edge


class TestEmptyAndMinimalData:
    def test_empty_database_metrics_safe(self, db_path: Path) -> None:
        metrics = compute_dashboard_metrics(load_analytics_dataframe(db_path=db_path))
        assert metrics.current_basket_cost is None
        assert metrics.highest_inflation_item is None

    def test_single_observation_no_inflation_extremes(self, db_path: Path) -> None:
        from src.entry_service import PriceEntryInput, save_price_entry

        save_price_entry(
            PriceEntryInput(
                item_name="Solo",
                store_name="S",
                category_name="C",
                price_total=1,
                date_recorded=date(2026, 5, 1),
            ),
            db_path=db_path,
        )
        df = load_analytics_dataframe(db_path=db_path)
        assert highest_increase(df) is None
        assert highest_decrease(df) is None

    def test_empty_chart_annotation(self) -> None:
        fig = build_price_trend_chart(records_to_dataframe([]))
        assert len(fig.layout.annotations) > 0


class TestNumericBoundaries:
    def test_percentage_change_zero_base(self) -> None:
        assert percentage_change(0, 100) is None

    def test_very_small_quantity_high_unit_price(self, db_path: Path) -> None:
        from src.entry_service import PriceEntryInput, save_price_entry

        save_price_entry(
            PriceEntryInput(
                item_name="Spice",
                store_name="S",
                category_name="C",
                price_total=10,
                quantity=0.001,
                unit_type="g",
                date_recorded=date(2026, 5, 1),
            ),
            db_path=db_path,
        )
        df = load_analytics_dataframe(db_path=db_path)
        assert df.iloc[0]["unit_price"] == pytest.approx(10000.0)


class TestPaginationBoundaries:
    def test_page_beyond_total_clamps(self, populated_db: Path) -> None:
        result = list_records(page=999, page_size=5, db_path=populated_db)
        assert result.page == result.total_pages
        assert len(result.rows) <= 5

    def test_search_no_matches(self, populated_db: Path) -> None:
        result = list_records(search="nonexistent_xyz", db_path=populated_db)
        assert result.total == 0
        assert result.rows == []


class TestImportExportEdgeCases:
    def test_import_missing_columns(self, db_path: Path) -> None:
        result = import_records_from_csv(
            b"item_name,price_total\nRice,10\n",
            db_path=db_path,
        )
        assert result.rows_imported == 0
        assert any("Missing required" in e for e in result.errors)

    def test_import_empty_csv(self, db_path: Path) -> None:
        result = import_records_from_csv(
            b"item_name,store_name,category_name,price_total,date_recorded\n",
            db_path=db_path,
        )
        assert "empty" in result.errors[0].lower()

    def test_pdf_empty_database(self, db_path: Path) -> None:
        pdf = generate_pdf_report_bytes(db_path=db_path)
        assert pdf.startswith(b"%PDF")


class TestBackupEdgeCases:
    def test_backup_missing_database_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.db"
        with pytest.raises(DatabaseError):
            create_backup(db_path=missing)


class TestFilterEdgeCases:
    def test_filter_date_range_excludes_all(self, populated_db: Path) -> None:
        df = load_analytics_dataframe(db_path=populated_db)
        out = filter_dataframe(df, start_date="2020-01-01", end_date="2020-01-31")
        assert out.empty

    def test_inflation_single_month_empty(self, db_path: Path) -> None:
        from src.entry_service import PriceEntryInput, save_price_entry

        save_price_entry(
            PriceEntryInput(
                item_name="X",
                store_name="S",
                category_name="C",
                price_total=1,
                date_recorded=date(2026, 5, 1),
            ),
            db_path=db_path,
        )
        df = load_analytics_dataframe(db_path=db_path)
        assert monthly_inflation_estimate(df) == []
        fig = build_inflation_trend_chart(df)
        assert len(fig.layout.annotations) > 0


class TestUnicodeAndSpecialCharacters:
    def test_unicode_item_name(self, db_path: Path) -> None:
        from src.entry_service import PriceEntryInput, save_price_entry

        save_price_entry(
            PriceEntryInput(
                item_name="Café con Leche",
                store_name="Mercado São Paulo",
                category_name="Bebidas",
                price_total=12,
                date_recorded=date(2026, 5, 1),
            ),
            db_path=db_path,
        )
        result = list_records(search="café", db_path=db_path)
        assert result.total >= 1

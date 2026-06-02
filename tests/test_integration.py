"""
Integration tests — end-to-end flows across DB, services, analytics, export.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.data_processor import (
    compute_dashboard_metrics,
    filter_dataframe,
    load_analytics_dataframe,
)
from src.entry_service import PriceEntryInput, save_price_entry
from src.export.csv_export import export_records_csv_bytes
from src.export.pdf_report import generate_pdf_report_bytes
from src.import_data.csv_import import import_records_from_csv
from src.record_service import delete_record, fetch_all_records, list_records, update_record

pytestmark = pytest.mark.integration


class TestEntryToAnalyticsPipeline:
    """User logs prices → dashboard metrics reflect them."""

    def test_save_then_dashboard_metrics(self, db_path: Path) -> None:
        save_price_entry(
            PriceEntryInput(
                item_name="Rice",
                store_name="Market",
                category_name="Staples",
                price_total=100,
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
                price_total=110,
                date_recorded=date(2026, 5, 15),
                quantity=1,
                unit_type="kg",
            ),
            db_path=db_path,
        )
        df = load_analytics_dataframe(db_path=db_path)
        metrics = compute_dashboard_metrics(df)
        assert metrics.observation_count == 2
        assert metrics.current_basket_cost == pytest.approx(110.0)
        assert metrics.highest_inflation_item is not None
        assert metrics.highest_inflation_item.percentage_change == pytest.approx(10.0)


class TestRecordsCrudPipeline:
    """Manage records: list → update → delete."""

    def test_full_crud_cycle(self, populated_db: Path) -> None:
        page = list_records(db_path=populated_db, page_size=10)
        assert page.total >= 4
        target = page.rows[0]

        update_record(
            target.log_id,
            PriceEntryInput(
                item_name=target.item_name,
                store_name=target.store_name,
                category_name=target.category_name,
                price_total=999.0,
                date_recorded=target.date_recorded,
                quantity=target.quantity,
                unit_type=target.unit_type,
            ),
            db_path=populated_db,
        )
        updated_page = list_records(
            search=str(target.log_id),
            db_path=populated_db,
            page_size=10,
        )
        assert any(r.price_total == 999.0 for r in updated_page.rows)

        delete_record(target.log_id, db_path=populated_db)
        remaining = fetch_all_records(db_path=populated_db)
        assert all(r.log_id != target.log_id for r in remaining)


class TestExportImportRoundTrip:
    """CSV export → modify → import adds rows."""

    def test_export_import_adds_row(self, populated_db: Path) -> None:
        csv_bytes = export_records_csv_bytes(db_path=populated_db)
        assert b"Rice" in csv_bytes

        extra = (
            b"item_name,store_name,category_name,price_total,date_recorded\n"
            b"Honey,Shop Z,Pantry,25.0,2026-05-22\n"
        )
        result = import_records_from_csv(extra, db_path=populated_db, skip_duplicates=True)
        assert result.rows_imported == 1
        names = [r.item_name for r in fetch_all_records(db_path=populated_db)]
        assert "Honey" in names


class TestPdfReportGeneration:
    def test_pdf_non_empty(self, populated_db: Path) -> None:
        pdf = generate_pdf_report_bytes(db_path=populated_db)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 500


class TestFilteredAnalytics:
    def test_category_filter_reduces_rows(self, populated_db: Path) -> None:
        df = load_analytics_dataframe(db_path=populated_db)
        dairy_only = filter_dataframe(df, category_name="Dairy")
        assert dairy_only["item_name"].nunique() == 1
        assert (dairy_only["category_name"] == "Dairy").all()

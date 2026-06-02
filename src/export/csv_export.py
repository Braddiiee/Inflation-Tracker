"""
CSV export for price log records.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd

from src.data_processor import load_analytics_dataframe

EXPORT_COLUMNS = [
    "log_id",
    "date_recorded",
    "item_name",
    "store_name",
    "category_name",
    "price_total",
    "quantity",
    "unit_type",
    "unit_price",
    "notes",
]


def records_dataframe_for_export(db_path: Path | None = None) -> pd.DataFrame:
    """Load all records in a stable column order for export/import round-trip."""
    df = load_analytics_dataframe(db_path=db_path)
    if df.empty:
        return pd.DataFrame(columns=EXPORT_COLUMNS)

    out = df.copy()
    out["date_recorded"] = pd.to_datetime(out["date_recorded"]).dt.strftime("%Y-%m-%d")
    out = out[EXPORT_COLUMNS]
    return out.sort_values(["date_recorded", "log_id"])


def export_records_csv(
    destination: Path,
    *,
    db_path: Path | None = None,
) -> Path:
    """Write all price records to a CSV file. Returns the output path."""
    df = records_dataframe_for_export(db_path=db_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destination, index=False, encoding="utf-8-sig")
    return destination


def export_records_csv_bytes(*, db_path: Path | None = None) -> bytes:
    """Return CSV content as UTF-8 bytes (for Streamlit download buttons)."""
    df = records_dataframe_for_export(db_path=db_path)
    buffer = StringIO()
    df.to_csv(buffer, index=False, encoding="utf-8")
    return buffer.getvalue().encode("utf-8-sig")


def default_csv_filename() -> str:
    """Suggested download filename with timestamp."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"grocery_prices_{stamp}.csv"

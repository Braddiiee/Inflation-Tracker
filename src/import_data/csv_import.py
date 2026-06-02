"""
CSV import for price records.

Expected columns (extra columns ignored):
  item_name, store_name, category_name, price_total, date_recorded,
  quantity (optional), unit_type (optional), notes (optional)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd

from src.entry_service import PriceEntryInput, save_price_entry
from src.exceptions import ValidationError
from src.export.csv_export import EXPORT_COLUMNS

REQUIRED_COLUMNS = {
    "item_name",
    "store_name",
    "category_name",
    "price_total",
    "date_recorded",
}


@dataclass
class ImportResult:
    """Summary of a CSV import run."""

    rows_processed: int = 0
    rows_imported: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and strip column headers."""
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    return out


def _parse_upload(file_bytes: bytes) -> pd.DataFrame:
    text = file_bytes.decode("utf-8-sig", errors="replace")
    return pd.read_csv(StringIO(text))


def import_records_from_csv(
    source: Path | bytes,
    *,
    db_path=None,
    skip_duplicates: bool = False,
) -> ImportResult:
    """
    Import rows from CSV into the database via entry_service validation.

    skip_duplicates: if True, skip rows that raise ValidationError (e.g. category mismatch).
    """
    if isinstance(source, Path):
        df = pd.read_csv(source, encoding="utf-8-sig")
    else:
        df = _parse_upload(source)

    result = ImportResult()
    if df.empty:
        result.errors.append("CSV file is empty.")
        return result

    df = _normalize_columns(df)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        result.errors.append(f"Missing required columns: {', '.join(sorted(missing))}")
        return result

    for idx, row in df.iterrows():
        result.rows_processed += 1
        line = int(idx) + 2  # header + 1-based

        try:
            quantity = row.get("quantity", 1.0)
            if pd.isna(quantity):
                quantity = 1.0
            unit_type = row.get("unit_type", "unit")
            if pd.isna(unit_type):
                unit_type = "unit"
            notes = row.get("notes")
            if pd.isna(notes):
                notes = None

            payload = PriceEntryInput(
                item_name=str(row["item_name"]),
                store_name=str(row["store_name"]),
                category_name=str(row["category_name"]),
                price_total=row["price_total"],
                date_recorded=str(row["date_recorded"])[:10],
                quantity=quantity,
                unit_type=str(unit_type),
                notes=str(notes) if notes is not None else None,
            )
            save_price_entry(payload, db_path=db_path)
            result.rows_imported += 1
        except ValidationError as exc:
            msg = f"Row {line}: {exc}"
            result.errors.append(msg)
            if skip_duplicates:
                result.rows_skipped += 1
            else:
                raise ValidationError(msg) from exc
        except Exception as exc:
            result.errors.append(f"Row {line}: {exc}")

    return result


def import_template_csv_bytes() -> bytes:
    """Empty template with correct headers for download."""
    df = pd.DataFrame(columns=[c for c in EXPORT_COLUMNS if c not in ("log_id", "unit_price")])
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")

"""
Business logic for viewing, searching, sorting, paginating, editing, and deleting records.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from src.database import get_session
from src.entry_service import PriceEntryInput, validate_entry_form
from src.exceptions import DatabaseError, NotFoundError, ValidationError
from src.models import PriceLog
from src.repositories import PriceLogRepository

SortField = Literal[
    "date_recorded",
    "item_name",
    "store_name",
    "category_name",
    "price_total",
]
SortOrder = Literal["asc", "desc"]

DEFAULT_PAGE_SIZE = 10
PAGE_SIZE_OPTIONS = (1, 5, 10, 25, 50)


@dataclass(frozen=True)
class PriceRecordRow:
    """Flat row for tables and forms (denormalized for the UI)."""

    log_id: int
    item_name: str
    store_name: str
    category_name: str
    price_total: float
    quantity: float
    unit_type: str
    date_recorded: str
    notes: str | None
    unit_price: float

    @property
    def unit_label(self) -> str:
        return f"{self.quantity:g} {self.unit_type}"


@dataclass(frozen=True)
class PaginatedRecords:
    """One page of records plus pagination metadata."""

    rows: list[PriceRecordRow]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 1
        return max(1, math.ceil(self.total / self.page_size))

    @property
    def showing_from(self) -> int:
        if self.total == 0:
            return 0
        return (self.page - 1) * self.page_size + 1

    @property
    def showing_to(self) -> int:
        if self.total == 0:
            return 0
        return min(self.page * self.page_size, self.total)


def _format_date(value: object) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[union-attr]
    return str(value)


def _log_to_row(log: PriceLog) -> PriceRecordRow:
    if log.product is None or log.store is None or log.product.category is None:
        raise DatabaseError("Incomplete record relationships.")
    return PriceRecordRow(
        log_id=log.log_id,
        item_name=log.product.product_name,
        store_name=log.store.store_name,
        category_name=log.product.category.category_name,
        price_total=float(log.price_total),
        quantity=float(log.quantity),
        unit_type=log.unit_type,
        date_recorded=_format_date(log.date_recorded),
        notes=log.notes,
        unit_price=float(log.price_total) / float(log.quantity),
    )


def _matches_search(row: PriceRecordRow, query: str) -> bool:
    q = query.strip().lower()
    if not q:
        return True
    haystack = " ".join(
        [
            str(row.log_id),
            row.item_name,
            row.store_name,
            row.category_name,
            row.notes or "",
            row.date_recorded,
        ]
    ).lower()
    return q in haystack


def _sort_key(row: PriceRecordRow, field: SortField):
    if field == "date_recorded":
        return row.date_recorded
    if field == "item_name":
        return row.item_name.lower()
    if field == "store_name":
        return row.store_name.lower()
    if field == "category_name":
        return row.category_name.lower()
    if field == "price_total":
        return row.price_total
    return row.date_recorded


def fetch_all_records(
    *,
    search: str = "",
    sort_by: SortField = "date_recorded",
    sort_order: SortOrder = "desc",
    db_path: Path | None = None,
) -> list[PriceRecordRow]:
    """Load every matching record (no pagination) for analytics."""
    with get_session(db_path) as session:
        logs = PriceLogRepository(session).list_enriched()

    rows = [_log_to_row(log) for log in logs]
    rows = [r for r in rows if _matches_search(r, search)]
    rows.sort(key=lambda r: _sort_key(r, sort_by), reverse=(sort_order == "desc"))
    return rows


def list_records(
    *,
    search: str = "",
    sort_by: SortField = "date_recorded",
    sort_order: SortOrder = "desc",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    db_path: Path | None = None,
) -> PaginatedRecords:
    """
    Return one page of records after search, sort, and slice.

    Page numbers are 1-based. Out-of-range pages clamp to the last page.
    """
    if page_size not in PAGE_SIZE_OPTIONS:
        page_size = DEFAULT_PAGE_SIZE
    page = max(1, page)

    with get_session(db_path) as session:
        logs = PriceLogRepository(session).list_enriched()

    rows = [_log_to_row(log) for log in logs]
    rows = [r for r in rows if _matches_search(r, search)]
    rows.sort(key=lambda r: _sort_key(r, sort_by), reverse=(sort_order == "desc"))

    total = len(rows)
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    page = min(page, total_pages)

    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return PaginatedRecords(
        rows=page_rows,
        total=total,
        page=page,
        page_size=page_size,
    )


def get_record(log_id: int, db_path: Path | None = None) -> PriceRecordRow:
    """Load a single record by id."""
    with get_session(db_path) as session:
        try:
            log = PriceLogRepository(session).get_by_id(log_id)
        except NotFoundError:
            raise
    return _log_to_row(log)


def update_record(
    log_id: int,
    data: PriceEntryInput,
    db_path: Path | None = None,
) -> PriceRecordRow:
    """Validate and persist edits to an existing price log."""
    errors = validate_entry_form(data)
    if errors:
        first_field = next(iter(errors))
        raise ValidationError(errors[first_field], field=first_field)

    from src.validation import (
        normalize_name,
        validate_date_recorded,
        validate_notes,
        validate_positive_number,
        validate_unit_type,
    )

    item = normalize_name(data.item_name, "item_name")
    store = normalize_name(data.store_name, "store_name")
    category = normalize_name(data.category_name, "category_name")
    price = validate_positive_number(data.price_total, "price")
    qty = validate_positive_number(data.quantity, "quantity")
    unit = validate_unit_type(data.unit_type)
    recorded = validate_date_recorded(data.date_recorded)
    notes = validate_notes(data.notes)

    with get_session(db_path) as session:
        log = PriceLogRepository(session).update_price_record(
            log_id=log_id,
            product_name=item,
            category_name=category,
            store_name=store,
            price_total=price,
            quantity=qty,
            unit_type=unit,
            date_recorded=recorded,
            notes=notes,
        )

    return _log_to_row(log)


def delete_record(log_id: int, db_path: Path | None = None) -> None:
    """Permanently delete a price log."""
    with get_session(db_path) as session:
        PriceLogRepository(session).delete(log_id)

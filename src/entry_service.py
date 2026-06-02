"""
Business logic for the Add Price Entry form.

Validates form payloads, persists via repositories, and returns structured results
for the Streamlit layer (no UI imports here).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.database import get_session, init_db
from src.exceptions import DatabaseError, ValidationError
from src.models import PriceLog
from src.repositories import CategoryRepository, PriceLogRepository
from src.validation import (
    normalize_name,
    validate_date_recorded,
    validate_notes,
    validate_positive_number,
    validate_unit_type,
)


@dataclass(frozen=True)
class PriceEntryInput:
    """Raw form values before validation."""

    item_name: str
    store_name: str
    category_name: str
    price_total: Any
    date_recorded: date | str
    notes: str | None = None
    quantity: Any = 1.0
    unit_type: str = "unit"


@dataclass(frozen=True)
class PriceEntryResult:
    """Successful save payload for UI confirmation."""

    log_id: int
    item_name: str
    store_name: str
    category_name: str
    price_total: float
    date_recorded: str
    unit_label: str


def ensure_database_ready(db_path: Path | None = None) -> None:
    """Create tables and apply migrations on first app load."""
    init_db(db_path)


def list_category_names(db_path: Path | None = None) -> list[str]:
    """Return sorted category names for form suggestions."""
    with get_session(db_path) as session:
        return [c.category_name for c in CategoryRepository(session).list_all()]


def validate_entry_form(data: PriceEntryInput) -> dict[str, str]:
    """
    Run all field validations without writing to the database.

    Returns a mapping of field name → error message (empty dict means valid).
    """
    errors: dict[str, str] = {}

    try:
        normalize_name(data.item_name, "item_name")
    except ValidationError as exc:
        errors["item_name"] = str(exc)

    try:
        normalize_name(data.store_name, "store_name")
    except ValidationError as exc:
        errors["store_name"] = str(exc)

    try:
        normalize_name(data.category_name, "category_name")
    except ValidationError as exc:
        errors["category_name"] = str(exc)

    try:
        validate_positive_number(data.price_total, "price")
    except ValidationError as exc:
        errors["price"] = str(exc)

    try:
        validate_date_recorded(data.date_recorded)
    except ValidationError as exc:
        errors["date_recorded"] = str(exc)

    try:
        validate_notes(data.notes)
    except ValidationError as exc:
        errors["notes"] = str(exc)

    try:
        validate_positive_number(data.quantity, "quantity")
    except ValidationError as exc:
        errors["quantity"] = str(exc)

    try:
        validate_unit_type(data.unit_type)
    except ValidationError as exc:
        errors["unit_type"] = str(exc)

    return errors


def save_price_entry(
    data: PriceEntryInput,
    db_path: Path | None = None,
) -> PriceEntryResult:
    """
    Validate and persist a new price log.

    Raises ValidationError or DatabaseError on failure.
    """
    errors = validate_entry_form(data)
    if errors:
        first_field = next(iter(errors))
        raise ValidationError(errors[first_field], field=first_field)

    item = normalize_name(data.item_name, "item_name")
    store = normalize_name(data.store_name, "store_name")
    category = normalize_name(data.category_name, "category_name")
    price = validate_positive_number(data.price_total, "price")
    qty = validate_positive_number(data.quantity, "quantity")
    unit = validate_unit_type(data.unit_type)
    recorded = validate_date_recorded(data.date_recorded)
    notes = validate_notes(data.notes)

    with get_session(db_path) as session:
        log: PriceLog = PriceLogRepository(session).insert_price_record(
            product_name=item,
            category_name=category,
            store_name=store,
            price_total=price,
            quantity=qty,
            unit_type=unit,
            date_recorded=recorded,
            notes=notes,
        )

    return PriceEntryResult(
        log_id=log.log_id,
        item_name=item,
        store_name=store,
        category_name=category,
        price_total=price,
        date_recorded=recorded,
        unit_label=f"{qty} {unit}",
    )

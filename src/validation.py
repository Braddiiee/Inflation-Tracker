"""
Input validation for the database layer.

All user-facing strings are trimmed; numeric and date rules mirror CHECK constraints
and MVP integrity goals (no negative prices, no future observation dates).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Final

from src.exceptions import ValidationError

VALID_UNITS: Final[tuple[str, ...]] = ("kg", "g", "l", "ml", "unit")


def normalize_name(value: str, field: str = "name") -> str:
    """Strip whitespace and reject empty names after trim."""
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError(f"{field} cannot be empty.", field=field)
    return cleaned


def validate_positive_number(value: float, field: str) -> float:
    """Ensure a numeric field is strictly greater than zero."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be a number.", field=field) from exc
    if number <= 0:
        raise ValidationError(f"{field} must be greater than zero.", field=field)
    return number


def validate_unit_type(unit_type: str) -> str:
    """Restrict units to the standardized set used in CHECK constraints."""
    unit = (unit_type or "").strip().lower()
    if unit not in VALID_UNITS:
        allowed = ", ".join(VALID_UNITS)
        raise ValidationError(
            f"unit_type must be one of: {allowed}.",
            field="unit_type",
        )
    return unit


def validate_date_recorded(value: str | date) -> str:
    """
    Accept ISO date strings (YYYY-MM-DD) or date objects.
    Reject future dates so demo integrity matches project goals.
    """
    if isinstance(value, date):
        recorded = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            recorded = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError(
                "date_recorded must be YYYY-MM-DD.",
                field="date_recorded",
            ) from exc
    else:
        raise ValidationError(
            "date_recorded must be a date or YYYY-MM-DD string.",
            field="date_recorded",
        )

    if recorded > date.today():
        raise ValidationError(
            "date_recorded cannot be in the future.",
            field="date_recorded",
        )
    return recorded.isoformat()


def to_date_recorded(value: str | date) -> date:
    """Return a Python date for ORM Date columns (after validation)."""
    iso = validate_date_recorded(value)
    return datetime.strptime(iso, "%Y-%m-%d").date()


def validate_notes(value: str | None) -> str | None:
    """Optional notes field; strip and enforce max length when provided."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > 500:
        raise ValidationError(
            "Notes must be 500 characters or fewer.",
            field="notes",
        )
    return text

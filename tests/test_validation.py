"""Unit tests — validation layer (src/validation.py)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.exceptions import ValidationError
from src.validation import (
    VALID_UNITS,
    normalize_name,
    to_date_recorded,
    validate_date_recorded,
    validate_notes,
    validate_positive_number,
    validate_unit_type,
)

pytestmark = pytest.mark.unit


class TestNormalizeName:
    def test_trims_whitespace(self) -> None:
        assert normalize_name("  Rice  ") == "Rice"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError) as exc:
            normalize_name("   ", field="item_name")
        assert exc.value.field == "item_name"


class TestPositiveNumber:
    def test_accepts_float_string(self) -> None:
        assert validate_positive_number("12.5", "price") == 12.5

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValidationError):
            validate_positive_number(0, "quantity")

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValidationError):
            validate_positive_number(-1, "price")

    def test_rejects_non_numeric(self) -> None:
        with pytest.raises(ValidationError):
            validate_positive_number("abc", "price")


class TestUnitType:
    @pytest.mark.parametrize("unit", VALID_UNITS)
    def test_accepts_valid_units(self, unit: str) -> None:
        assert validate_unit_type(unit) == unit

    def test_normalizes_case(self) -> None:
        assert validate_unit_type("KG") == "kg"

    def test_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            validate_unit_type("pound")


class TestDateRecorded:
    def test_accepts_date_object(self) -> None:
        assert validate_date_recorded(date(2026, 5, 1)) == "2026-05-01"

    def test_rejects_future(self) -> None:
        future = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError):
            validate_date_recorded(future)

    def test_rejects_bad_format(self) -> None:
        with pytest.raises(ValidationError):
            validate_date_recorded("05/01/2026")

    def test_to_date_returns_date_type(self) -> None:
        assert to_date_recorded("2026-05-01") == date(2026, 5, 1)


class TestNotes:
    def test_none_and_empty(self) -> None:
        assert validate_notes(None) is None
        assert validate_notes("   ") is None

    def test_trims(self) -> None:
        assert validate_notes("  promo  ") == "promo"

    def test_max_length(self) -> None:
        with pytest.raises(ValidationError):
            validate_notes("x" * 501)

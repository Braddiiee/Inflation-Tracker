"""
Reusable Streamlit UI building blocks for the inflation tracker.
"""

from __future__ import annotations

import streamlit as st

from src.entry_service import PriceEntryResult


def render_app_header() -> None:
    """Page title and short product description."""
    st.title("Grocery Inflation Tracker")
    st.caption(
        "Log local grocery prices to build your personal basket history. "
        "Dashboard charts coming soon."
    )


def render_field_errors(errors: dict[str, str]) -> None:
    """Show a summary error banner and per-field hints when validation fails."""
    if not errors:
        return
    st.error("Please fix the highlighted fields below.")
    for field, message in errors.items():
        st.session_state[f"field_error_{field}"] = message


def field_error_message(field: str) -> str | None:
    """Return a pending error for a field, if any."""
    return st.session_state.get(f"field_error_{field}")


def clear_field_errors() -> None:
    """Remove cached field errors after a successful submit or new attempt."""
    keys = [key for key in st.session_state if key.startswith("field_error_")]
    for key in keys:
        del st.session_state[key]


def render_success_message(result: PriceEntryResult) -> None:
    """Confirmation banner after a successful database write."""
    st.success(
        f"Saved **{result.item_name}** at **{result.store_name}** "
        f"({result.category_name}) — "
        f"**{result.price_total:,.2f}** for {result.unit_label} on **{result.date_recorded}**. "
        f"Record ID: `{result.log_id}`."
    )

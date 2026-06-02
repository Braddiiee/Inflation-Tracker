"""
Reusable Streamlit UI building blocks for the inflation tracker.
"""

from __future__ import annotations

import streamlit as st

from src.data_processor import BasketPeriodChange, ItemExtremeChange
from src.entry_service import PriceEntryResult


def render_app_header() -> None:
    """Page title and short product description."""
    st.title("Grocery Inflation Tracker")
    st.caption(
        "Log local grocery prices to build your personal basket history. "
        "Open the Dashboard page for interactive charts."
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


def render_flash_message(session_key: str) -> None:
    """Show and clear a one-shot success/info message from session state."""
    message = st.session_state.get(session_key)
    if message:
        st.success(message)
        st.session_state[session_key] = None


def render_dashboard_card(
    label: str,
    value: str,
    *,
    delta: str | None = None,
    help_text: str | None = None,
    delta_color: str = "inverse",
) -> None:
    """Bordered KPI card for the main dashboard row."""
    with st.container(border=True):
        st.metric(
            label=label,
            value=value,
            delta=delta,
            delta_color=delta_color,  # type: ignore[arg-type]
            help=help_text,
        )


def render_basket_change_card(
    title: str,
    change: BasketPeriodChange,
    *,
    help_text: str,
) -> None:
    """Card for weekly / monthly basket change (% and absolute)."""
    with st.container(border=True):
        if change.percent_change is None or change.current_cost is None:
            st.metric(title, "—", help=help_text)
            return
        st.metric(
            title,
            f"{change.percent_change:+.2f}%",
            delta=f"{change.price_difference:+,.2f} basket"
            if change.price_difference is not None
            else None,
            delta_color="inverse",
            help=help_text,
        )
        if change.previous_cost is not None:
            st.caption(
                f"Basket {change.previous_cost:,.2f} → {change.current_cost:,.2f}"
            )


def render_item_inflation_card(
    title: str,
    item: ItemExtremeChange | None,
    *,
    help_text: str,
    rising: bool,
) -> None:
    """Card for highest / lowest inflation item."""
    with st.container(border=True):
        if item is None:
            st.metric(title, "—", help=help_text)
            return
        pct = item.percentage_change
        arrow = "↑" if rising else "↓"
        st.metric(
            title,
            item.item_name,
            delta=f"{arrow} {pct:+.1f}% unit price",
            delta_color="inverse" if rising else "normal",
            help=help_text,
        )
        st.caption(f"{item.store_name} · {item.start_date} → {item.end_date}")

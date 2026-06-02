"""
Add Price Entry view — Streamlit form (UI only).
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from src.entry_service import (
    PriceEntryInput,
    PriceEntryResult,
    ensure_database_ready,
    list_category_names,
    save_price_entry,
    validate_entry_form,
)
from src.exceptions import DatabaseError, ValidationError
from src.ui_components import (
    clear_field_errors,
    field_error_message,
    render_app_header,
    render_success_message,
)
from src.validation import VALID_UNITS

_NEW_CATEGORY = "➕ New category…"
_UNIT_LABELS = {
    "kg": "Kilogram (kg)",
    "g": "Gram (g)",
    "l": "Liter (l)",
    "ml": "Milliliter (ml)",
    "unit": "Per item / pack (unit)",
}


def _init_session_state() -> None:
    if "entry_success" not in st.session_state:
        st.session_state.entry_success = None


def render_add_price_page() -> None:
    """Render the full Add Price Entry form and handle submission."""
    ensure_database_ready()
    _init_session_state()

    render_app_header()

    success: PriceEntryResult | None = st.session_state.entry_success
    if success is not None:
        render_success_message(success)

    categories = list_category_names()
    category_options = categories + [_NEW_CATEGORY] if categories else [_NEW_CATEGORY]

    with st.form("add_price_form", clear_on_submit=False):
        st.subheader("Add price entry")

        col_item, col_store = st.columns(2)
        with col_item:
            item_name = st.text_input(
                "Item name *",
                placeholder="e.g. Rice (Parboiled)",
                help="The product you are tracking.",
            )
            if field_error_message("item_name"):
                st.caption(f":red[{field_error_message('item_name')}]")

        with col_store:
            store_name = st.text_input(
                "Store name *",
                placeholder="e.g. Local Market A",
                help="Where you observed this price.",
            )
            if field_error_message("store_name"):
                st.caption(f":red[{field_error_message('store_name')}]")

        category_choice = st.selectbox(
            "Category *",
            options=category_options,
            help="Group items for filtering (e.g. Staples, Dairy).",
        )
        if category_choice == _NEW_CATEGORY:
            category_name = st.text_input(
                "New category name *",
                placeholder="e.g. Staples",
            )
        else:
            category_name = category_choice

        if field_error_message("category_name"):
            st.caption(f":red[{field_error_message('category_name')}]")

        col_price, col_date = st.columns(2)
        with col_price:
            price = st.number_input(
                "Price (total paid) *",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Total amount paid for the quantity below (not per-unit).",
            )
            if field_error_message("price"):
                st.caption(f":red[{field_error_message('price')}]")

        with col_date:
            recorded = st.date_input(
                "Date observed *",
                value=date.today(),
                max_value=date.today(),
                help="Cannot be in the future.",
            )
            if field_error_message("date_recorded"):
                st.caption(f":red[{field_error_message('date_recorded')}]")

        notes = st.text_area(
            "Notes",
            placeholder="Optional: brand, promotion, package change, etc.",
            max_chars=500,
            help="Stored with this record for your own audit trail.",
        )
        if field_error_message("notes"):
            st.caption(f":red[{field_error_message('notes')}]")

        with st.expander("Package size (recommended for accurate trends)", expanded=False):
            st.caption(
                "Required for fair price comparisons when package sizes change (shrinkflation). "
                "Defaults: 1 item at per-pack pricing."
            )
            col_qty, col_unit = st.columns(2)
            with col_qty:
                quantity = st.number_input(
                    "Quantity *",
                    min_value=0.0,
                    value=1.0,
                    step=0.01,
                    format="%.3f",
                )
                if field_error_message("quantity"):
                    st.caption(f":red[{field_error_message('quantity')}]")
            with col_unit:
                unit_type = st.selectbox(
                    "Unit of measure *",
                    options=list(VALID_UNITS),
                    format_func=lambda u: _UNIT_LABELS.get(u, u),
                )
                if field_error_message("unit_type"):
                    st.caption(f":red[{field_error_message('unit_type')}]")

        submitted = st.form_submit_button(
            "Save price entry",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    clear_field_errors()
    st.session_state.entry_success = None

    payload = PriceEntryInput(
        item_name=item_name,
        store_name=store_name,
        category_name=category_name or "",
        price_total=price,
        date_recorded=recorded,
        notes=notes or None,
        quantity=quantity,
        unit_type=unit_type,
    )

    errors = validate_entry_form(payload)
    if errors:
        for field, message in errors.items():
            st.session_state[f"field_error_{field}"] = message
        st.rerun()

    try:
        result = save_price_entry(payload)
    except ValidationError as exc:
        field = exc.field or "price"
        st.session_state[f"field_error_{field}"] = str(exc)
        st.rerun()
    except DatabaseError as exc:
        st.error(f"Could not save to the database. Please try again. ({exc})")
        return

    st.session_state.entry_success = result
    st.rerun()

"""
Manage Records view — list, search, sort, paginate, edit, and delete price logs.
"""

from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from src.entry_service import PriceEntryInput, ensure_database_ready, list_category_names
from src.theme import apply_theme
from src.exceptions import DatabaseError, NotFoundError, ValidationError
from src.record_service import (
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PaginatedRecords,
    PriceRecordRow,
    SortField,
    SortOrder,
    delete_record,
    get_record,
    list_records,
    update_record,
)
from src.ui_components import render_flash_message
from src.validation import VALID_UNITS

_NEW_CATEGORY = "➕ New category…"
_UNIT_LABELS = {
    "kg": "Kilogram (kg)",
    "g": "Gram (g)",
    "l": "Liter (l)",
    "ml": "Milliliter (ml)",
    "unit": "Per item / pack (unit)",
}
_SORT_LABELS: dict[SortField, str] = {
    "date_recorded": "Date",
    "item_name": "Item name",
    "store_name": "Store",
    "category_name": "Category",
    "price_total": "Price (total)",
}


def _init_records_state() -> None:
    defaults = {
        "records_search": "",
        "records_sort_by": "date_recorded",
        "records_sort_order": "desc",
        "records_page": 1,
        "records_page_size": DEFAULT_PAGE_SIZE,
        "records_edit_id": None,
        "records_pending_delete": None,
        "records_flash": None,
        "records_edit_errors": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.dialog("Confirm deletion")
def _confirm_delete_dialog(record: PriceRecordRow) -> None:
    """Modal confirmation before permanent delete."""
    st.warning(
        f"You are about to delete record **#{record.log_id}**.\n\n"
        f"**{record.item_name}** at **{record.store_name}** "
        f"({record.date_recorded}) — **{record.price_total:,.2f}**.\n\n"
        "This cannot be undone."
    )
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Yes, delete permanently", type="primary", use_container_width=True):
            try:
                delete_record(record.log_id)
            except DatabaseError as exc:
                st.error(f"Delete failed: {exc}")
                return
            st.session_state.records_pending_delete = None
            st.session_state.records_edit_id = None
            st.session_state.records_flash = (
                f"Deleted record #{record.log_id} ({record.item_name})."
            )
            st.rerun()
    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.session_state.records_pending_delete = None
            st.rerun()


def _render_toolbar() -> None:
    """Search, sort, and page-size controls."""
    st.subheader("Browse records")

    col_search, col_sort, col_order, col_size = st.columns([2, 1.2, 1, 0.8])

    with col_search:
        search = st.text_input(
            "Search",
            value=st.session_state.records_search,
            placeholder="Item, store, category, notes, or ID…",
            help="Filters the current dataset (case-insensitive).",
        )
        if search != st.session_state.records_search:
            st.session_state.records_search = search
            st.session_state.records_page = 1

    with col_sort:
        sort_by: SortField = st.selectbox(
            "Sort by",
            options=list(_SORT_LABELS.keys()),
            format_func=lambda k: _SORT_LABELS[k],
            index=list(_SORT_LABELS.keys()).index(st.session_state.records_sort_by),
        )
        if sort_by != st.session_state.records_sort_by:
            st.session_state.records_sort_by = sort_by
            st.session_state.records_page = 1

    with col_order:
        sort_order: SortOrder = st.selectbox(
            "Order",
            options=["desc", "asc"],
            format_func=lambda o: "Newest / A → Z" if o == "desc" else "Oldest / Z → A",
            index=0 if st.session_state.records_sort_order == "desc" else 1,
        )
        if sort_order != st.session_state.records_sort_order:
            st.session_state.records_sort_order = sort_order
            st.session_state.records_page = 1

    with col_size:
        page_size = st.selectbox(
            "Per page",
            options=list(PAGE_SIZE_OPTIONS),
            index=list(PAGE_SIZE_OPTIONS).index(st.session_state.records_page_size),
        )
        if page_size != st.session_state.records_page_size:
            st.session_state.records_page_size = page_size
            st.session_state.records_page = 1


def _render_pagination(result: PaginatedRecords) -> None:
    """Previous / next controls and page indicator."""
    col_info, col_prev, col_page, col_next = st.columns([2, 1, 1, 1])

    with col_info:
        if result.total == 0:
            st.caption("No records match your search.")
        else:
            st.caption(
                f"Showing **{result.showing_from}–{result.showing_to}** of **{result.total}** "
                f"(page {result.page} of {result.total_pages})"
            )

    with col_prev:
        if st.button("← Previous", disabled=result.page <= 1, use_container_width=True):
            st.session_state.records_page = max(1, result.page - 1)
            st.rerun()

    with col_page:
        new_page = st.number_input(
            "Page",
            min_value=1,
            max_value=result.total_pages,
            value=result.page,
            step=1,
            label_visibility="collapsed",
        )
        if new_page != result.page:
            st.session_state.records_page = int(new_page)
            st.rerun()

    with col_next:
        if st.button(
            "Next →",
            disabled=result.page >= result.total_pages,
            use_container_width=True,
        ):
            st.session_state.records_page = result.page + 1
            st.rerun()


def _render_records_table(result: PaginatedRecords) -> None:
    """Table of records with Edit / Delete actions per row."""
    if not result.rows:
        st.info("No price records yet. Add your first entry from **Add Price Entry**.")
        return

    header = st.columns([0.5, 1.6, 1.2, 1.0, 0.9, 0.9, 1.0, 0.9])
    labels = ["ID", "Item", "Store", "Category", "Price", "Qty", "Date", "Actions"]
    for col, label in zip(header, labels):
        col.markdown(f"**{label}**")

    st.divider()

    for row in result.rows:
        cols = st.columns([0.5, 1.6, 1.2, 1.0, 0.9, 0.9, 1.0, 0.9])
        cols[0].write(f"`{row.log_id}`")
        cols[1].write(row.item_name)
        cols[2].write(row.store_name)
        cols[3].write(row.category_name)
        cols[4].write(f"{row.price_total:,.2f}")
        cols[5].write(row.unit_label)
        cols[6].write(row.date_recorded)
        with cols[7]:
            btn_edit, btn_del = st.columns(2)
            with btn_edit:
                if st.button("Edit", key=f"edit_{row.log_id}", use_container_width=True):
                    st.session_state.records_edit_id = row.log_id
                    st.session_state.records_edit_errors = {}
                    st.rerun()
            with btn_del:
                if st.button("Delete", key=f"del_{row.log_id}", use_container_width=True):
                    st.session_state.records_pending_delete = row.log_id
                    st.rerun()

        if row.notes:
            st.caption(f"Notes: _{row.notes}_")

        st.divider()


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _render_edit_form(record: PriceRecordRow) -> None:
    """Inline edit form for the selected record."""
    st.subheader(f"Edit record #{record.log_id}")

    categories = list_category_names()
    category_options = categories + [_NEW_CATEGORY] if categories else [_NEW_CATEGORY]
    current_category = record.category_name
    if current_category in categories:
        default_index = categories.index(current_category)
    else:
        category_options = [current_category] + category_options
        default_index = 0

    errors: dict[str, str] = st.session_state.records_edit_errors

    with st.form(f"edit_form_{record.log_id}", clear_on_submit=False):
        col_item, col_store = st.columns(2)
        with col_item:
            item_name = st.text_input("Item name *", value=record.item_name)
            if errors.get("item_name"):
                st.caption(f":red[{errors['item_name']}]")
        with col_store:
            store_name = st.text_input("Store name *", value=record.store_name)
            if errors.get("store_name"):
                st.caption(f":red[{errors['store_name']}]")

        category_choice = st.selectbox(
            "Category *",
            options=category_options,
            index=default_index if current_category in category_options else 0,
        )
        if category_choice == _NEW_CATEGORY:
            category_name = st.text_input("New category name *", value=record.category_name)
        else:
            category_name = category_choice
        if errors.get("category_name"):
            st.caption(f":red[{errors['category_name']}]")

        col_price, col_date = st.columns(2)
        with col_price:
            price = st.number_input(
                "Price (total paid) *",
                min_value=0.0,
                value=float(record.price_total),
                step=0.01,
                format="%.2f",
            )
            if errors.get("price"):
                st.caption(f":red[{errors['price']}]")
        with col_date:
            recorded = st.date_input(
                "Date observed *",
                value=_parse_date(record.date_recorded),
                max_value=date.today(),
            )
            if errors.get("date_recorded"):
                st.caption(f":red[{errors['date_recorded']}]")

        notes = st.text_area("Notes", value=record.notes or "", max_chars=500)
        if errors.get("notes"):
            st.caption(f":red[{errors['notes']}]")

        col_qty, col_unit = st.columns(2)
        with col_qty:
            quantity = st.number_input(
                "Quantity *",
                min_value=0.0,
                value=float(record.quantity),
                step=0.01,
                format="%.3f",
            )
            if errors.get("quantity"):
                st.caption(f":red[{errors['quantity']}]")
        with col_unit:
            unit_index = list(VALID_UNITS).index(record.unit_type)
            unit_type = st.selectbox(
                "Unit of measure *",
                options=list(VALID_UNITS),
                index=unit_index,
                format_func=lambda u: _UNIT_LABELS.get(u, u),
            )
            if errors.get("unit_type"):
                st.caption(f":red[{errors['unit_type']}]")

        col_save, col_cancel = st.columns(2)
        save = col_save.form_submit_button("Save changes", type="primary", use_container_width=True)
        cancel = col_cancel.form_submit_button("Cancel", use_container_width=True)

    if cancel:
        st.session_state.records_edit_id = None
        st.session_state.records_edit_errors = {}
        st.rerun()

    if not save:
        return

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

    from src.entry_service import validate_entry_form

    validation_errors = validate_entry_form(payload)
    if validation_errors:
        st.session_state.records_edit_errors = validation_errors
        st.rerun()

    try:
        updated = update_record(record.log_id, payload)
    except ValidationError as exc:
        field = exc.field or "price"
        st.session_state.records_edit_errors = {field: str(exc)}
        st.rerun()
    except DatabaseError as exc:
        st.error(f"Could not save changes: {exc}")
        return

    st.session_state.records_edit_id = None
    st.session_state.records_edit_errors = {}
    st.session_state.records_flash = (
        f"Updated record #{updated.log_id} ({updated.item_name})."
    )
    st.rerun()


def render_manage_records_page() -> None:
    """Main entry: view, edit, and delete price records."""
    ensure_database_ready()
    apply_theme()
    _init_records_state()

    st.title("Manage Records")
    st.caption("View, edit, or delete saved price entries.")

    render_flash_message("records_flash")

    pending_id = st.session_state.records_pending_delete
    if pending_id is not None:
        try:
            pending_record = get_record(pending_id)
            _confirm_delete_dialog(pending_record)
        except NotFoundError:
            st.session_state.records_pending_delete = None
            st.warning("That record was already removed.")
            st.rerun()

    _render_toolbar()

    result = list_records(
        search=st.session_state.records_search,
        sort_by=st.session_state.records_sort_by,
        sort_order=st.session_state.records_sort_order,
        page=st.session_state.records_page,
        page_size=st.session_state.records_page_size,
    )

    _render_pagination(result)
    _render_records_table(result)
    _render_pagination(result)

    edit_id = st.session_state.records_edit_id
    if edit_id is not None:
        try:
            record = get_record(edit_id)
        except NotFoundError:
            st.session_state.records_edit_id = None
            st.warning("Record not found—it may have been deleted.")
            st.rerun()
        st.divider()
        _render_edit_form(record)

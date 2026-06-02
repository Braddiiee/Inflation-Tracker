"""
Settings & data tools — export, import, backup, restore, theme.
"""

from __future__ import annotations

import streamlit as st

from src.backup.database_backup import create_backup, list_backups, restore_backup
from src.database import DEFAULT_DB_PATH, reset_engine
from src.entry_service import ensure_database_ready
from src.exceptions import DatabaseError, ValidationError
from src.export.csv_export import default_csv_filename, export_records_csv_bytes
from src.export.pdf_report import default_pdf_filename, generate_pdf_report_bytes
from src.import_data.csv_import import import_records_from_csv, import_template_csv_bytes
from src.theme import THEME_DARK, THEME_LIGHT, apply_theme, get_theme, set_theme


def _clear_caches() -> None:
    """Clear Streamlit data caches after DB changes."""
    from src.dashboard_view import _load_data

    _load_data.clear()
    reset_engine()


def render_settings_page() -> None:
    """Settings hub with tabs for each capability."""
    ensure_database_ready()
    apply_theme()

    st.title("Settings & data")
    st.caption("Export reports, import CSV, backup or restore your database, and switch appearance.")

    tab_export, tab_import, tab_backup, tab_appearance = st.tabs(
        ["Export", "Import", "Backup & restore", "Appearance"]
    )

    # --- Export ---
    with tab_export:
        st.subheader("Export data")
        col_csv, col_pdf = st.columns(2)

        with col_csv:
            st.markdown("**CSV export**")
            st.caption("All price records for Excel or Google Sheets.")
            try:
                csv_bytes = export_records_csv_bytes()
                st.download_button(
                    label="Download CSV",
                    data=csv_bytes,
                    file_name=default_csv_filename(),
                    mime="text/csv",
                    type="primary",
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"CSV export failed: {exc}")

        with col_pdf:
            st.markdown("**PDF report**")
            st.caption("Summary KPIs, inflation table, and recent entries.")
            try:
                pdf_bytes = generate_pdf_report_bytes()
                st.download_button(
                    label="Download PDF report",
                    data=pdf_bytes,
                    file_name=default_pdf_filename(),
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"PDF export failed: {exc}")

    # --- Import ---
    with tab_import:
        st.subheader("Import from CSV")
        st.download_button(
            label="Download import template",
            data=import_template_csv_bytes(),
            file_name="grocery_import_template.csv",
            mime="text/csv",
        )
        st.markdown(
            "Required columns: `item_name`, `store_name`, `category_name`, "
            "`price_total`, `date_recorded`. Optional: `quantity`, `unit_type`, `notes`."
        )

        uploaded = st.file_uploader("Choose CSV file", type=["csv"])
        skip_dup = st.checkbox(
            "Skip rows with validation errors (import valid rows only)",
            value=True,
        )

        if st.button("Import CSV", type="primary", disabled=uploaded is None):
            if uploaded is None:
                return
            try:
                result = import_records_from_csv(
                    uploaded.getvalue(),
                    skip_duplicates=skip_dup,
                )
                _clear_caches()
                st.success(
                    f"Imported **{result.rows_imported}** of **{result.rows_processed}** rows."
                )
                if result.errors:
                    with st.expander(f"{len(result.errors)} warnings / errors"):
                        for err in result.errors[:50]:
                            st.text(err)
            except ValidationError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Import failed: {exc}")

    # --- Backup & restore ---
    with tab_backup:
        st.subheader("Backup database")
        st.caption(f"Live database: `{DEFAULT_DB_PATH}`")

        if st.button("Create backup now", type="primary"):
            try:
                info = create_backup()
                st.success(f"Backup saved: `{info.filename}` ({info.size_bytes:,} bytes)")
            except DatabaseError as exc:
                st.error(str(exc))

        backups = list_backups()
        st.markdown(f"**{len(backups)}** backup(s) on disk")

        if backups:
            options = {
                f"{b.filename} — {b.created_at:%Y-%m-%d %H:%M} ({b.size_bytes:,} B)": b
                for b in backups
            }
            choice = st.selectbox("Select backup to restore", options=list(options.keys()))
            st.warning(
                "Restore replaces your current database. A safety backup is created automatically."
            )
            if st.button("Restore selected backup", type="secondary"):
                try:
                    restore_backup(options[choice].path)
                    _clear_caches()
                    st.success("Database restored. Reloading…")
                    st.rerun()
                except DatabaseError as exc:
                    st.error(str(exc))
        else:
            st.info("No backups yet. Create one before making large imports or experiments.")

    # --- Appearance ---
    with tab_appearance:
        st.subheader("Dark mode")
        current = get_theme()
        choice = st.radio(
            "Theme",
            options=[THEME_LIGHT, THEME_DARK],
            index=0 if current == THEME_LIGHT else 1,
            format_func=lambda t: "Light" if t == THEME_LIGHT else "Dark",
            horizontal=True,
        )
        if choice != current:
            set_theme(choice)
            st.rerun()
        st.caption("Theme applies across all pages in this session.")

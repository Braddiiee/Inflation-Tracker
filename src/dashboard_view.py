"""
Product dashboard — KPI cards, charts, filters, and recent entries.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts import (
    build_basket_cost_chart,
    build_inflation_trend_chart,
    build_price_trend_chart,
    build_store_comparison_chart,
)
from src.data_processor import (
    compute_dashboard_metrics,
    filter_dataframe,
    load_analytics_dataframe,
)
from src.entry_service import ensure_database_ready
from src.ui_components import (
    render_basket_change_card,
    render_dashboard_card,
    render_item_inflation_card,
)

RECENT_ENTRIES_LIMIT = 10


def _apply_multiselect_filter(
    df: pd.DataFrame,
    column: str,
    selected: list[str],
) -> pd.DataFrame:
    if not selected or df.empty:
        return df
    return df[df[column].isin(selected)].copy()


@st.cache_data(show_spinner="Loading price data…", ttl=60)
def _load_data() -> pd.DataFrame:
    return load_analytics_dataframe()


def _render_sidebar_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None, list[str]]:
    """Sidebar filters; returns filtered df, store-comparison item, trend items."""
    st.sidebar.header("Dashboard filters")

    if df.empty:
        st.sidebar.info("Add price entries to enable filters.")
        return df, None, []

    min_d = df["date_recorded"].min().date()
    max_d = df["date_recorded"].max().date()

    c1, c2 = st.sidebar.columns(2)
    with c1:
        start = st.date_input("From", value=min_d, min_value=min_d, max_value=max_d)
    with c2:
        end = st.date_input("To", value=max_d, min_value=min_d, max_value=max_d)

    if start > end:
        st.sidebar.error("'From' must be on or before 'To'.")
        return df.iloc[0:0], None, []

    categories = sorted(df["category_name"].unique())
    stores = sorted(df["store_name"].unique())
    items = sorted(df["item_name"].unique())

    selected_categories = st.sidebar.multiselect(
        "Categories",
        options=categories,
        default=categories,
    )
    selected_stores = st.sidebar.multiselect(
        "Stores",
        options=stores,
        default=stores,
    )
    selected_items = st.sidebar.multiselect(
        "Items (charts)",
        options=items,
        default=items,
    )

    compare_item = st.sidebar.selectbox(
        "Item — store comparison",
        options=items,
        index=0,
    )

    basket_mode = st.sidebar.radio(
        "Basket chart",
        options=["timeline", "monthly"],
        format_func=lambda m: "Over time" if m == "timeline" else "By month",
    )

    if st.sidebar.button("Refresh data", use_container_width=True, type="primary"):
        _load_data.clear()
        st.rerun()

    filtered = filter_dataframe(
        df,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )
    filtered = _apply_multiselect_filter(filtered, "category_name", selected_categories)
    filtered = _apply_multiselect_filter(filtered, "store_name", selected_stores)

    st.session_state["dashboard_basket_mode"] = basket_mode
    return filtered, compare_item, selected_items


def _render_dashboard_cards(df: pd.DataFrame) -> None:
    """Top row: five product KPI cards."""
    metrics = compute_dashboard_metrics(df)

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        render_dashboard_card(
            "Current basket cost",
            f"{metrics.current_basket_cost:,.2f}"
            if metrics.current_basket_cost is not None
            else "—",
            help_text="Sum of the latest shelf price paid for each item in your basket.",
        )

    with c2:
        render_basket_change_card(
            "Weekly change",
            metrics.weekly_change,
            help_text="Basket cost today vs 7 days ago (% and absolute).",
        )

    with c3:
        render_basket_change_card(
            "Monthly change",
            metrics.monthly_change,
            help_text="Basket cost today vs 30 days ago (% and absolute).",
        )

    with c4:
        render_item_inflation_card(
            "Highest inflation item",
            metrics.highest_inflation_item,
            help_text="Largest unit-price increase (first → last observation in range).",
            rising=True,
        )

    with c5:
        render_item_inflation_card(
            "Lowest inflation item",
            metrics.lowest_inflation_item,
            help_text="Largest unit-price decrease — best relief for your budget.",
            rising=False,
        )


def _render_secondary_kpis(df: pd.DataFrame) -> None:
    """Supporting metrics below the main cards."""
    metrics = compute_dashboard_metrics(df)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Observations", metrics.observation_count)
    k2.metric("Items in basket", metrics.item_count)
    k3.metric(
        "Avg unit price",
        f"{metrics.average_unit_price:,.2f}" if metrics.average_unit_price else "—",
    )
    wc = metrics.weekly_change
    if wc.previous_cost is not None and wc.current_cost is not None:
        k4.metric(
            "Basket (7d ago)",
            f"{wc.previous_cost:,.2f}",
            delta=f"{wc.current_cost - wc.previous_cost:+,.2f} vs today",
            delta_color="inverse",
        )
    else:
        k4.metric("Basket (7d ago)", "—")


def _render_recent_entries(df: pd.DataFrame) -> None:
    """Table of the most recent price logs."""
    st.subheader("Recent entries")
    if df.empty:
        st.caption("No entries in the current filter range.")
        return

    recent = (
        df.sort_values(["date_recorded", "log_id"], ascending=False)
        .head(RECENT_ENTRIES_LIMIT)
        .copy()
    )
    recent["date_recorded"] = recent["date_recorded"].dt.strftime("%Y-%m-%d")
    display = recent[
        [
            "log_id",
            "date_recorded",
            "item_name",
            "store_name",
            "category_name",
            "price_total",
            "quantity",
            "unit_type",
            "unit_price",
            "notes",
        ]
    ].rename(
        columns={
            "log_id": "ID",
            "date_recorded": "Date",
            "item_name": "Item",
            "store_name": "Store",
            "category_name": "Category",
            "price_total": "Price paid",
            "quantity": "Qty",
            "unit_type": "Unit",
            "unit_price": "Unit price",
            "notes": "Notes",
        }
    )
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price paid": st.column_config.NumberColumn(format="%.2f"),
            "Unit price": st.column_config.NumberColumn(format="%.2f"),
            "Qty": st.column_config.NumberColumn(format="%.3f"),
        },
    )
    st.caption(
        f"Showing {len(recent)} of {len(df)} records · "
        "Manage all entries on **Manage Records**."
    )


def _render_charts(
    df: pd.DataFrame,
    *,
    trend_items: list[str],
    compare_item: str | None,
    basket_mode: str,
) -> None:
    """Two-row chart grid."""
    st.subheader("Charts")

    row1_a, row1_b = st.columns(2)
    with row1_a:
        st.markdown("**Price trends** — unit price over time")
        st.plotly_chart(
            build_price_trend_chart(df, items=trend_items or None),
            use_container_width=True,
            key="chart_price_trend",
        )
    with row1_b:
        st.markdown("**Basket cost**")
        st.plotly_chart(
            build_basket_cost_chart(df, mode=basket_mode),
            use_container_width=True,
            key="chart_basket",
        )

    row2_a, row2_b = st.columns(2)
    with row2_a:
        st.markdown("**Store comparison**")
        st.plotly_chart(
            build_store_comparison_chart(df, item_name=compare_item, metric="mean"),
            use_container_width=True,
            key="chart_store",
        )
    with row2_b:
        st.markdown("**Monthly inflation**")
        st.plotly_chart(
            build_inflation_trend_chart(df),
            use_container_width=True,
            key="chart_inflation",
        )


def render_dashboard_page() -> None:
    """Full product dashboard."""
    ensure_database_ready()

    st.title("Dashboard")
    st.caption(
        "Your grocery inflation command center — basket cost, period changes, "
        "item movers, charts, and latest entries. Use the sidebar to filter."
    )

    raw_df = _load_data()
    filtered_df, compare_item, trend_items = _render_sidebar_filters(raw_df)

    if raw_df.empty:
        st.warning(
            "No price data yet. Open **Add Price Entry** to log your first shop, "
            "then return here for insights."
        )
        st.page_link("pages/1_Add_Price.py", label="➕ Go to Add Price Entry")
        return

    _render_dashboard_cards(filtered_df if not filtered_df.empty else raw_df)
    st.divider()

    active_df = filtered_df if not filtered_df.empty else raw_df
    _render_secondary_kpis(active_df)

    if filtered_df.empty:
        st.warning("No records match the current filters. Widen the date range or clear selections.")
        return

    basket_mode = st.session_state.get("dashboard_basket_mode", "timeline")

    _render_charts(
        filtered_df,
        trend_items=trend_items,
        compare_item=compare_item,
        basket_mode=basket_mode,
    )

    st.divider()
    _render_recent_entries(filtered_df)

"""
Analytics dashboard — interactive Plotly charts with sidebar filters.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.charts import (
    build_basket_cost_chart,
    build_inflation_trend_chart,
    build_price_trend_chart,
    build_store_comparison_chart,
)
from src.data_processor import compute_analytics_summary, filter_dataframe, load_analytics_dataframe
from src.entry_service import ensure_database_ready


def _apply_multiselect_filter(
    df: pd.DataFrame,
    column: str,
    selected: list[str],
) -> pd.DataFrame:
    if not selected or df.empty:
        return df
    return df[df[column].isin(selected)].copy()


@st.cache_data(show_spinner=False, ttl=60)
def _load_data() -> pd.DataFrame:
    return load_analytics_dataframe()


def _render_sidebar_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Sidebar filters; returns filtered DataFrame and selected item for store chart."""
    st.sidebar.header("Chart filters")

    if df.empty:
        st.sidebar.info("Add price entries to enable filters.")
        return df, None

    min_d = df["date_recorded"].min().date()
    max_d = df["date_recorded"].max().date()

    col1, col2 = st.sidebar.columns(2)
    with col1:
        start = st.date_input("From", value=min_d, min_value=min_d, max_value=max_d)
    with col2:
        end = st.date_input("To", value=max_d, min_value=min_d, max_value=max_d)

    if start > end:
        st.sidebar.error("Start date must be on or before end date.")
        return df.iloc[0:0], None

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
        "Items (price trend)",
        options=items,
        default=items,
    )

    compare_item = st.sidebar.selectbox(
        "Item for store comparison",
        options=items,
        index=0,
    )

    basket_mode = st.sidebar.radio(
        "Basket cost view",
        options=["timeline", "monthly"],
        format_func=lambda m: "Over time" if m == "timeline" else "By month",
        horizontal=True,
    )

    filtered = filter_dataframe(
        df,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )
    filtered = _apply_multiselect_filter(filtered, "category_name", selected_categories)
    filtered = _apply_multiselect_filter(filtered, "store_name", selected_stores)

    st.session_state["dashboard_basket_mode"] = basket_mode
    st.session_state["dashboard_trend_items"] = selected_items
    return filtered, compare_item


def _render_kpi_row(df: pd.DataFrame) -> None:
    """Headline metrics above charts."""
    summary = compute_analytics_summary(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Observations", summary.observation_count)
    c2.metric("Items tracked", summary.item_count)
    if summary.basket_cost_latest is not None:
        c3.metric("Latest basket cost", f"{summary.basket_cost_latest:,.2f}")
    else:
        c3.metric("Latest basket cost", "—")
    if summary.monthly_inflation:
        last = summary.monthly_inflation[-1]
        if last.inflation_pct is not None:
            c4.metric(
                "Latest MoM inflation",
                f"{last.inflation_pct:+.2f}%",
                delta=f"{last.price_difference:+,.2f} basket",
                delta_color="inverse",
            )
        else:
            c4.metric("Latest MoM inflation", "—")
    elif summary.highest_increase:
        c4.metric(
            "Largest rise",
            f"{summary.highest_increase.item_name}",
            delta=f"{summary.highest_increase.percentage_change:+.1f}%",
            delta_color="inverse",
        )
    else:
        c4.metric("Largest rise", "—")


def render_dashboard_page() -> None:
    """Main dashboard with four interactive chart sections."""
    ensure_database_ready()

    st.title("Analytics Dashboard")
    st.caption(
        "Interactive views of unit prices, basket spend, store differences, and monthly inflation. "
        "Adjust filters in the sidebar."
    )

    raw_df = _load_data()
    filtered_df, compare_item = _render_sidebar_filters(raw_df)

    if raw_df.empty:
        st.warning(
            "No price data yet. Go to **Add Price Entry** to log your first observation, "
            "then return here."
        )
        return

    _render_kpi_row(filtered_df)

    if filtered_df.empty:
        st.warning("No records match the current filters. Widen the date range or clear selections.")
        return

    trend_items = st.session_state.get(
        "dashboard_trend_items",
        sorted(filtered_df["item_name"].unique()),
    )
    basket_mode = st.session_state.get("dashboard_basket_mode", "timeline")

    if st.sidebar.button("Refresh data", use_container_width=True):
        _load_data.clear()
        st.rerun()

    tab_trend, tab_basket, tab_store, tab_inflation = st.tabs(
        [
            "Price trends",
            "Basket cost",
            "Store comparison",
            "Inflation trend",
        ]
    )

    with tab_trend:
        st.markdown(
            "Normalized **unit price** (`price ÷ quantity`) over time. "
            "Compare shrinkflation-adjusted trends per item and store."
        )
        fig_trend = build_price_trend_chart(filtered_df, items=trend_items)
        st.plotly_chart(fig_trend, use_container_width=True)

    with tab_basket:
        st.markdown(
            "Estimated **total shelf spend** for your basket: sum of the latest package price "
            "paid per item at each point in time (or per month)."
        )
        fig_basket = build_basket_cost_chart(filtered_df, mode=basket_mode)
        st.plotly_chart(fig_basket, use_container_width=True)

    with tab_store:
        st.markdown(
            "Compare **unit prices across stores** for one item. "
            "Green = lowest; red = highest (when multiple stores)."
        )
        fig_store = build_store_comparison_chart(
            filtered_df,
            item_name=compare_item,
            metric="mean",
        )
        st.plotly_chart(fig_store, use_container_width=True)

        with st.expander("Latest price by store (same item)"):
            fig_latest = build_store_comparison_chart(
                filtered_df,
                item_name=compare_item,
                metric="latest",
            )
            st.plotly_chart(fig_latest, use_container_width=True)

    with tab_inflation:
        st.markdown(
            "**Month-over-month basket inflation** (%): change in total basket cost vs the prior month. "
            "Dotted line shows basket level."
        )
        fig_inflation = build_inflation_trend_chart(filtered_df)
        st.plotly_chart(fig_inflation, use_container_width=True)

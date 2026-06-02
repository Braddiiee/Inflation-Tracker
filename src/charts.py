"""
Plotly chart builders for the Grocery Inflation Tracker.

Pure visualization — no Streamlit imports. Accepts pandas DataFrames prepared by
`data_processor` and returns `plotly.graph_objects.Figure` instances.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data_processor import basket_cost_for_month, monthly_inflation_estimate

# Shared styling for a consistent dashboard look
CHART_TEMPLATE = "plotly_white"
COLOR_UP = "#c0392b"
COLOR_DOWN = "#27ae60"
COLOR_PRIMARY = "#2563eb"
COLOR_SECONDARY = "#7c3aed"
COLOR_NEUTRAL = "#64748b"

PALETTE = [
    "#2563eb",
    "#7c3aed",
    "#db2777",
    "#ea580c",
    "#ca8a04",
    "#16a34a",
    "#0891b2",
    "#4f46e5",
]


def _empty_figure(title: str, message: str = "No data for the current filters.") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        template=CHART_TEMPLATE,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            dict(
                text=message,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color=COLOR_NEUTRAL),
            )
        ],
        height=380,
    )
    return fig


def _base_layout(title: str, y_title: str, *, height: int = 420) -> dict:
    return dict(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=16)),
        template=CHART_TEMPLATE,
        hovermode="x unified",
        height=height,
        margin=dict(l=48, r=24, t=56, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title=y_title,
        xaxis_title="Date",
    )


def build_price_trend_chart(
    df: pd.DataFrame,
    *,
    items: Sequence[str] | None = None,
    show_unit_price: bool = True,
) -> go.Figure:
    """
  Interactive line chart: normalized unit price over time.

  One line per (item, store) pair. Hover shows package price and quantity.
    """
    if df.empty:
        return _empty_figure("Price trend (unit price)")

    data = df.copy()
    if items:
        allowed = {i.lower() for i in items}
        data = data[data["item_name"].str.lower().isin(allowed)]

    if data.empty:
        return _empty_figure("Price trend (unit price)", "No items match the selected filters.")

    data["series"] = data["item_name"] + " @ " + data["store_name"]
    y_col = "unit_price" if show_unit_price else "price_total"
    y_label = "Unit price" if show_unit_price else "Package price (total)"

    fig = go.Figure()
    for idx, (series_name, group) in enumerate(data.groupby("series", sort=True)):
        color = PALETTE[idx % len(PALETTE)]
        fig.add_trace(
            go.Scatter(
                x=group["date_recorded"],
                y=group[y_col],
                mode="lines+markers",
                name=series_name,
                line=dict(color=color, width=2),
                marker=dict(size=7),
                customdata=group[["price_total", "quantity", "unit_type", "store_name"]],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    f"{y_label}: %{{y:,.2f}}<br>"
                    "Paid: %{customdata[0]:,.2f} for %{customdata[1]:g} %{customdata[2]}<br>"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(**_base_layout("Price trend (unit price)", y_label))
    return fig


def basket_cost_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build cumulative basket cost snapshots at each observation date.

    At each date D: sum of latest price_total per item among logs on or before D.
    """
    if df.empty:
        return pd.DataFrame(columns=["date_recorded", "basket_cost", "item_count"])

    dates = sorted(df["date_recorded"].unique())
    rows: list[dict] = []
    for dt in dates:
        subset = df[df["date_recorded"] <= dt]
        latest = (
            subset.sort_values(["date_recorded", "log_id"])
            .groupby("item_name", as_index=False)
            .last()
        )
        rows.append(
            {
                "date_recorded": dt,
                "basket_cost": float(latest["price_total"].sum()),
                "item_count": len(latest),
            }
        )
    return pd.DataFrame(rows)


def build_basket_cost_chart(df: pd.DataFrame, *, mode: str = "timeline") -> go.Figure:
    """
    Basket cost visualization.

    mode='timeline': cumulative basket total over observation dates.
    mode='monthly': last basket total per calendar month.
    """
    if df.empty:
        return _empty_figure("Basket cost")

    if mode == "monthly":
        months = sorted(df["year_month"].dropna().unique())
        rows = []
        for month in months:
            cost = basket_cost_for_month(df, month)
            if cost is not None:
                rows.append({"month": str(month), "basket_cost": cost})
        series = pd.DataFrame(rows)
        if series.empty:
            return _empty_figure("Basket cost (monthly)", "Need observations in at least one month.")

        fig = go.Figure(
            go.Bar(
                x=series["month"],
                y=series["basket_cost"],
                marker_color=COLOR_PRIMARY,
                hovertemplate="Month: %{x}<br>Basket cost: %{y:,.2f}<extra></extra>",
            )
        )
        fig.update_layout(
            **_base_layout("Basket cost by month", "Total basket (last price per item)"),
        )
        fig.update_layout(xaxis_title="Month", xaxis_tickangle=-35)
        return fig

    series = basket_cost_timeseries(df)
    if series.empty:
        return _empty_figure("Basket cost")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=series["date_recorded"],
            y=series["basket_cost"],
            mode="lines+markers",
            name="Basket cost",
            line=dict(color=COLOR_PRIMARY, width=3),
            marker=dict(size=8),
            fill="tozeroy",
            fillcolor="rgba(37, 99, 235, 0.08)",
            customdata=series[["item_count"]],
            hovertemplate=(
                "Date: %{x|%Y-%m-%d}<br>"
                "Basket cost: %{y:,.2f}<br>"
                "Items in basket: %{customdata[0]}<br>"
                "<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        **_base_layout(
            "Basket cost over time",
            "Total basket (sum of latest shelf price per item)",
        )
    )
    return fig


def build_store_comparison_chart(
    df: pd.DataFrame,
    *,
    item_name: str | None = None,
    metric: str = "mean",
) -> go.Figure:
    """
    Bar chart comparing stores for one item (average or latest unit price).

    metric: 'mean' | 'latest'
    """
    if df.empty:
        return _empty_figure("Store comparison")

    data = df.copy()
    if item_name:
        data = data[data["item_name"].str.lower() == item_name.strip().lower()]

    if data.empty:
        return _empty_figure("Store comparison", "Select an item with data in this period.")

    if item_name is None:
        # Default: item with most observations
        item_name = data["item_name"].value_counts().idxmax()
        data = data[data["item_name"] == item_name]

    title_item = data["item_name"].iloc[0]

    if metric == "latest":
        agg = (
            data.sort_values(["date_recorded", "log_id"])
            .groupby("store_name", as_index=False)
            .last()[["store_name", "unit_price", "date_recorded", "price_total"]]
        )
        y_col = "unit_price"
        subtitle = "Latest unit price by store"
    else:
        agg = (
            data.groupby("store_name", as_index=False)
            .agg(
                unit_price=("unit_price", "mean"),
                observations=("log_id", "count"),
            )
            .sort_values("unit_price", ascending=False)
        )
        y_col = "unit_price"
        subtitle = "Average unit price by store"

    if agg.empty:
        return _empty_figure("Store comparison")

    colors = [
        COLOR_DOWN if v == agg[y_col].min() else COLOR_UP if v == agg[y_col].max() else COLOR_PRIMARY
        for v in agg[y_col]
    ] if len(agg) > 1 else [COLOR_PRIMARY]

    fig = go.Figure(
        go.Bar(
            x=agg["store_name"],
            y=agg[y_col],
            marker_color=colors,
            hovertemplate="Store: %{x}<br>Unit price: %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_base_layout(f"Store comparison — {title_item}", "Unit price"),
    )
    fig.update_layout(xaxis_title="Store", xaxis_tickangle=-25)
    fig.add_annotation(
        text=subtitle,
        xref="paper",
        yref="paper",
        x=0,
        y=1.08,
        showarrow=False,
        font=dict(size=11, color=COLOR_NEUTRAL),
        xanchor="left",
    )
    return fig


def build_inflation_trend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Month-over-month basket inflation rate (%).

  Bars colored green (deflation) or red (inflation). Secondary trace: basket cost level.
    """
    rows = monthly_inflation_estimate(df)
    if not rows:
        return _empty_figure(
            "Monthly inflation trend",
            "Need price logs in at least two different months.",
        )

    inflation_df = pd.DataFrame(
        [
            {
                "month": r.month,
                "inflation_pct": r.inflation_pct,
                "basket_cost": r.basket_cost,
                "previous_basket_cost": r.previous_basket_cost,
            }
            for r in rows
            if r.inflation_pct is not None
        ]
    )

    if inflation_df.empty:
        return _empty_figure("Monthly inflation trend", "Could not compute month-over-month rates.")

    bar_colors = [
        COLOR_UP if v > 0 else COLOR_DOWN if v < 0 else COLOR_NEUTRAL
        for v in inflation_df["inflation_pct"]
    ]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=inflation_df["month"],
            y=inflation_df["inflation_pct"],
            name="MoM inflation %",
            marker_color=bar_colors,
            hovertemplate=(
                "Month: %{x}<br>"
                "Inflation: %{y:.2f}%<br>"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=inflation_df["month"],
            y=inflation_df["basket_cost"],
            name="Basket cost",
            mode="lines+markers",
            line=dict(color=COLOR_SECONDARY, width=2, dash="dot"),
            marker=dict(size=7),
            hovertemplate="Month: %{x}<br>Basket: %{y:,.2f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(text="Monthly inflation trend", x=0, xanchor="left", font=dict(size=16)),
        template=CHART_TEMPLATE,
        hovermode="x unified",
        height=440,
        margin=dict(l=48, r=48, t=56, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        barmode="group",
    )
    fig.update_yaxes(title_text="Inflation (%)", secondary_y=False, zeroline=True, zerolinecolor="#e2e8f0")
    fig.update_yaxes(title_text="Basket cost", secondary_y=True, showgrid=False)
    fig.update_xaxes(title_text="Month", tickangle=-35)
    fig.add_hline(y=0, line_dash="dash", line_color=COLOR_NEUTRAL, line_width=1, secondary_y=False)

    return fig

"""
Pandas analytics engine for grocery price and basket inflation metrics.

All monetary comparisons use **unit price** (price_total / quantity) unless
the metric explicitly targets shelf spend (basket cost uses price_total).

Charts and Streamlit stay in separate modules; this file is calculation-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from src.record_service import PriceRecordRow, fetch_all_records

# ---------------------------------------------------------------------------
# Core formulas (pure functions)
# ---------------------------------------------------------------------------


def price_difference(old_price: float, new_price: float) -> float:
    """
    Absolute change between two unit prices.

    Formula: ΔP = P_new − P_old
    Positive → price went up; negative → price went down.
    """
    return float(new_price) - float(old_price)


def percentage_change(old_price: float, new_price: float) -> float | None:
    """
    Relative change as a percentage.

    Formula: %Δ = ((P_new − P_old) / P_old) × 100
    Returns None when P_old is zero (undefined).
    """
    old_price = float(old_price)
    new_price = float(new_price)
    if old_price == 0:
        return None
    return price_difference(old_price, new_price) / old_price * 100.0


def average_price(prices: Sequence[float]) -> float | None:
    """
    Arithmetic mean of unit prices.

    Formula: P̄ = (Σ P_i) / n
    Returns None when the input series is empty.
    """
    if not prices:
        return None
    return float(sum(prices) / len(prices))


def median_price(prices: Sequence[float]) -> float | None:
    """
    Median unit price (robust to one-off spikes).

    Formula: middle value of sorted P_i (average of two middles when n is even).
    Returns None when the input series is empty.
    """
    if not prices:
        return None
    series = sorted(float(p) for p in prices)
    n = len(series)
    mid = n // 2
    if n % 2 == 1:
        return series[mid]
    return (series[mid - 1] + series[mid]) / 2.0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def records_to_dataframe(rows: Sequence[PriceRecordRow]) -> pd.DataFrame:
    """Convert service-layer rows into an analytics-ready DataFrame."""
    if not rows:
        return pd.DataFrame(
            columns=[
                "log_id",
                "item_name",
                "store_name",
                "category_name",
                "price_total",
                "quantity",
                "unit_type",
                "date_recorded",
                "notes",
                "unit_price",
            ]
        )
    data = [
        {
            "log_id": r.log_id,
            "item_name": r.item_name,
            "store_name": r.store_name,
            "category_name": r.category_name,
            "price_total": r.price_total,
            "quantity": r.quantity,
            "unit_type": r.unit_type,
            "date_recorded": r.date_recorded,
            "notes": r.notes,
            "unit_price": r.unit_price,
        }
        for r in rows
    ]
    return _enrich_dataframe(pd.DataFrame(data))


def load_analytics_dataframe(
    db_path: Path | None = None,
    *,
    search: str = "",
) -> pd.DataFrame:
    """Load all matching price logs from SQLite into a DataFrame."""
    rows = fetch_all_records(
        search=search,
        sort_by="date_recorded",
        sort_order="asc",
        db_path=db_path,
    )
    return records_to_dataframe(rows)


def _enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns and sort chronologically."""
    if df.empty:
        return df
    out = df.copy()
    out["date_recorded"] = pd.to_datetime(out["date_recorded"])
    out["unit_price"] = out["price_total"] / out["quantity"]
    out["year_month"] = out["date_recorded"].dt.to_period("M")
    return out.sort_values(["date_recorded", "log_id"]).reset_index(drop=True)


def filter_dataframe(
    df: pd.DataFrame,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    item_name: str | None = None,
    store_name: str | None = None,
    category_name: str | None = None,
) -> pd.DataFrame:
    """Subset analytics data by optional dimensions."""
    if df.empty:
        return df
    mask = pd.Series(True, index=df.index)
    if start_date:
        mask &= df["date_recorded"] >= pd.Timestamp(start_date)
    if end_date:
        mask &= df["date_recorded"] <= pd.Timestamp(end_date)
    if item_name:
        mask &= df["item_name"].str.lower() == item_name.strip().lower()
    if store_name:
        mask &= df["store_name"].str.lower() == store_name.strip().lower()
    if category_name:
        mask &= df["category_name"].str.lower() == category_name.strip().lower()
    return df.loc[mask].copy()


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ItemPriceChange:
    """First-to-last unit price change for one item in a period."""

    item_name: str
    store_name: str
    start_date: str
    end_date: str
    start_unit_price: float
    end_unit_price: float
    price_difference: float
    percentage_change: float | None


@dataclass(frozen=True)
class ItemExtremeChange:
    """Largest rise or fall by percentage for one item."""

    item_name: str
    store_name: str
    start_date: str
    end_date: str
    start_unit_price: float
    end_unit_price: float
    price_difference: float
    percentage_change: float


@dataclass(frozen=True)
class MonthlyInflationRow:
    """Month-over-month basket inflation estimate."""

    month: str
    basket_cost: float
    previous_basket_cost: float
    price_difference: float
    inflation_pct: float | None


@dataclass(frozen=True)
class AnalyticsSummary:
    """Bundle of headline metrics for a filtered dataset."""

    observation_count: int
    item_count: int
    average_unit_price: float | None
    median_unit_price: float | None
    basket_cost_latest: float | None
    highest_increase: ItemExtremeChange | None
    highest_decrease: ItemExtremeChange | None
    monthly_inflation: list[MonthlyInflationRow]
    item_changes: list[ItemPriceChange]


# ---------------------------------------------------------------------------
# Basket & period helpers
# ---------------------------------------------------------------------------


def _latest_per_item(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent row per item_name (by date, then log_id)."""
    if df.empty:
        return df
    return (
        df.sort_values(["date_recorded", "log_id"])
        .groupby("item_name", as_index=False)
        .last()
    )


def _latest_per_item_store(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent row per (item_name, store_name) pair."""
    if df.empty:
        return df
    return (
        df.sort_values(["date_recorded", "log_id"])
        .groupby(["item_name", "store_name"], as_index=False)
        .last()
    )


def basket_cost(
    df: pd.DataFrame,
    *,
    as_of_date: str | None = None,
) -> float | None:
    """
    Estimated total shelf spend for the basket.

    Formula: Σ price_total_i for the latest observation of each item on or before
    as_of_date. Uses actual package prices paid (not normalized unit price), so
    it reflects what a shopper last paid per product line.
    Returns None when no rows qualify.
    """
    if df.empty:
        return None
    subset = df
    if as_of_date:
        subset = subset[subset["date_recorded"] <= pd.Timestamp(as_of_date)]
    if subset.empty:
        return None
    latest = _latest_per_item(subset)
    return float(latest["price_total"].sum())


def basket_cost_for_month(df: pd.DataFrame, month: str | pd.Period) -> float | None:
    """
    Basket cost using only observations recorded in a calendar month.

    Formula: for each item, take its last log in that month; sum price_total.
    Items with no observation in the month are excluded.
    """
    if df.empty:
        return None
    period = pd.Period(month, freq="M")
    month_df = df[df["year_month"] == period]
    if month_df.empty:
        return None
    latest = _latest_per_item(month_df)
    return float(latest["price_total"].sum())


# ---------------------------------------------------------------------------
# Item-level change metrics
# ---------------------------------------------------------------------------


def item_price_changes(
    df: pd.DataFrame,
    *,
    by_store: bool = True,
) -> list[ItemPriceChange]:
    """
    First vs last unit price per item (and optionally per store) in the dataset.

    Requires at least two observations per group.
    """
    if df.empty:
        return []

    group_cols = ["item_name", "store_name"] if by_store else ["item_name"]
    changes: list[ItemPriceChange] = []

    for keys, group in df.groupby(group_cols, sort=False):
        if len(group) < 2:
            continue
        first = group.iloc[0]
        last = group.iloc[-1]
        start_p = float(first["unit_price"])
        end_p = float(last["unit_price"])
        item = first["item_name"] if not by_store else keys[0]
        store = first["store_name"] if not by_store else keys[1]
        changes.append(
            ItemPriceChange(
                item_name=item,
                store_name=store,
                start_date=first["date_recorded"].strftime("%Y-%m-%d"),
                end_date=last["date_recorded"].strftime("%Y-%m-%d"),
                start_unit_price=start_p,
                end_unit_price=end_p,
                price_difference=price_difference(start_p, end_p),
                percentage_change=percentage_change(start_p, end_p),
            )
        )
    return changes


def highest_increase(df: pd.DataFrame, *, by_store: bool = True) -> ItemExtremeChange | None:
    """
    Item with the largest positive percentage unit-price change.

    Formula: argmax(%Δ) over items with at least two observations and %Δ > 0.
    """
    candidates = [
        c
        for c in item_price_changes(df, by_store=by_store)
        if c.percentage_change is not None and c.percentage_change > 0
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda c: c.percentage_change or 0.0)
    return ItemExtremeChange(
        item_name=best.item_name,
        store_name=best.store_name,
        start_date=best.start_date,
        end_date=best.end_date,
        start_unit_price=best.start_unit_price,
        end_unit_price=best.end_unit_price,
        price_difference=best.price_difference,
        percentage_change=best.percentage_change,  # type: ignore[arg-type]
    )


def highest_decrease(df: pd.DataFrame, *, by_store: bool = True) -> ItemExtremeChange | None:
    """
    Item with the largest negative percentage unit-price change (biggest drop).

    Formula: argmin(%Δ) over items with at least two observations and %Δ < 0.
    """
    candidates = [
        c
        for c in item_price_changes(df, by_store=by_store)
        if c.percentage_change is not None and c.percentage_change < 0
    ]
    if not candidates:
        return None
    worst = min(candidates, key=lambda c: c.percentage_change or 0.0)
    return ItemExtremeChange(
        item_name=worst.item_name,
        store_name=worst.store_name,
        start_date=worst.start_date,
        end_date=worst.end_date,
        start_unit_price=worst.start_unit_price,
        end_unit_price=worst.end_unit_price,
        price_difference=worst.price_difference,
        percentage_change=worst.percentage_change,  # type: ignore[arg-type]
    )


def average_unit_price(df: pd.DataFrame) -> float | None:
    """Mean unit price across all observations in df."""
    if df.empty:
        return None
    return average_price(df["unit_price"].tolist())


def median_unit_price(df: pd.DataFrame) -> float | None:
    """Median unit price across all observations in df."""
    if df.empty:
        return None
    return median_price(df["unit_price"].tolist())


def monthly_inflation_estimate(df: pd.DataFrame) -> list[MonthlyInflationRow]:
    """
    Month-over-month basket inflation estimate.

    For each consecutive pair of months (in order):
      - B_m   = basket_cost_for_month(month m)
      - %Inf_m = ((B_m − B_{m−1}) / B_{m−1}) × 100

  Only months with at least one priced item contribute. Requires ≥2 months of data.
    """
    if df.empty:
        return []

    months = sorted(df["year_month"].dropna().unique())
    if len(months) < 2:
        return []

    rows: list[MonthlyInflationRow] = []
    prev_cost: float | None = None
    prev_month: str | None = None

    for month in months:
        cost = basket_cost_for_month(df, month)
        if cost is None:
            continue
        month_str = str(month)
        if prev_cost is not None and prev_month is not None:
            rows.append(
                MonthlyInflationRow(
                    month=month_str,
                    basket_cost=cost,
                    previous_basket_cost=prev_cost,
                    price_difference=price_difference(prev_cost, cost),
                    inflation_pct=percentage_change(prev_cost, cost),
                )
            )
        prev_cost = cost
        prev_month = month_str

    return rows


@dataclass(frozen=True)
class BasketPeriodChange:
    """Basket cost now vs a prior point in time."""

    current_cost: float | None
    previous_cost: float | None
    price_difference: float | None
    percent_change: float | None
    current_as_of: str | None
    previous_as_of: str | None


@dataclass(frozen=True)
class DashboardMetrics:
    """Headline KPIs for the product dashboard."""

    current_basket_cost: float | None
    weekly_change: BasketPeriodChange
    monthly_change: BasketPeriodChange
    highest_inflation_item: ItemExtremeChange | None
    lowest_inflation_item: ItemExtremeChange | None
    observation_count: int
    item_count: int
    average_unit_price: float | None


def basket_cost_change(
    df: pd.DataFrame,
    *,
    days: int,
    reference_date: pd.Timestamp | None = None,
) -> BasketPeriodChange:
    """
    Compare basket cost at reference_date vs `days` earlier.

    Uses basket_cost(as_of) at each anchor so the basket reflects latest
    known price per item on or before each date.
    """
    if df.empty:
        return BasketPeriodChange(None, None, None, None, None, None)

    ref = reference_date if reference_date is not None else df["date_recorded"].max()
    ref_str = ref.strftime("%Y-%m-%d")
    prior = ref - pd.Timedelta(days=days)
    prior_str = prior.strftime("%Y-%m-%d")

    current = basket_cost(df, as_of_date=ref_str)
    previous = basket_cost(df, as_of_date=prior_str)

    if current is None:
        return BasketPeriodChange(None, previous, None, None, ref_str, prior_str)

    diff = price_difference(previous, current) if previous is not None else None
    pct = percentage_change(previous, current) if previous is not None else None

    return BasketPeriodChange(
        current_cost=current,
        previous_cost=previous,
        price_difference=diff,
        percent_change=pct,
        current_as_of=ref_str,
        previous_as_of=prior_str,
    )


def compute_dashboard_metrics(
    df: pd.DataFrame,
    *,
    by_store: bool = True,
) -> DashboardMetrics:
    """All dashboard card values for the filtered dataset."""
    ref_date = df["date_recorded"].max() if not df.empty else None
    return DashboardMetrics(
        current_basket_cost=basket_cost(
            df,
            as_of_date=ref_date.strftime("%Y-%m-%d") if ref_date is not None else None,
        ),
        weekly_change=basket_cost_change(df, days=7, reference_date=ref_date),
        monthly_change=basket_cost_change(df, days=30, reference_date=ref_date),
        highest_inflation_item=highest_increase(df, by_store=by_store),
        lowest_inflation_item=highest_decrease(df, by_store=by_store),
        observation_count=len(df),
        item_count=int(df["item_name"].nunique()) if not df.empty else 0,
        average_unit_price=average_unit_price(df),
    )


def compute_analytics_summary(
    df: pd.DataFrame,
    *,
    by_store: bool = True,
    as_of_date: str | None = None,
) -> AnalyticsSummary:
    """
    Compute all headline analytics for a filtered DataFrame.

    Intended for dashboards and reports; safe on empty input.
    """
    return AnalyticsSummary(
        observation_count=len(df),
        item_count=int(df["item_name"].nunique()) if not df.empty else 0,
        average_unit_price=average_unit_price(df),
        median_unit_price=median_unit_price(df),
        basket_cost_latest=basket_cost(df, as_of_date=as_of_date),
        highest_increase=highest_increase(df, by_store=by_store),
        highest_decrease=highest_decrease(df, by_store=by_store),
        monthly_inflation=monthly_inflation_estimate(df),
        item_changes=item_price_changes(df, by_store=by_store),
    )

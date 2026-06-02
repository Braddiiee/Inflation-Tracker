# Analytics Engine — Calculation Reference

This document explains every metric implemented in `src/data_processor.py`.  
**No charts** — numbers only, consumed later by the dashboard.

---

## Normalized unit price (foundation)

Before comparing observations, each log is converted to a **unit price**:

```
unit_price = price_total / quantity
```

Example: $280 for 0.5 kg → **560 per kg**.  
Shrinkflation (smaller packs) is handled because `quantity` and `unit_type` are stored separately.

---

## 1. Price difference (ΔP)

**Function:** `price_difference(old_price, new_price)`

```
ΔP = P_new − P_old
```

| Sign | Meaning |
|------|---------|
| Positive | Price increased |
| Negative | Price decreased |
| Zero | No change |

**Example:** Rice was 500/kg, now 560/kg → **ΔP = +60**.

---

## 2. Percentage change (%Δ)

**Function:** `percentage_change(old_price, new_price)`

```
%Δ = ((P_new − P_old) / P_old) × 100
```

**Example:** (560 − 500) / 500 × 100 = **+12%**.

Returns `None` if `P_old = 0` (division undefined).

---

## 3. Average price (P̄)

**Function:** `average_price(prices)` / `average_unit_price(df)`

```
P̄ = (Σ unit_price_i) / n
```

Arithmetic mean of **unit prices** over all observations in the filtered set.  
Sensitive to outliers (one expensive log pulls the average up).

**Example:** Unit prices [500, 560, 12] → **P̄ = 357.33**.

---

## 4. Median price

**Function:** `median_price(prices)` / `median_unit_price(df)`

Middle value of sorted unit prices. For even *n*, average of the two middle values.  
More robust than the mean when one item spikes.

**Example:** [500, 560, 12] → sorted [12, 500, 560] → **median = 500**.

---

## 5. Basket cost

**Function:** `basket_cost(df, as_of_date=None)`

```
Basket = Σ price_total_i
```

For each **item_name**, take the **latest** observation on or before `as_of_date`, then sum the **package prices** (`price_total`) actually paid.

This answers: *“What did my basket cost the last time I bought each item?”*  
It uses shelf spend, not unit price, because households pay per package at checkout.

**Example (as of 2026-05-10):**

| Item | Latest price_total |
|------|-------------------|
| Rice | 280.00 |
| Milk | 12.00 |
| **Basket** | **292.00** |

---

## 6. Highest increase

**Function:** `highest_increase(df)`

For each item (and store, if `by_store=True`) with **≥ 2** logs in the period:

1. `P_start` = unit price on earliest date  
2. `P_end` = unit price on latest date  
3. Compute `%Δ`

Return the item with the **largest positive** `%Δ`.

**Example:** Rice +12%, Milk +5% → **Highest increase = Rice (+12%)**.

---

## 7. Highest decrease

**Function:** `highest_decrease(df)`

Same as above, but return the item with the **most negative** `%Δ` (largest price drop).

**Example:** Bread −8%, Eggs −3% → **Highest decrease = Bread (−8%)**.

---

## 8. Monthly inflation estimate

**Function:** `monthly_inflation_estimate(df)`

For each calendar month *m* with data:

1. **B_m** = `basket_cost_for_month(m)` — sum of last `price_total` per item **within that month**
2. For consecutive months:  
   `%Inflation_m = ((B_m − B_{m−1}) / B_{m−1}) × 100`

**Example:**

| Month | Basket B_m | MoM % |
|-------|-----------|-------|
| 2026-04 | 270.00 | — |
| 2026-05 | 292.00 | **+8.15%** |

**Limitations (MVP):**

- Items not purchased in a month are excluded from that month’s basket (no carry-forward).
- Mixed units across months still compare shelf totals; use consistent shopping lists for best results.

---

## Aggregated report

**Function:** `compute_analytics_summary(df)`

Returns an `AnalyticsSummary` dataclass with all metrics above for one filtered dataset.

---

## Filtering

Use `filter_dataframe(df, start_date=..., end_date=..., item_name=..., store_name=..., category_name=...)` before computing metrics.

---

## Data loading

| Function | Use |
|----------|-----|
| `load_analytics_dataframe()` | Load from SQLite |
| `records_to_dataframe(rows)` | Build from in-memory rows |

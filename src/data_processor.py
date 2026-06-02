"""
Pandas analytics and normalization layer.

Responsibilities (future):
- Load query results into DataFrames
- Compute normalized_price (e.g., price per 100 ml / per kg)
- Basket inflation rate over date ranges
- Prepare series for Plotly (trend, store comparison, summary)

Keeps visualization-agnostic calculations separate from Streamlit and SQL.
"""

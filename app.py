"""
Grocery Inflation Tracker — application entry point.

Run: streamlit run app.py

Use the sidebar to open **Add Price Entry** or **Manage Records**.
Analytics dashboard is not implemented yet.
"""

import streamlit as st

st.set_page_config(
    page_title="Grocery Inflation Tracker",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Grocery Inflation Tracker")
st.markdown(
    """
Track local grocery prices, manage your records, and prepare for basket inflation insights.

| Page | Description |
|------|-------------|
| **Add Price Entry** | Log a new item price (item, store, category, date, notes). |
| **Manage Records** | Search, sort, paginate, edit, or delete saved entries. |

Select a page from the **sidebar** to get started.
"""
)

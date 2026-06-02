"""
Grocery Inflation Tracker — application entry point.

Run: streamlit run app.py

Use the sidebar to open **Add Price Entry**, **Manage Records**, or **Dashboard**.
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
Track local grocery prices, manage your records, and monitor basket inflation.

| Page | Description |
|------|-------------|
| **Dashboard** | KPI cards, charts, filters, and recent entries. |
| **Add Price Entry** | Log a new item price (item, store, category, date, notes). |
| **Manage Records** | Search, sort, paginate, edit, or delete saved entries. |

**Tip:** Open **Dashboard** in the sidebar for basket cost, weekly/monthly change, and inflation insights.
"""
)

if st.button("Open Dashboard", type="primary"):
    st.switch_page("pages/0_Dashboard.py")

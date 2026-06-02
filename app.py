"""
Grocery Inflation Tracker — application entry point.

MVP: Add Price Entry only (dashboard not yet implemented).
Run: streamlit run app.py
"""

import streamlit as st

from src.entry_view import render_add_price_page

st.set_page_config(
    page_title="Add Price Entry | Grocery Inflation Tracker",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed",
)

render_add_price_page()

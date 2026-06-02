"""
Add Price Entry (Streamlit multi-page shim).

Hidden from navigation when using `streamlit run app.py` as the main entry.
Use app.py for the single-page MVP experience.
"""

from src.entry_view import render_add_price_page

render_add_price_page()

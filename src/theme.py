"""
Application theme (light / dark) for Streamlit.

Inject CSS via apply_theme() on every page load.
"""

from __future__ import annotations

import streamlit as st

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_KEY = "app_theme"


def get_theme() -> str:
    """Current theme from session state."""
    return st.session_state.get(THEME_KEY, THEME_LIGHT)


def set_theme(theme: str) -> None:
    """Persist theme choice."""
    st.session_state[THEME_KEY] = theme if theme in (THEME_LIGHT, THEME_DARK) else THEME_LIGHT


def apply_theme() -> None:
    """Inject CSS overrides for dark mode (no-op for light)."""
    if get_theme() != THEME_DARK:
        return

    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }
        [data-testid="stSidebar"] {
            background-color: #161b22;
        }
        [data-testid="stMetric"] {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 0.5rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #30363d !important;
        }
        .stMarkdown, p, label, span {
            color: #e6edf3;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

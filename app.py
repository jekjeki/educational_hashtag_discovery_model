"""
app.py
Entry point HashBI Dashboard
Handles page config, CSS injection, sidebar, dan routing.

Jalankan dengan:
    streamlit run app.py
"""

import streamlit as st
from components.sidebar import render_sidebar
from core.data_service import ensure_session_state_initialized
from config import (
    DASHBOARD_CONFIG,
    ASSETS_DIR,
)

# ─────────────────────────────────────────────
# PAGE CONFIG — harus dipanggil pertama
# ─────────────────────────────────────────────
st.set_page_config(
    page_title=DASHBOARD_CONFIG["title"],
    page_icon=DASHBOARD_CONFIG["page_icon"],
    layout=DASHBOARD_CONFIG["layout"],
    initial_sidebar_state=DASHBOARD_CONFIG["initial_sidebar_state"],
)

# ─────────────────────────────────────────────
# INJECT CUSTOM CSS
# ─────────────────────────────────────────────
def load_css():
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# ─────────────────────────────────────────────
# SESSION STATE & INIT DATA
# ─────────────────────────────────────────────
# Initialize session state dan auto-load data dari file
ensure_session_state_initialized()


render_sidebar()

# ─────────────────────────────────────────────
# MAIN — cek data, redirect ke overview
# ─────────────────────────────────────────────
meta = st.session_state.metadata

if not meta:
    st.warning(
        "Data processed belum tersedia. Jalankan dulu script berikut:"
    )
    st.code("python generate_processed_data.py", language="bash")
    st.stop()

# Redirect ke overview sebagai halaman utama
st.switch_page("pages/01_overview.py")
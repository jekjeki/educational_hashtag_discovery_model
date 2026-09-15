import streamlit as st
from config import UNIVERSITIES, ASSETS_DIR

def load_shared_css():
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:

        # Pilih Universitas
        st.markdown(
            '<div class="sidebar-section-label">Universitas</div>',
            unsafe_allow_html=True
        )

        # Semua Universitas
        is_all = st.session_state.selected_university == "all"
        if st.button(
            "Semua Universitas",
            key="btn_all",
            use_container_width=True,
            type="primary" if is_all else "secondary",
        ):
            st.session_state.selected_university = "all"
            st.rerun()

        # Per universitas dengan dot warna
        for key, cfg in UNIVERSITIES.items():
            color    = cfg["color"]
            name     = cfg["name_short"]
            is_active = st.session_state.selected_university == key

            label = f"{name}"
            if st.button(
                label,
                key=f"btn_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.selected_university = key
                st.rerun()

        # Menu Navigasi
        st.markdown(
            '<div class="sidebar-section-label" style="margin-top:1.5rem">Menu</div>',
            unsafe_allow_html=True
        )

        st.page_link("pages/01_overview.py",          label="Overview")
        st.page_link("pages/02_network_graph.py",     label="Network Graph")
        st.page_link("pages/03_association_rules.py", label="Association Rules")
        st.page_link("pages/04_perbandingan.py",      label="Perbandingan")
        st.page_link("pages/05_rekomendasi.py",       label="Rekomendasi")
        st.page_link("pages/06_analisis_konten.py",   label="Analisis Konten")

        # Footer Sidebar
        st.markdown("---")
        meta        = st.session_state.metadata
        total_posts = meta.get("total_posts", 0)

        st.markdown(f"""
        <div style="font-size:11px;color:var(--text-muted);line-height:1.6">
            <div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px">
                Total Data
            </div>
            <div style="font-size:22px;font-weight:700;color:var(--text-primary);margin-bottom:2px">
                {total_posts:,}
            </div>
            konten Instagram 2025
            <div style="margin-top:6px">
                <span style="background:rgba(59,130,246,0.15);color:#3b82f6;
                padding:2px 8px;border-radius:20px;font-size:10px;font-weight:600">
                QS WUR</span>
                &nbsp;
                <span style="background:rgba(139,92,246,0.15);color:#8b5cf6;
                padding:2px 8px;border-radius:20px;font-size:10px;font-weight:600">
                Apriori</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
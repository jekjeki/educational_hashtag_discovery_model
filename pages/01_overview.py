"""
pages/01_overview.py
Halaman Overview — ringkasan analisis hashtag dari 7 universitas.
"""

import streamlit as st

# Page config harus dipanggil pertama sebelum import lainnya
st.set_page_config(
    page_title="Overview | HashBI",
    page_icon="#",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
import plotly.io as pio

from config import UNIVERSITIES, APRIORI_CONFIG, ASSETS_DIR
from components.sidebar import render_sidebar
from components.metric_card import (
    render_metric_row,
    render_page_header,
    render_top_rules,
    render_methodology_card,
)
from components.charts import plot_bar_hashtag_frequency, plot_bar_comparison
from core.data_service import (
    ensure_session_state_initialized,
    get_selected_university,
    get_rules,
    get_metadata,
    get_post_count_per_university,
    get_hashtag_frequency,
    get_engagement_summary,
    get_university_display_info,
    get_min_support_used,
)


def init_page():
    """Inisialisasi layout, CSS, dan sidebar."""
    ensure_session_state_initialized()
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    render_sidebar()


def render_metrics_section(meta: dict, selected_key: str):
    """Render metric cards row."""
    total_posts = meta.get("total_posts", 0)
    total_hashtag = meta.get("total_unique_hashtags", 0)
    total_rules = meta.get("total_rules_all", 0)
    avg_lift = meta.get("avg_lift", 0)
    max_conf = meta.get("max_confidence", 0)
    min_sup = get_min_support_used()

    render_metric_row([
        {
            "label": "Total Post",
            "value": f"{total_posts:,}",
            "sub": f"{len(UNIVERSITIES)} universitas · 2025" if selected_key == "all" else "posts",
            "accent_color": "#3b82f6",
        },
        {
            "label": "Hashtag Unik",
            "value": f"{total_hashtag:,}",
            "sub": "setelah preprocessing",
            "accent_color": "#8b5cf6",
        },
        {
            "label": "Association Rules",
            "value": f"{total_rules:,}",
            "sub": f"min. support {min_sup:.2f}",
            "accent_color": "#10b981",
        },
        {
            "label": "Avg. Lift",
            "value": f"{avg_lift:.2f}",
            "sub": "rata-rata seluruh rules",
            "accent_color": "#f59e0b",
        },
        {
            "label": "Max Confidence",
            "value": f"{max_conf:.2f}",
            "sub": "rule terkuat",
            "accent_color": "#f43f5e",
        },
    ])


def render_engagement_and_rules(rules: list):
    """Render row: Engagement Trend + Top Association Rules."""
    col_left, col_right = st.columns([1.2, 1], gap="medium")

    with col_left:
        engagement_df = get_engagement_summary()
        if not engagement_df.empty and "avg_likes" in engagement_df.columns:
            engagement_data = {
                row["university_key"]: round(float(row["avg_likes"]), 0)
                for _, row in engagement_df.iterrows()
                if row["university_key"] in UNIVERSITIES
            }

            fig = plot_bar_comparison(
                data=engagement_data,
                metric_label="Rata-rata Likes per Post",
                title="",
            )
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=30), height=240)
            chart_html = pio.to_html(fig, full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False})

            html_content = f"""
            <div class="chart-card">
                <h4 class="card-title">Tren Engagement (Avg. Likes)</h4>
                <div class="chart-wrapper">{chart_html}</div>
            </div>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                * {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ margin: 0; background: transparent; }}
                .chart-card {{
                    background: #fff;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                    border: 1px solid #e2e8f0;
                }}
                .card-title {{
                    font-size: 15px;
                    font-weight: 600;
                    color: #0f172a;
                    margin: 0 0 16px 0;
                    letter-spacing: -0.01em;
                }}
                .chart-wrapper {{
                    width: 100%;
                    overflow: hidden;
                }}
                .js-plotly-plot, .plotly {{ width: 100% !important; }}
            </style>
            """
            st.iframe(html_content, height=320)
        else:
            st.markdown("<h4 class='dashboard-card-title'>Tren Engagement (Avg. Likes)</h4>", unsafe_allow_html=True)
            st.info("Tren engagement akan tampil setelah generate_processed_data.py dijalankan.")

    with col_right:
        # Generate top rules HTML with styled button
        if rules:
            top_rules = sorted(rules, key=lambda x: x.get("lift", 0), reverse=True)[:5]
            rules_html = ""

            for rule in top_rules:
                antecedent = rule.get("antecedents_str", "")
                consequent = rule.get("consequents_str", "")
                lift = rule.get("lift", 0)

                # Determine badge class based on lift value
                if lift >= 2.5:
                    badge_class = "lift-high"
                elif lift >= 1.5:
                    badge_class = "lift-mid"
                else:
                    badge_class = "lift-normal"

                rules_html += f"""
                <div class="rule-item">
                    <span class="rule-text">
                        {antecedent}
                        <span class="rule-arrow">→</span>
                        {consequent}
                    </span>
                    <span class="lift-badge {badge_class}">lift {lift:.2f}</span>
                </div>
                """

            # Build full HTML card with embedded button
            rules_card_html = f"""
            <div class="rules-card">
                <div class="card-header">
                    <h4 class="dashboard-card-title">Top 5 Association Rules</h4>
                    <div class="info-wrapper">
                        <span class="info-icon">i</span>
                        <div class="tooltip">
                            <strong>Apa itu Lift?</strong><br/>
                            Lift mengukur seberapa kuat hubungan antara antecedent dan consequent
                            dibandingkan dengan jika keduanya saling bebas.<br/><br/>
                            <span style="color:#4ade80">• Lift &gt; 1:</span> korelasi positif<br/>
                            <span style="color:#facc15">• Lift = 1:</span> tidak ada korelasi<br/>
                            <span style="color:#94a3b8">• Lift &lt; 1:</span> korelasi negatif
                        </div>
                    </div>
                </div>
                {rules_html}
            </div>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                * {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ margin: 0; }}
                .rules-card {{
                    background: #fff;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    margin-bottom: 0;
                }}
                .card-header {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 1rem;
                }}
                .dashboard-card-title {{
                    font-size: 15px;
                    font-weight: 600;
                    color: #0f172a;
                    margin: 0;
                    letter-spacing: -0.01em;
                }}
                .rule-item {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px 0;
                    border-bottom: 1px solid #f1f5f9;
                }}
                .rule-item:last-of-type {{
                    border-bottom: none;
                }}
                .rule-text {{
                    font-size: 13px;
                    color: #334155;
                    font-weight: 500;
                }}
                .rule-arrow {{
                    color: #94a3b8;
                    margin: 0 6px;
                }}
                .lift-badge {{
                    font-size: 12px;
                    font-weight: 600;
                    padding: 5px 8px;
                    border-radius: 4px;
                }}
                .lift-high {{ background: #dcfce7; color: #16a34a; }}
                .lift-mid {{ background: #fef9c3; color: #ca8a04; }}
                .lift-normal {{ background: #f1f5f9; color: #64748b; }}
                .info-wrapper {{
                    position: relative;
                }}
                .info-icon {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 16px;
                    height: 16px;
                    font-size: 10px;
                    font-weight: 700;
                    color: #94a3b8;
                    border: 1.5px solid #cbd5e1;
                    border-radius: 50%;
                    cursor: help;
                    transition: all 0.2s;
                }}
                .info-icon:hover {{
                    color: #3b82f6;
                    border-color: #3b82f6;
                    background: #eff6ff;
                }}
                .tooltip {{
                    display: none;
                    position: absolute;
                    top: calc(100% + 8px);
                    left: 0;
                    background: #1e293b;
                    color: #f8fafc;
                    padding: 12px 14px;
                    border-radius: 8px;
                    font-size: 12px;
                    line-height: 1.6;
                    width: 250px;
                    z-index: 100;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                }}
                .tooltip::after {{
                    content: '';
                    position: absolute;
                    bottom: 100%;
                    left: 14px;
                    border: 6px solid transparent;
                    border-bottom-color: #1e293b;
                }}
                .info-wrapper:hover .tooltip {{
                    display: block;
                }}
                .btn-wrapper {{
                    margin-top: 0.75rem;
                    text-align: left;
                }}
                .btn-show-more {{
                    display: inline-block;
                    background: #3b82f6;
                    color: #fff;
                    padding: 6px 16px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-size: 13px;
                    font-weight: 500;
                    transition: background 0.2s;
                }}
                .btn-show-more:hover {{
                    background: #2563eb;
                }}
            </style>
            """
            st.iframe(rules_card_html, height=300)
            
        else:
            st.info("Tidak ada association rules yang tersedia.")


def render_posts_and_methodology(meta: dict):
    """Render row: Post per Universitas + Metodologi."""
    col_left, col_right = st.columns([1.2, 1], gap="medium")

    with col_left:
        post_data = get_post_count_per_university()
        if post_data:
            fig = plot_bar_comparison(
                data=post_data,
                metric_label="Jumlah Post",
                title="",
                orientation="h",
            )
            fig.update_layout(margin=dict(l=80, r=40, t=10, b=30), height=300)
            chart_html = pio.to_html(fig, full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False})

            html_content = f"""
            <div class="chart-card">
                <h4 class="card-title">Jumlah Post per Universitas</h4>
                <div class="chart-wrapper">{chart_html}</div>
            </div>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                * {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ margin: 0; background: transparent; }}
                .chart-card {{
                    background: #fff;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                    border: 1px solid #e2e8f0;
                }}
                .card-title {{
                    font-size: 15px;
                    font-weight: 600;
                    color: #0f172a;
                    margin: 0 0 16px 0;
                    letter-spacing: -0.01em;
                }}
                .chart-wrapper {{
                    width: 100%;
                    overflow: hidden;
                }}
                .js-plotly-plot, .plotly {{ width: 100% !important; }}
            </style>
            """
            st.iframe(html_content, height=380)
        else:
            st.info("Data belum tersedia.")

    with col_right:
        total_posts = meta.get("total_posts", 0)
        total_hashtag = meta.get("total_unique_hashtags", 0)
        render_methodology_card(
            algorithm="Apriori (Market Basket Analysis)",
            source="Instagram scraping - akun resmi universitas",
            period="2025 - QS WUR ranking",
            min_support=APRIORI_CONFIG["min_support"],
            min_confidence=APRIORI_CONFIG["min_confidence"],
            total_itemset=f"{total_posts:,} post → {total_hashtag:,} hashtag unik",
        )


def render_hashtag_frequency(selected_key: str):
    """Render row: Top Hashtag Frequency."""
    st.markdown("<h4 class='dashboard-card-title'>Top Hashtag Terpopuler</h4>", unsafe_allow_html=True)

    freq_list = get_hashtag_frequency(selected_key)

    if freq_list:
        col_chart, col_table = st.columns(2, gap="medium")

        with col_chart:
            color = "#3b82f6"
            if selected_key != "all" and selected_key in UNIVERSITIES:
                color = UNIVERSITIES[selected_key]["color"]

            fig = plot_bar_hashtag_frequency(freq_data=freq_list, title="", top_n=15, color=color)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with col_table:
            df_freq = pd.DataFrame(freq_list[:15])
            if not df_freq.empty:
                df_freq["hashtag"] = df_freq["hashtag"].apply(lambda x: f"#{x}")
                df_freq.columns = ["Hashtag", "Frekuensi", "Persentase (%)"]
                st.dataframe(df_freq, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("Data frekuensi hashtag belum tersedia.")


def main():
    init_page()

    selected_key = get_selected_university()
    meta = get_metadata()
    rules = get_rules()
    display_info = get_university_display_info()

    # Page Header
    render_page_header(
        title=display_info["title"],
        subtitle=display_info["subtitle"],
        badge="Data scraped: Instagram 2025",
    )

    # Metric Cards
    render_metrics_section(meta, selected_key)
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

    # Row 1: Engagement + Top Rules
    render_engagement_and_rules(rules)
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

    # Row 2: Posts per Univ + Methodology
    render_posts_and_methodology(meta)
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)


main()

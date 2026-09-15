"""
pages/04_perbandingan.py
Halaman Perbandingan — analisis komparatif antar universitas dan QS tier.
"""

import streamlit as st

st.set_page_config(
    page_title="Perbandingan | HashBI",
    page_icon="#",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
from config import (
    UNIVERSITIES, QS_TIERS, QS_TIER_COLORS, get_university_colors, ASSETS_DIR,
    FOLLOWERS_SNAPSHOT_DATE,
)
from core.engagement import compute_engagement_rate_per_university
from components.metric_card import render_page_header
from components.charts import plot_bar_comparison, plot_multiline_trend
from components.sidebar import render_sidebar
from core.data_service import ensure_session_state_initialized, get_engagement_summary


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_all_rules_per_univ() -> dict:
    """Return dict {key: list of rules} untuk semua universitas."""
    rules_per_univ = st.session_state.get("rules_per_univ", {})
    return {
        k: v.get("rules", [])
        for k, v in rules_per_univ.items()
        if k in UNIVERSITIES
    }


def get_summary_table() -> pd.DataFrame:
    """Build tabel ringkasan per universitas."""
    rules_per_univ = st.session_state.get("rules_per_univ", {})
    rows = []

    for key, cfg in UNIVERSITIES.items():
        univ_data = rules_per_univ.get(key, {})
        rules     = univ_data.get("rules", [])

        avg_lift   = round(sum(r.get("lift", 0)       for r in rules) / len(rules), 3) if rules else 0
        max_conf   = round(max((r.get("confidence", 0) for r in rules), default=0), 3)
        max_lift   = round(max((r.get("lift", 0)       for r in rules), default=0), 3)
        avg_sup    = round(sum(r.get("support", 0)     for r in rules) / len(rules), 4) if rules else 0

        rows.append({
            "Universitas"       : cfg["name_short"],
            "QS Tier"           : cfg["qs_tier"],
            "QS Rank"           : cfg["qs_rank"],
            "Total Post"        : univ_data.get("total_transactions", 0),
            "Hashtag Unik"      : univ_data.get("total_unique_hashtags", 0),
            "Total Rules"       : univ_data.get("total_rules", 0),
            "Avg. Lift"         : avg_lift,
            "Max. Confidence"   : max_conf,
            "Max. Lift"         : max_lift,
            "Avg. Support"      : avg_sup,
        })

    return pd.DataFrame(rows)


def get_top_hashtags_per_univ(top_n: int = 5) -> dict:
    """Return dict {key: list of top hashtag strings}."""
    freq_data = st.session_state.get("hashtag_frequency", {})
    result = {}
    for key in UNIVERSITIES:
        freq_list = freq_data.get(key, [])
        result[key] = [f"#{item['hashtag']}" for item in freq_list[:top_n]]
    return result


def get_content_type_distribution() -> dict:
    """Get foto vs video/reel distribution per universitas dari data real."""
    from core.preprocessing import load_university_data

    result = {}

    for key in UNIVERSITIES:
        try:
            df = load_university_data(key)

            if df.empty or "is_video" not in df.columns:
                result[key] = {"foto": 65, "video": 35}
                continue

            total = len(df)
            video_count = df["is_video"].sum()
            foto_count = total - video_count

            result[key] = {
                "foto": round((foto_count / total) * 100) if total > 0 else 65,
                "video": round((video_count / total) * 100) if total > 0 else 35
            }
        except Exception:
            result[key] = {"foto": 65, "video": 35}

    return result


def get_dominant_hashtags_per_univ(top_n: int = 5) -> dict:
    """Get top N dominant hashtags per universitas."""
    freq_data = st.session_state.get("hashtag_frequency", {})
    result = {}

    for key in UNIVERSITIES:
        freq_list = freq_data.get(key, [])
        result[key] = [item.get("hashtag", "") for item in freq_list[:top_n]]

    return result


def get_comparative_data(summary_df: pd.DataFrame) -> dict:
    """Prepare data untuk analisis komparatif."""
    engagement_df = get_engagement_summary()

    # Build data dict untuk berbagai metrik
    data = {
        "avg_likes": {},
        "avg_comments": {},
        "engagement_rate": {},
        "total_rules": {},
        "avg_hashtag_per_post": {},
    }

    # Engagement data
    if not engagement_df.empty:
        for _, row in engagement_df.iterrows():
            key = row.get("university_key", "")
            if key in UNIVERSITIES:
                avg_likes = float(row.get("avg_likes", 0))
                avg_comments = float(row.get("avg_comments", 0))
                data["avg_likes"][key] = round(avg_likes, 0)
                data["avg_comments"][key] = round(avg_comments, 0)

                er = compute_engagement_rate_per_university(avg_likes, avg_comments, key)
                if er:
                    data["engagement_rate"][key] = er

    # Data dari summary_df
    for _, row in summary_df.iterrows():
        key = next(
            (k for k, v in UNIVERSITIES.items() if v["name_short"] == row["Universitas"]),
            None
        )
        if key:
            data["total_rules"][key] = int(row["Total Rules"])
            # Calculate avg hashtag per post
            total_post = row["Total Post"]
            hashtag_unik = row["Hashtag Unik"]
            if total_post > 0:
                data["avg_hashtag_per_post"][key] = round(hashtag_unik / total_post, 1)
            else:
                data["avg_hashtag_per_post"][key] = 0

    return data


def render_horizontal_comparative_chart(data_dict: dict, metric_name: str, metric_label: str):
    """Render horizontal bar chart untuk analisis komparatif dengan animasi smooth."""
    if not data_dict:
        st.info(f"Data {metric_label} belum tersedia.")
        return

    # Sort data by value descending
    sorted_data = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)

    # Build HTML bars
    bars_html = ""
    max_value = max(data_dict.values()) if data_dict else 1

    for idx, (key, value) in enumerate(sorted_data):
        cfg = UNIVERSITIES.get(key, {})
        name = cfg.get("name_short", key)
        color = cfg.get("color", "#3b82f6")

        # Calculate bar width percentage
        bar_width = (value / max_value * 100) if max_value > 0 else 0

        # Format value display
        if metric_name == "engagement_rate":
            value_str = f"{value:.2f}%".replace(".", ",")
        elif metric_name in ["avg_likes", "avg_comments"]:
            value_str = f"{int(value)}"
        elif metric_name == "avg_hashtag_per_post":
            value_str = f"{value:.1f}"
        else:
            value_str = f"{int(value)}"

        # Add staggered animation delay
        delay = idx * 0.05

        bars_html += f"""
        <div class="bar-row" style="animation-delay: {delay}s;">
            <div class="bar-label">{name}</div>
            <div class="bar-container">
                <div class="bar-fill" style="background: {color};" data-width="{bar_width}">
                    <span class="bar-value">{value_str}</span>
                </div>
            </div>
        </div>
        """

    # Full HTML with styling and JavaScript for smooth animations
    html_content = f"""
    <div class="comparative-chart">
        <h3 class="chart-title">{metric_label}</h3>
        <div class="bars-wrapper">
            {bars_html}
        </div>
    </div>

    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        * {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: transparent;
        }}

        .comparative-chart {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            animation: fadeIn 0.4s ease-out;
        }}

        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .chart-title {{
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 20px;
            letter-spacing: -0.02em;
            animation: slideInFromLeft 0.5s ease-out;
        }}

        @keyframes slideInFromLeft {{
            from {{
                opacity: 0;
                transform: translateX(-20px);
            }}
            to {{
                opacity: 1;
                transform: translateX(0);
            }}
        }}

        .bars-wrapper {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .bar-row {{
            display: flex;
            align-items: center;
            gap: 16px;
            opacity: 0;
            animation: slideInFromRight 0.6s ease-out forwards;
        }}

        @keyframes slideInFromRight {{
            from {{
                opacity: 0;
                transform: translateX(30px);
            }}
            to {{
                opacity: 1;
                transform: translateX(0);
            }}
        }}

        .bar-label {{
            min-width: 100px;
            font-size: 14px;
            font-weight: 500;
            color: #475569;
            text-align: right;
        }}

        .bar-container {{
            flex: 1;
            height: 42px;
            background: #f1f5f9;
            border-radius: 21px;
            overflow: hidden;
            position: relative;
        }}

        .bar-fill {{
            height: 100%;
            border-radius: 21px;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            padding-left: 16px;
            min-width: 60px;
            width: 0%;
            transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .bar-value {{
            font-size: 15px;
            font-weight: 700;
            color: #fff;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
            opacity: 0;
            transition: opacity 0.3s ease 0.5s;
        }}

        .bar-fill.animated .bar-value {{
            opacity: 1;
        }}
    </style>

    <script>
        // Animate bars after elements are loaded
        document.addEventListener('DOMContentLoaded', function() {{
            setTimeout(() => {{
                const barFills = document.querySelectorAll('.bar-fill');
                barFills.forEach((bar, index) => {{
                    const targetWidth = bar.getAttribute('data-width');
                    setTimeout(() => {{
                        bar.style.width = targetWidth + '%';
                        bar.classList.add('animated');
                    }}, index * 80);
                }});
            }}, 100);
        }});

        // Trigger animation immediately if DOMContentLoaded already fired
        if (document.readyState === 'complete' || document.readyState === 'interactive') {{
            setTimeout(() => {{
                const barFills = document.querySelectorAll('.bar-fill');
                barFills.forEach((bar, index) => {{
                    const targetWidth = bar.getAttribute('data-width');
                    setTimeout(() => {{
                        bar.style.width = targetWidth + '%';
                        bar.classList.add('animated');
                    }}, index * 80);
                }});
            }}, 100);
        }}
    </script>
    """

    st.iframe(html_content, height=len(sorted_data) * 58 + 100)


def render_content_type_chart(content_data: dict):
    """Render stacked horizontal bar chart untuk foto vs video/reel."""
    if not content_data:
        st.info("Data content type belum tersedia.")
        return

    bars_html = ""

    for key in UNIVERSITIES:
        cfg = UNIVERSITIES[key]
        name = cfg["name_short"]
        data = content_data.get(key, {"foto": 50, "video": 50})
        foto_pct = data["foto"]
        video_pct = data["video"]

        bars_html += f"""
        <div class="content-row">
            <div class="content-label">{name}</div>
            <div class="stacked-bar">
                <div class="bar-segment foto" style="width: {foto_pct}%;">
                    <span class="segment-value">{foto_pct:.0f}%</span>
                </div>
                <div class="bar-segment video" style="width: {video_pct}%;">
                    <span class="segment-value">{video_pct:.0f}%</span>
                </div>
            </div>
        </div>
        """

    html_content = f"""
    <div class="content-type-card">
        <h3 class="card-title">Foto vs Video/Reel (%)</h3>
        <div class="content-bars">
            {bars_html}
        </div>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color foto"></div>
                <span>Foto</span>
            </div>
            <div class="legend-item">
                <div class="legend-color video"></div>
                <span>Video/Reel</span>
            </div>
        </div>
    </div>

    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        * {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: transparent;
        }}

        .content-type-card {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            animation: fadeIn 0.4s ease-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .card-title {{
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 20px;
            letter-spacing: -0.02em;
        }}

        .content-bars {{
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin-bottom: 20px;
        }}

        .content-row {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .content-label {{
            min-width: 90px;
            font-size: 14px;
            font-weight: 500;
            color: #475569;
        }}

        .stacked-bar {{
            flex: 1;
            display: flex;
            height: 36px;
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .bar-segment {{
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .bar-segment.foto {{
            background: #3b82f6;
        }}

        .bar-segment.video {{
            background: #f97316;
        }}

        .segment-value {{
            font-size: 13px;
            font-weight: 700;
            color: #fff;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }}

        .legend {{
            display: flex;
            gap: 20px;
            justify-content: flex-start;
            padding-top: 12px;
            border-top: 1px solid #f1f5f9;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }}

        .legend-color.foto {{
            background: #3b82f6;
        }}

        .legend-color.video {{
            background: #f97316;
        }}

        .legend-item span {{
            font-size: 13px;
            color: #64748b;
            font-weight: 500;
        }}
    </style>
    """

    st.iframe(html_content, height=480)


def render_dominant_hashtags(hashtags_data: dict):
    """Render dominant hashtags per institusi dengan pills."""
    if not hashtags_data:
        st.info("Data hashtag dominan belum tersedia.")
        return

    rows_html = ""

    for key in UNIVERSITIES:
        cfg = UNIVERSITIES[key]
        name_short = cfg["name_short"]
        color = cfg["color"]
        hashtags = hashtags_data.get(key, [])

        # Create pills HTML
        pills_html = ""
        if hashtags:
            for tag in hashtags:
                if tag:
                    pills_html += f'<span class="hashtag-pill">#{tag}</span>'
        else:
            pills_html = '<span class="no-data">Data belum tersedia</span>'

        rows_html += f"""
        <div class="hashtag-row">
            <div class="univ-badge" style="background: {color}20; color: {color}; border: 1.5px solid {color}40;">
                {name_short}
            </div>
            <div class="hashtag-pills">
                {pills_html}
            </div>
        </div>
        """

    html_content = f"""
    <div class="hashtag-card">
        <h3 class="card-title">Hashtag Dominan per Institusi</h3>
        <div class="hashtag-rows">
            {rows_html}
        </div>
    </div>

    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        * {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: transparent;
        }}

        .hashtag-card {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            animation: fadeIn 0.4s ease-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .card-title {{
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 20px;
            letter-spacing: -0.02em;
        }}

        .hashtag-rows {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .hashtag-row {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #f1f5f9;
        }}

        .hashtag-row:last-child {{
            border-bottom: none;
        }}

        .univ-badge {{
            min-width: 70px;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            text-align: center;
            flex-shrink: 0;
        }}

        .hashtag-pills {{
            flex: 1;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
        }}

        .hashtag-pill {{
            display: inline-block;
            padding: 6px 14px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
            color: #475569;
            transition: all 0.2s ease;
        }}

        .hashtag-pill:hover {{
            background: #e0e7ff;
            border-color: #c7d2fe;
            color: #4f46e5;
            transform: translateY(-1px);
        }}

        .no-data {{
            font-size: 12px;
            color: #94a3b8;
            font-style: italic;
        }}
    </style>
    """

    st.iframe(html_content, height=520)


# ─────────────────────────────────────────────
# MAIN PAGE
# ─────────────────────────────────────────────

def init_page():
    """Inisialisasi layout, CSS, dan sidebar."""
    ensure_session_state_initialized()
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    render_sidebar()


def main():
    init_page()

    render_page_header(
        title="Perbandingan",
        subtitle="Analisis komparatif pola hashtag antar universitas dan QS tier",
    )

    rules_per_univ = get_all_rules_per_univ()
    summary_df     = get_summary_table()

    if summary_df.empty:
        st.warning("Data belum tersedia.")
        st.stop()


    st.markdown("""
    <div style='margin-top: 1.5rem; margin-bottom: 1rem;'>
        <h2 style='font-size: 28px; font-weight: 700; color: #0f172a; margin: 0; letter-spacing: -0.02em;'>
            Analisis Komparatif Antar Institusi
        </h2>
        <p style='font-size: 14px; color: #64748b; margin: 4px 0 0 0;'>
            Perbandingan pola asosiasi hashtag dan engagement 7 universitas
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Get comparative data
    comparative_data = get_comparative_data(summary_df)

    # Metric selection dengan custom pills
    metrics = [
        ("avg_likes", "Avg. Likes"),
        ("avg_comments", "Avg. Comments"),
        ("engagement_rate", "Engagement Rate"),
        ("total_rules", "Jumlah Rules"),
        ("avg_hashtag_per_post", "Avg. Hashtag / Post"),
    ]

    # Initialize selected metric in session state
    if "selected_comparative_metric" not in st.session_state:
        st.session_state.selected_comparative_metric = "avg_likes"

    # Create pills using columns
    cols = st.columns(len(metrics))
    for idx, (col, (metric_key, metric_label)) in enumerate(zip(cols, metrics)):
        with col:
            is_active = st.session_state.selected_comparative_metric == metric_key
            button_type = "primary" if is_active else "secondary"
            if st.button(
                metric_label,
                key=f"metric_btn_{metric_key}",
                use_container_width=True,
                type=button_type,
            ):
                st.session_state.selected_comparative_metric = metric_key
                st.rerun()

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # Render horizontal chart based on selected metric
    selected_metric = st.session_state.selected_comparative_metric
    selected_label = next((label for key, label in metrics if key == selected_metric), "")
    selected_data = comparative_data.get(selected_metric, {})

    render_horizontal_comparative_chart(selected_data, selected_metric, selected_label)

    if selected_metric == "engagement_rate":
        st.caption(
            "Engagement rate = (rata-rata likes + rata-rata comments) / jumlah followers x 100%. "
            f"Jumlah followers dicatat pada {FOLLOWERS_SNAPSHOT_DATE} dan bersifat snapshot satu "
            "titik waktu, bukan nilai historis saat masing-masing konten diunggah."
        )

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)


    col_left, col_right = st.columns(2, gap="medium")

    with col_left:
        content_type_data = get_content_type_distribution()
        render_content_type_chart(content_type_data)

    with col_right:
        dominant_hashtags_data = get_dominant_hashtags_per_univ(top_n=5)
        render_dominant_hashtags(dominant_hashtags_data)

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

main()
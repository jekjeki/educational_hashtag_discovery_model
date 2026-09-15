"""
components/charts.py
Semua fungsi visualisasi Plotly untuk HashBI dashboard.
Chart theme yang konsisten dengan light theme modern.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config import UNIVERSITIES, get_university_colors, QS_TIER_COLORS

# ─────────────────────────────────────────────
# THEME CONFIG — Light Theme
# ─────────────────────────────────────────────
CHART_THEME = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#475569", size=12),
    xaxis=dict(
        gridcolor="#e2e8f0",
        linecolor="#e2e8f0",
        tickcolor="#e2e8f0",
        tickfont=dict(color="#475569", size=11),
    ),
    yaxis=dict(
        gridcolor="#e2e8f0",
        linecolor="#e2e8f0",
        tickcolor="#e2e8f0",
        tickfont=dict(color="#475569", size=11),
    ),
    margin=dict(l=0, r=0, t=30, b=0),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="#e2e8f0",
        font=dict(color="#475569", size=11),
    ),
)


def _apply_theme(fig: go.Figure) -> go.Figure:
    """Apply light theme ke figure Plotly."""
    fig.update_layout(**CHART_THEME)
    return fig


# ─────────────────────────────────────────────
# CHART 1 — TOP HASHTAG FREQUENCY (Bar Horizontal)
# ─────────────────────────────────────────────
def plot_bar_hashtag_frequency(
    freq_data: list,
    title: str = "Top Hashtag",
    top_n: int = 15,
    color: str = "#3b82f6",
) -> go.Figure:
    """
    Bar chart horizontal untuk frekuensi hashtag.

    Args:
        freq_data: list of dict {hashtag, frequency, percentage}
        title    : judul chart
        top_n    : jumlah hashtag yang ditampilkan
        color    : warna bar
    """
    df = pd.DataFrame(freq_data).head(top_n)
    if df.empty:
        return go.Figure()

    df = df.sort_values("frequency", ascending=True)

    fig = go.Figure(go.Bar(
        x=df["frequency"],
        y=df["hashtag"].apply(lambda x: f"#{x}"),
        orientation="h",
        marker=dict(
            color=color,
            opacity=0.9,
            line=dict(width=0),
        ),
        text=df["frequency"],
        textposition="outside",
        textfont=dict(color="#475569", size=11),
        hovertemplate="<b>%{y}</b><br>Frekuensi: %{x}<extra></extra>",
    ))

    _apply_theme(fig)
    fig.update_layout(
        title=dict(text=title, font=dict(color="#0f172a", size=14)),
        height=max(300, top_n * 28),
        margin=dict(l=0, r=60, t=40, b=0),
    )
    fig.update_yaxes(tickfont=dict(color="#0f172a", size=12))

    return fig


# ─────────────────────────────────────────────
# CHART 2 — ENGAGEMENT TREND (Line Chart)
# ─────────────────────────────────────────────
def plot_engagement_trend(
    trend_df: pd.DataFrame,
    university_key: str = "all",
    metric: str = "avg_likes",
) -> go.Figure:
    """
    Line chart tren engagement per bulan.

    Args:
        trend_df      : DataFrame dengan kolom month, avg_likes, avg_comments, post_count
        university_key: key universitas atau 'all'
        metric        : kolom yang diplot (avg_likes / avg_comments / post_count)
    """
    if trend_df.empty or metric not in trend_df.columns:
        return go.Figure()

    color = "#3b82f6"
    if university_key != "all" and university_key in UNIVERSITIES:
        color = UNIVERSITIES[university_key]["color"]

    label_map = {
        "avg_likes"   : "Rata-rata Likes",
        "avg_comments": "Rata-rata Komentar",
        "post_count"  : "Jumlah Post",
    }

    fig = go.Figure()

    # Area fill
    fig.add_trace(go.Scatter(
        x=trend_df["month"],
        y=trend_df[metric],
        mode="lines+markers",
        fill="tozeroy",
        fillcolor=f"rgba({_hex_to_rgb(color)},0.08)",
        line=dict(color=color, width=2),
        marker=dict(size=5, color=color),
        name=label_map.get(metric, metric),
        hovertemplate="%{x}<br>" + label_map.get(metric, metric) + ": %{y:.0f}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(
            text=label_map.get(metric, metric),
            font=dict(color="#0f172a", size=14)
        ),
        height=220,
        showlegend=False,
        **{k: v for k, v in CHART_THEME.items() if k not in ["margin"]},
        margin=dict(l=0, r=0, t=35, b=0),
    )

    return _apply_theme(fig)


# ─────────────────────────────────────────────
# CHART 3 — RULES SCATTER (Support vs Confidence, color=Lift)
# ─────────────────────────────────────────────
def plot_rules_scatter(rules_df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot support vs confidence dengan warna lift.
    """
    if rules_df.empty:
        return go.Figure()

    fig = go.Figure(go.Scatter(
        x=rules_df["support"],
        y=rules_df["confidence"],
        mode="markers",
        marker=dict(
            size=8,
            color=rules_df["lift"],
            colorscale="Blues",
            showscale=True,
            colorbar=dict(
                title=dict(text="Lift", font=dict(color="#475569", size=11)),
                tickfont=dict(color="#475569", size=10),
            ),
            opacity=0.85,
            line=dict(width=0.5, color="#e2e8f0"),
        ),
        hovertemplate=(
            "<b>Support:</b> %{x:.3f}<br>"
            "<b>Confidence:</b> %{y:.3f}<br>"
            "<b>Lift:</b> %{marker.color:.3f}"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        title=dict(text="Support vs Confidence (warna = Lift)", font=dict(color="#0f172a", size=14)),
        xaxis_title="Support",
        yaxis_title="Confidence",
        height=350,
        **{k: v for k, v in CHART_THEME.items() if k not in ["margin"]},
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return _apply_theme(fig)


# ─────────────────────────────────────────────
# CHART 4 — COMPARISON BAR (antar universitas)
# ─────────────────────────────────────────────
def plot_bar_comparison(
    data: dict,
    metric_label: str = "Jumlah Post",
    title: str = "Perbandingan antar Universitas",
    orientation: str = "v",
) -> go.Figure:
    """
    Bar chart perbandingan antar universitas.

    Args:
        data        : dict {university_key: value}
        metric_label: label sumbu nilai
        title       : judul chart
        orientation : "v" (vertikal) atau "h" (horizontal)
    """
    if not data:
        return go.Figure()

    univ_colors = get_university_colors()
    labels  = []
    values  = []
    colors  = []

    for key, val in data.items():
        if key in UNIVERSITIES:
            labels.append(UNIVERSITIES[key]["name_short"])
            values.append(val)
            colors.append(univ_colors.get(key, "#3b82f6"))

    if orientation == "h":
        # Sort ascending supaya bar terbesar ada di atas
        order = sorted(range(len(values)), key=lambda i: values[i])
        labels = [labels[i] for i in order]
        values = [values[i] for i in order]
        colors = [colors[i] for i in order]

        fig = go.Figure(go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=colors, opacity=0.9, line=dict(width=0)),
            text=values,
            textposition="outside",
            textfont=dict(color="#475569", size=11),
            hovertemplate="<b>%{y}</b><br>" + metric_label + ": %{x}<extra></extra>",
        ))

        fig.update_layout(
            title=dict(text=title, font=dict(color="#0f172a", size=14)),
            xaxis_title=metric_label,
            height=max(280, len(labels) * 40),
            showlegend=False,
            **{k: v for k, v in CHART_THEME.items() if k not in ["margin"]},
            margin=dict(l=0, r=60, t=40, b=0),
        )
        fig.update_yaxes(
            tickfont=dict(color="#0f172a", size=12),
            automargin=True,
        )
    else:
        fig = go.Figure(go.Bar(
            x=labels,
            y=values,
            marker=dict(color=colors, opacity=0.9, line=dict(width=0)),
            text=values,
            textposition="outside",
            textfont=dict(color="#475569", size=11),
            hovertemplate="<b>%{x}</b><br>" + metric_label + ": %{y}<extra></extra>",
        ))

        fig.update_layout(
            title=dict(text=title, font=dict(color="#0f172a", size=14)),
            yaxis_title=metric_label,
            height=300,
            showlegend=False,
            **{k: v for k, v in CHART_THEME.items() if k not in ["margin"]},
            margin=dict(l=0, r=0, t=40, b=0),
        )

    return _apply_theme(fig)


# ─────────────────────────────────────────────
# CHART 5 — LIFT DISTRIBUTION (Histogram)
# ─────────────────────────────────────────────
def plot_lift_distribution(rules_df: pd.DataFrame, color: str = "#8b5cf6") -> go.Figure:
    """
    Histogram distribusi nilai lift dari association rules.
    """
    if rules_df.empty or "lift" not in rules_df.columns:
        return go.Figure()

    fig = go.Figure(go.Histogram(
        x=rules_df["lift"],
        nbinsx=20,
        marker=dict(color=color, opacity=0.8, line=dict(width=0)),
        hovertemplate="Lift: %{x:.2f}<br>Jumlah Rules: %{y}<extra></extra>",
    ))

    # Garis vertikal di lift=1
    fig.add_vline(
        x=1.0,
        line=dict(color="#f43f5e", width=1.5, dash="dash"),
        annotation_text="lift=1",
        annotation_font=dict(color="#f43f5e", size=10),
    )

    fig.update_layout(
        title=dict(text="Distribusi Lift", font=dict(color="#0f172a", size=14)),
        xaxis_title="Lift",
        yaxis_title="Jumlah Rules",
        height=250,
        showlegend=False,
        **{k: v for k, v in CHART_THEME.items() if k not in ["margin"]},
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return _apply_theme(fig)


# ─────────────────────────────────────────────
# CHART 6 — MULTI-LINE TREND (semua universitas)
# ─────────────────────────────────────────────
def plot_multiline_trend(
    trend_dict: dict,
    metric: str = "avg_likes",
    title: str = "Tren Engagement per Universitas",
) -> go.Figure:
    """
    Multi-line chart untuk perbandingan tren semua universitas.

    Args:
        trend_dict: dict {university_key: trend_df}
        metric    : kolom yang diplot
        title     : judul chart
    """
    fig = go.Figure()
    univ_colors = get_university_colors()

    for key, df in trend_dict.items():
        if df.empty or metric not in df.columns or key == "all":
            continue
        if key not in UNIVERSITIES:
            continue

        name  = UNIVERSITIES[key]["name_short"]
        color = univ_colors.get(key, "#3b82f6")

        fig.add_trace(go.Scatter(
            x=df["month"],
            y=df[metric],
            mode="lines+markers",
            name=name,
            line=dict(color=color, width=1.5),
            marker=dict(size=4, color=color),
            hovertemplate=f"<b>{name}</b><br>%{{x}}<br>{metric}: %{{y:.0f}}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(color="#0f172a", size=14)),
        height=320,
        **{k: v for k, v in CHART_THEME.items() if k not in ["margin"]},
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return _apply_theme(fig)


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color ke string RGB untuk rgba()."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"{r},{g},{b}"
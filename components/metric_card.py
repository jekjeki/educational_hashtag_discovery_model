"""
components/metric_card.py
Reusable metric card components untuk HashBI dashboard.
"""

import streamlit as st


def render_metric_card(
    label: str,
    value: str,
    sub: str = "",
    accent_color: str = "#3b82f6",
    icon: str = "",
) -> None:
    """
    Render satu metric card dengan accent bar berwarna di atas.

    Args:
        label       : Label di atas angka (uppercase kecil)
        value       : Nilai utama yang ditampilkan besar
        sub         : Teks kecil di bawah nilai
        accent_color: Warna accent bar (hex)
        icon        : Opsional — emoji atau karakter ikon
    """
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-accent" style="background:{accent_color}"></div>
        <div class="metric-label">{icon + " " if icon else ""}{label}</div>
        <div class="metric-value">{value}</div>
        {f'<div class="metric-sub">{sub}</div>' if sub else ""}
    </div>
    """, unsafe_allow_html=True)


def render_metric_row(metrics: list) -> None:
    """
    Render beberapa metric card dalam satu baris kolom.

    Args:
        metrics: list of dict dengan keys:
            - label       : str
            - value       : str
            - sub         : str (opsional)
            - accent_color: str hex (opsional, default biru)
            - icon        : str (opsional)
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            render_metric_card(
                label=m.get("label", ""),
                value=m.get("value", "—"),
                sub=m.get("sub", ""),
                accent_color=m.get("accent_color", "#3b82f6"),
                icon=m.get("icon", ""),
            )


def render_stat_inline(label: str, value: str, color: str = "var(--text-secondary)") -> str:
    """
    Return HTML string untuk stat kecil inline (tidak pakai st.markdown).
    Berguna untuk ditempel di dalam card lain.
    """
    return f"""
    <div style="display:flex;justify-content:space-between;
    align-items:center;padding:10px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:13px;color:var(--text-secondary)">{label}</span>
        <span style="font-size:13px;font-weight:600;color:{color}">{value}</span>
    </div>
    """


def render_methodology_card(
    algorithm: str,
    source: str,
    period: str,
    min_support: float,
    min_confidence: float,
    total_itemset: str,
) -> None:
    """
    Render kartu metodologi seperti di hi-fi design (pojok kanan bawah overview).
    """
    rows = [
        render_stat_inline("Algoritma", algorithm, "var(--accent-blue)"),
        render_stat_inline("Sumber Data", source),
        render_stat_inline("Periode", period),
        render_stat_inline("Min. Support", f"{min_support:.2f}"),
        render_stat_inline("Min. Confidence", f"{min_confidence:.2f}"),
        render_stat_inline("Total Itemset", total_itemset),
    ]
    st.markdown(f"""
    <div class="dashboard-card">
        <h4 class="dashboard-card-title">Metodologi</h4>
        {"".join(rows)}
    </div>
    """, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str, badge: str = "") -> None:
    """
    Render header halaman dengan judul, subtitle, dan opsional badge.
    """
    badge_html = ""
    if badge:
        badge_html = f'<span class="badge badge-info">{badge}</span>'

    st.markdown(f"""
    <div class="page-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
        {badge_html}
    </div>
    """, unsafe_allow_html=True)


def render_rule_item(
    antecedent: str,
    consequent: str,
    lift: float,
) -> None:
    """
    Render satu baris association rule dengan lift badge berwarna.
    """
    if lift >= 2.5:
        badge_class = "lift-high"
    elif lift >= 1.5:
        badge_class = "lift-mid"
    else:
        badge_class = "lift-normal"

    st.markdown(f"""
    <div class="rule-item">
        <span class="rule-text">
            {antecedent}
            <span class="rule-arrow">→</span>
            {consequent}
        </span>
        <span class="lift-badge {badge_class}">lift {lift:.2f}</span>
    </div>
    """, unsafe_allow_html=True)


def render_top_rules(rules_list: list, top_n: int = 5) -> None:
    """
    Render top N association rules dari list of dict.
    Tiap dict harus punya: antecedents_str, consequents_str, lift
    """
    if not rules_list:
        st.info("Tidak ada association rules yang tersedia.")
        return

    top = sorted(rules_list, key=lambda x: x.get("lift", 0), reverse=True)[:top_n]

    for rule in top:
        render_rule_item(
            antecedent=rule.get("antecedents_str", ""),
            consequent=rule.get("consequents_str", ""),
            lift=rule.get("lift", 0),
        )
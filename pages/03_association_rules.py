"""
pages/03_association_rules.py
Halaman Association Rules — tabel lengkap, ringkasan metrik, dan ekspor data.
"""

import streamlit as st

st.set_page_config(
    page_title="Association Rules | HashBI",
    page_icon="#",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
from core.data_service import ensure_session_state_initialized
from config import ASSETS_DIR, UNIVERSITIES
from components.sidebar import render_sidebar


# ─────────────────────────────────────────────
# KATEGORI KEKUATAN ASOSIASI
# (selaras dengan halaman Network Graph)
# ─────────────────────────────────────────────
LIFT_CATEGORIES = [
    {"label": "Sangat erat", "hint": "lift ≥ 5",  "color": "#10b981", "test": lambda v: v >= 5},
    {"label": "Erat",        "hint": "lift 3–5",  "color": "#3b82f6", "test": lambda v: 3 <= v < 5},
    {"label": "Cukup erat",  "hint": "lift 2–3",  "color": "#6366f1", "test": lambda v: 2 <= v < 3},
    {"label": "Kurang erat", "hint": "lift < 2",  "color": "#94a3b8", "test": lambda v: v < 2},
]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_selected_key() -> str:
    return st.session_state.get("selected_university", "all")


def get_rules_for_selected() -> list:
    key = get_selected_key()
    rules_per_univ = st.session_state.get("rules_per_univ", {})

    if key == "all":
        all_rules = []
        for univ_data in rules_per_univ.values():
            all_rules.extend(univ_data.get("rules", []))
        return sorted(all_rules, key=lambda x: x.get("lift", 0), reverse=True)

    return rules_per_univ.get(key, {}).get("rules", [])


def format_hashtags_plain(items: list) -> str:
    """Format list hashtags menjadi plain text dengan #."""
    if not items:
        return ""
    return " ".join(f"#{tag}" if not str(tag).startswith("#") else str(tag) for tag in items)


def filter_rules(rules: list, search_query: str) -> list:
    """Filter rules berdasarkan search query."""
    if not search_query:
        return rules

    search_lower = search_query.lower().replace("#", "")
    filtered = []
    for rule in rules:
        all_tags = [
            str(t).lower()
            for t in rule.get("antecedents", []) + rule.get("consequents", [])
        ]
        if any(search_lower in tag for tag in all_tags):
            filtered.append(rule)
    return filtered


def fmt_num(n: int) -> str:
    """Format ribuan dengan titik sesuai kaidah penulisan Bahasa Indonesia."""
    return f"{n:,}".replace(",", ".")


def rules_to_dataframe(rules: list) -> pd.DataFrame:
    """Konversi list rules menjadi DataFrame siap tampil / ekspor."""
    return pd.DataFrame([
        {
            "#": idx,
            "Antecedent": format_hashtags_plain(r.get("antecedents", [])),
            "Consequent": format_hashtags_plain(r.get("consequents", [])),
            "Support": r.get("support", 0),
            "Confidence": r.get("confidence", 0),
            "Lift": r.get("lift", 0),
        }
        for idx, r in enumerate(rules, start=1)
    ])


def lift_breakdown(rules: list) -> list:
    """Hitung sebaran rules per kategori kekuatan asosiasi."""
    lifts = [r.get("lift", 0) for r in rules]
    total = len(lifts) or 1
    out = []
    for cat in LIFT_CATEGORIES:
        n = sum(1 for v in lifts if cat["test"](v))
        out.append({
            "label": cat["label"], "hint": cat["hint"], "color": cat["color"],
            "count": n, "pct": n / total * 100,
        })
    return out


# ─────────────────────────────────────────────
# KOMPONEN TAMPILAN
# ─────────────────────────────────────────────

PAGE_CSS = """
<style>
/* Header halaman ini tanpa garis aksen gradasi */
.ar-header { margin-bottom: 0; }
.ar-header h1 {
    font-size: 27px; font-weight: 800; color: #0f172a;
    margin: 0 0 6px 0; letter-spacing: -0.03em;
}
.ar-header p { font-size: 14px; color: #64748b; margin: 0; }
.ar-header b { color: #0f172a; font-weight: 700; }

.ar-section-label {
    display: inline-flex; align-items: center; gap: 8px;
    font-size: 11px; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: #94a3b8; margin-bottom: 10px;
}

/* Kartu metrik */
.ar-metric {
    background: #fff; border: 1px solid #e6e9f2; border-radius: 14px;
    padding: 15px 17px; height: 100%;
    box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 6px 16px -8px rgba(15,23,42,.10);
    transition: transform .25s cubic-bezier(.22,1,.36,1), box-shadow .25s cubic-bezier(.22,1,.36,1);
}
.ar-metric:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 4px rgba(15,23,42,.05), 0 14px 28px -10px rgba(15,23,42,.16);
}
.ar-metric-top { display: flex; align-items: center; gap: 8px; margin-bottom: 9px; }
.ar-metric-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ar-metric-label {
    font-size: 10.5px; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: #94a3b8;
}
.ar-metric-value {
    font-size: 28px; font-weight: 800; color: #0f172a;
    line-height: 1.05; letter-spacing: -0.03em;
    font-family: 'JetBrains Mono', monospace;
}
.ar-metric-sub { font-size: 12px; color: #94a3b8; margin-top: 5px; }

/* Sebaran kekuatan */
.ar-dist-bar {
    display: flex; height: 10px; border-radius: 999px;
    overflow: hidden; background: #eef1f7; margin-bottom: 14px;
}
.ar-dist-legend { display: flex; flex-wrap: wrap; gap: 18px; }
.ar-dist-item { display: inline-flex; align-items: center; gap: 8px; }
.ar-dist-dot { width: 9px; height: 9px; border-radius: 50%; }
.ar-dist-label { font-size: 12.5px; font-weight: 600; color: #0f172a; }
.ar-dist-hint { font-size: 11px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; }
.ar-dist-count {
    font-size: 12.5px; font-weight: 700; color: #475569;
    font-family: 'JetBrains Mono', monospace;
}

/* Container tabel */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff;
    border: 1px solid #e6e9f2 !important;
    border-radius: 16px !important;
    box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 8px 20px -6px rgba(15,23,42,.07);
    padding: 1.15rem 1.3rem 1.25rem 1.3rem;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { border: none !important; }

.ar-table-head {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 8px; margin-bottom: 0.9rem;
}
.ar-table-title { font-size: 15px; font-weight: 700; color: #0f172a; }
.ar-table-note {
    font-size: 12px; color: #94a3b8; background: #f6f7fb;
    border: 1px solid #e6e9f2; padding: 4px 12px; border-radius: 999px;
}
</style>
"""


def render_metric_cards(rules: list, total_all: int) -> None:
    """Empat kartu metrik ringkas."""
    lifts = [r.get("lift", 0) for r in rules]
    confs = [r.get("confidence", 0) for r in rules]
    strong = sum(1 for v in lifts if v >= 2)

    cards = [
        {
            "label": "Total Rules", "color": "#6366f1",
            "value": fmt_num(len(rules)),
            "sub": (
                f"dari {fmt_num(total_all)} rules"
                if len(rules) != total_all else "algoritma Apriori"
            ),
        },
        {
            "label": "Rata-rata Lift", "color": "#8b5cf6",
            "value": f"{sum(lifts)/len(lifts):.2f}",
            "sub": "kekuatan asosiasi rata-rata",
        },
        {
            "label": "Lift Tertinggi", "color": "#10b981",
            "value": f"{max(lifts):.2f}",
            "sub": "pasangan hashtag terkuat",
        },
        {
            "label": "Confidence Tertinggi", "color": "#22d3ee",
            "value": f"{max(confs):.2f}",
            "sub": f"{fmt_num(strong)} rules berasosiasi kuat",
        },
    ]

    for col, c in zip(st.columns(4, gap="medium"), cards):
        with col:
            st.markdown(
                f"""
                <div class="ar-metric">
                    <div class="ar-metric-top">
                        <span class="ar-metric-dot" style="background:{c['color']}"></span>
                        <span class="ar-metric-label">{c['label']}</span>
                    </div>
                    <div class="ar-metric-value">{c['value']}</div>
                    <div class="ar-metric-sub">{c['sub']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_distribution(rules: list) -> None:
    """Bar sebaran kekuatan asosiasi + legenda."""
    bd = lift_breakdown(rules)
    segments = "".join(
        f'<div style="width:{b["pct"]}%;background:{b["color"]};"></div>'
        for b in bd if b["count"]
    )
    legend = "".join(
        f"""
        <span class="ar-dist-item">
            <span class="ar-dist-dot" style="background:{b['color']}"></span>
            <span class="ar-dist-label">{b['label']}</span>
            <span class="ar-dist-hint">{b['hint']}</span>
            <span class="ar-dist-count">{fmt_num(b['count'])} &middot; {b['pct']:.0f}%</span>
        </span>
        """
        for b in bd
    )
    st.markdown(
        f"""
        <div class="ar-dist-bar">{segments}</div>
        <div class="ar-dist-legend">{legend}</div>
        """,
        unsafe_allow_html=True,
    )


def render_rules_table(df: pd.DataFrame) -> None:
    """Tabel association rules dengan progress column."""
    max_lift = df["Lift"].max() if len(df) else 1

    column_config = {
        "#": st.column_config.NumberColumn("#", width="small", help="Nomor urut"),
        "Antecedent": st.column_config.TextColumn(
            "JIKA (Antecedent)", width="large",
            help="Hashtag yang menjadi kondisi awal",
        ),
        "Consequent": st.column_config.TextColumn(
            "MAKA (Consequent)", width="large",
            help="Hashtag yang biasanya menyertai antecedent",
        ),
        "Support": st.column_config.ProgressColumn(
            "Support", format="%.3f", min_value=0,
            max_value=float(df["Support"].max()) if len(df) else 1,
            help="Proporsi post yang memuat kombinasi hashtag ini",
        ),
        "Confidence": st.column_config.ProgressColumn(
            "Confidence", format="%.3f", min_value=0,
            max_value=float(df["Confidence"].max()) if len(df) else 1,
            help="Peluang consequent muncul bila antecedent ada",
        ),
        "Lift": st.column_config.ProgressColumn(
            "Lift", format="%.2f", min_value=0, max_value=float(max_lift),
            help="Berapa kali lebih sering dua hashtag muncul bersama dibanding kebetulan",
        ),
    }

    st.dataframe(
        df, column_config=column_config, hide_index=True,
        width="stretch", height=560,
    )


# ─────────────────────────────────────────────
# MAIN PAGE
# ─────────────────────────────────────────────

def init_page():
    ensure_session_state_initialized()
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    render_sidebar()


def main():
    init_page()
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    selected_key = get_selected_key()
    rules = get_rules_for_selected()

    scope = (
        "seluruh universitas" if selected_key == "all"
        else UNIVERSITIES.get(selected_key, {}).get("name", "")
    )

    # ── Header ──
    st.markdown(
        f"""
        <div class="ar-header">
            <h1>Association Rules</h1>
            <p><b>{fmt_num(len(rules))}</b> rules ditemukan pada {scope} &middot; algoritma Apriori</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not rules:
        st.info("Belum ada data rules. Jalankan preprocessing terlebih dahulu.")
        return

    st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

    # ── Pencarian + ekspor ──
    col_search, col_export = st.columns([3, 1], gap="medium")
    with col_search:
        search_query = st.text_input(
            "Cari hashtag",
            placeholder="Cari hashtag misalnya wisuda atau kampus",
            label_visibility="collapsed",
            key="search_hashtag",
        )

    filtered_rules = filter_rules(rules, search_query)

    if not filtered_rules:
        with col_export:
            st.empty()
        st.info("Tidak ada rules yang cocok dengan pencarian.")
        return

    df = rules_to_dataframe(filtered_rules)

    with col_export:
        st.download_button(
            "Ekspor CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"association_rules_{selected_key}.csv",
            mime="text/csv",
            width="stretch",
        )

    st.markdown("<div style='height:1.1rem'></div>", unsafe_allow_html=True)

    # ── Ringkasan metrik ──
    st.markdown('<div class="ar-section-label">Ringkasan Metrik</div>', unsafe_allow_html=True)
    render_metric_cards(filtered_rules, len(rules))

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── Sebaran kekuatan asosiasi ──
    with st.container(border=True):
        st.markdown(
            """
            <div class="ar-table-head">
                <span class="ar-table-title">Sebaran Kekuatan Asosiasi</span>
                <span class="ar-table-note">Lift = berapa kali lebih sering dari kebetulan</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_distribution(filtered_rules)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── Tabel rules ──
    with st.container(border=True):
        note = (
            f"Menampilkan {fmt_num(len(filtered_rules))} dari {fmt_num(len(rules))} rules"
            if search_query and len(filtered_rules) != len(rules)
            else "Diurutkan dari lift tertinggi"
        )
        st.markdown(
            f"""
            <div class="ar-table-head">
                <span class="ar-table-title">Daftar Association Rules</span>
                <span class="ar-table-note">{note}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_rules_table(df)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    with st.expander("Tentang metrik yang digunakan"):
        st.markdown(
            """
            **Support** — proporsi post yang memuat kombinasi hashtag tersebut.
            Support 0,05 berarti kombinasi itu muncul pada 5% dari seluruh post.

            **Confidence** — peluang hashtag *consequent* ikut muncul apabila hashtag
            *antecedent* sudah dipakai. Confidence 0,80 berarti pada 80% post yang
            memakai antecedent, consequent-nya ikut dipakai.

            **Lift** — berapa kali lebih sering dua hashtag muncul bersamaan dibanding
            jika kemunculannya murni kebetulan. Lift 3 berarti tiga kali lebih sering
            dari kebetulan. Nilai di atas 1 menandakan asosiasi positif, tepat 1 berarti
            tidak ada kaitan, dan di bawah 1 berarti keduanya justru cenderung tidak
            dipakai bersamaan.
            """
        )


main()

"""
pages/02_network_graph.py
Halaman Network Graph — visualisasi jaringan asosiasi hashtag menggunakan pyvis (vis-network).

Graph dan legenda dirender dalam satu dokumen HTML agar interaksi hover pada
legenda dapat menyorot node/edge yang bersangkutan di dalam graph.
"""

import streamlit as st

st.set_page_config(
    page_title="Network Graph | HashBI",
    page_icon="#",
    layout="wide",
    initial_sidebar_state="expanded",
)

import re
from pyvis.network import Network

from config import UNIVERSITIES, NETWORK_CONFIG, ASSETS_DIR
from components.sidebar import render_sidebar
from components.metric_card import render_page_header
from core.data_service import ensure_session_state_initialized


# ─────────────────────────────────────────────
# KATEGORI KEKUATAN ASOSIASI
# ─────────────────────────────────────────────
# Lift = berapa kali lebih sering dua hashtag muncul bersamaan
# dibanding jika kemunculannya murni kebetulan.
LIFT_CATEGORIES = [
    {
        "id": "kuat",
        "color": "#10b981",
        "label": "Sangat erat",
        "hint": "5x lebih sering dari kebetulan",
    },
    {
        "id": "erat",
        "color": "#3b82f6",
        "label": "Erat",
        "hint": "3-5x lebih sering",
    },
    {
        "id": "sedang",
        "color": "#6366f1",
        "label": "Cukup erat",
        "hint": "2-3x lebih sering",
    },
    {
        "id": "lemah",
        "color": "#94a3b8",
        "label": "Kurang erat",
        "hint": "di bawah 2x",
    },
]


def lift_category(lift: float) -> dict:
    """Petakan nilai lift ke kategori kekuatan asosiasi."""
    if lift >= 5:
        return LIFT_CATEGORIES[0]
    if lift >= 3:
        return LIFT_CATEGORIES[1]
    if lift >= 2:
        return LIFT_CATEGORIES[2]
    return LIFT_CATEGORIES[3]


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


def get_node_color(freq: int, max_freq: int) -> str:
    """
    Warna node berdasarkan jumlah koneksi.
    Gradasi cyan → violet: makin banyak koneksi, makin pekat ke ungu.
    """
    colors = [
        "#22d3ee",  # cyan  - koneksi paling sedikit
        "#38bdf8",  # sky
        "#60a5fa",  # blue
        "#818cf8",  # indigo
        "#a78bfa",  # violet
        "#8b5cf6",  # purple - koneksi paling banyak
    ]
    ratio = freq / max_freq if max_freq > 0 else 0
    index = min(int(ratio * (len(colors) - 1)), len(colors) - 1)
    return colors[index]


def build_graph_data(rules: list, top_n: int, min_lift: float) -> tuple[list, list]:
    """
    Bangun daftar node dan edge dari rules.
    Node = hashtag, Edge = pasangan asosiasi (antecedent → consequent).

    Returns: (nodes, edges) berupa list of dict siap dipakai pyvis.
    """
    filtered = [r for r in rules if r.get("lift", 0) >= min_lift]

    # Dedup pasangan berarah, ambil lift tertinggi per pasangan
    pair_best = {}
    for rule in filtered:
        lift = rule.get("lift", 0)
        confidence = rule.get("confidence", 0)
        for ant in rule.get("antecedents", []):
            for con in rule.get("consequents", []):
                if ant == con:
                    continue
                key = (ant, con)
                if key not in pair_best or lift > pair_best[key]["lift"]:
                    pair_best[key] = {"lift": lift, "confidence": confidence}

    if not pair_best:
        return [], []

    top_pairs = sorted(
        pair_best.items(), key=lambda kv: kv[1]["lift"], reverse=True
    )[:top_n]

    # Derajat tiap node menentukan ukuran & warna
    node_freq = {}
    for (ant, con), _ in top_pairs:
        node_freq[ant] = node_freq.get(ant, 0) + 1
        node_freq[con] = node_freq.get(con, 0) + 1

    max_freq = max(node_freq.values()) if node_freq else 1
    min_size = NETWORK_CONFIG["node_size_min"]
    max_size = NETWORK_CONFIG["node_size_max"]

    nodes = []
    for tag, freq in node_freq.items():
        nodes.append({
            "id": f"#{tag}",
            "label": f"#{tag}",
            "size": min_size + (freq / max_freq) * (max_size - min_size),
            "color": get_node_color(freq, max_freq),
            "degree": freq,
        })

    edges = []
    for (ant, con), info in top_pairs:
        cat = lift_category(info["lift"])
        edges.append({
            "source": f"#{ant}",
            "target": f"#{con}",
            "color": cat["color"],
            "cat": cat["id"],
            "lift": info["lift"],
            "confidence": info["confidence"],
            "width": 1 + info["confidence"] * 2.5,
        })

    return nodes, edges


# ─────────────────────────────────────────────
# RENDER GRAPH + LEGENDA (satu dokumen HTML)
# ─────────────────────────────────────────────

def build_network_html(nodes: list, edges: list, height: int = 520) -> str:
    """
    Bangun HTML pyvis, lalu suntikkan panel legenda interaktif.
    Legenda berada di dokumen yang sama dengan graph sehingga hover pada
    legenda dapat menyorot node/edge terkait.
    """
    net = Network(
        height=f"{height}px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#0f172a",
        cdn_resources="in_line",
    )

    for n in nodes:
        net.add_node(
            n["id"],
            label=n["label"],
            size=n["size"],
            color=n["color"],
            borderWidth=2,
            title=f"{n['label']} — terhubung ke {n['degree']} hashtag lain",
        )

    for e in edges:
        net.add_edge(
            e["source"],
            e["target"],
            color=e["color"],
            width=e["width"],
            liftcat=e["cat"],
            title=f"lift {e['lift']:.2f} · confidence {e['confidence']:.2f}",
        )

    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -5000,
          "centralGravity": 0.1,
          "springLength": 200,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "minVelocity": 0.75
      },
      "interaction": { "hover": true, "tooltipDelay": 120 },
      "nodes": { "shape": "dot", "font": { "size": 13, "face": "Inter" } },
      "edges": { "smooth": { "type": "continuous" }, "arrows": { "to": { "scaleFactor": 0.6 } } }
    }
    """)

    html = net.generate_html()

    # Buang referensi eksternal yang rusak / tak terpakai (bootstrap, node_modules)
    html = re.sub(r'<script[^>]*src="(?:\.\./node_modules|https://cdn\.jsdelivr)[^"]*"[^>]*>\s*</script>', "", html)
    html = re.sub(r'<link[^>]*href="(?:\.\./node_modules|https://cdn\.jsdelivr)[^"]*"[^>]*/?>', "", html)

    legend_items = "".join(
        f"""
        <div class="lg-item" data-cat="{c['id']}">
            <span class="lg-line" style="background:{c['color']}"></span>
            <span class="lg-txt">
                <span class="lg-label">{c['label']}</span>
                <span class="lg-hint">{c['hint']}</span>
            </span>
        </div>
        """
        for c in LIFT_CATEGORIES
    )

    panel = f"""
<style>
  html, body {{ margin:0; padding:0; background:transparent;
                font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif; }}

  /* pyvis memberi #mynetwork float:left sehingga elemen sesudahnya tertarik
     naik dan menimpa graph. Float dilepas agar legenda mengalir normal. */
  #mynetwork {{
      float:none !important;
      border:1px solid #e6e9f2 !important;
      border-radius:14px !important;
      background:#fdfdff !important;
      box-shadow:inset 0 1px 3px rgba(15,23,42,.04);
  }}
  .card {{ display:flow-root; border:none !important; background:transparent !important; }}

  .lg-wrap {{ clear:both; margin-top:20px; }}
  .lg-head {{ 
    font-size:11px; font-weight:700; letter-spacing:.08em;
              text-transform:uppercase; color:#94a3b8; margin-bottom:9px; }}
  /* align-items:start -> tiap kotak setinggi isinya sendiri, tidak dipaksa
     mengikuti kotak tetangga yang lebih tinggi. auto-fit + minmax membuat
     kolom turun ke bawah bila lebar iframe menyempit. */
  .lg-grid {{
      display:grid; gap:14px; align-items:start;
      grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));
  }}
  .lg-box {{
      border:1px solid #e6e9f2; border-radius:12px; padding:13px 15px;
      background:#fff; min-width:0; overflow-wrap:anywhere;
  }}
  .lg-title {{ font-size:12.5px; font-weight:700; color:#0f172a; margin-bottom:3px; }}
  .lg-sub {{ font-size:11.5px; color:#94a3b8; line-height:1.5; margin-bottom:11px; }}

  .lg-item {{ display:flex; align-items:center; gap:10px; padding:5px 8px;
              border-radius:8px; cursor:pointer; transition:background .15s ease; }}
  .lg-item:hover {{ background:#f6f7fb; }}
  .lg-line {{ width:22px; height:4px; border-radius:2px; flex-shrink:0; }}
  .lg-txt {{ display:flex; flex-direction:column; line-height:1.35; }}
  .lg-label {{ font-size:12.5px; font-weight:600; color:#0f172a; }}
  .lg-hint {{ font-size:11px; color:#94a3b8; }}

  .lg-scale {{ display:flex; align-items:center; gap:9px; margin-top:12px; }}
  .lg-dot-sm {{ width:9px;  height:9px;  border-radius:50%; background:#22d3ee; }}
  .lg-dot-lg {{ width:19px; height:19px; border-radius:50%; background:#8b5cf6; }}
  .lg-bar {{ flex:1; height:7px; border-radius:4px;
             background:linear-gradient(90deg,#22d3ee,#60a5fa,#a78bfa,#8b5cf6); }}
  .lg-scale-cap {{ display:flex; justify-content:space-between; font-size:10.5px;
                   color:#94a3b8; margin-top:6px; }}
  .lg-tip {{ margin-top:11px; font-size:11px; color:#94a3b8; line-height:1.5; }}
</style>

<div class="lg-wrap">
  <div class="lg-head">Cara Membaca Graph</div>
  <div class="lg-grid">

    <div class="lg-box">
      <div class="lg-title">Warna panah mendeskripsikan seberapa erat kaitannya</div>
      <div class="lg-sub">Arahkan kursor ke salah satu baris untuk menyorot
          pasangan hashtag dengan tingkat keeratan tersebut.</div>
      {legend_items}
    </div>

    <div class="lg-box">
      <div class="lg-title">Ukuran bulatan mendeskripsikan seberapa sering jadi penghubung</div>
      <div class="lg-sub">Bulatan makin besar dan makin ungu berarti hashtag itu
          terhubung ke makin banyak hashtag lain.</div>
      <div class="lg-scale">
        <span class="lg-dot-sm"></span>
        <span class="lg-bar"></span>
        <span class="lg-dot-lg"></span>
      </div>
      <div class="lg-scale-cap"><span>Sedikit koneksi</span><span>Banyak koneksi</span></div>
      <div class="lg-tip">Panah menunjukkan arah: hashtag asal &rarr; hashtag yang
          biasanya menyertainya. Klik dan geser bulatan untuk merapikan tampilan.</div>
    </div>

  </div>
</div>

<script>
(function () {{
  function ready(fn) {{
    if (typeof network !== 'undefined' && typeof edges !== 'undefined') fn();
    else setTimeout(function () {{ ready(fn); }}, 60);
  }}

  ready(function () {{
    var baseEdges = edges.get().map(function (e) {{
      return {{ id: e.id, color: e.color, width: e.width, liftcat: e.liftcat }};
    }});
    var baseNodes = nodes.get().map(function (n) {{
      return {{ id: n.id, color: n.color }};
    }});

    var FADE_EDGE = 'rgba(203,213,225,0.28)';
    var FADE_NODE = 'rgba(203,213,225,0.42)';

    function highlight(cat) {{
      var keepNodes = {{}};
      var eUpd = baseEdges.map(function (e) {{
        var on = e.liftcat === cat;
        if (on) {{
          var full = edges.get(e.id);
          keepNodes[full.from] = true;
          keepNodes[full.to] = true;
        }}
        return {{
          id: e.id,
          color: on ? e.color : FADE_EDGE,
          width: on ? e.width + 1.4 : e.width
        }};
      }});
      var nUpd = baseNodes.map(function (n) {{
        return {{ id: n.id, color: keepNodes[n.id] ? n.color : FADE_NODE }};
      }});
      edges.update(eUpd);
      nodes.update(nUpd);
    }}

    function reset() {{
      edges.update(baseEdges.map(function (e) {{
        return {{ id: e.id, color: e.color, width: e.width }};
      }}));
      nodes.update(baseNodes.map(function (n) {{
        return {{ id: n.id, color: n.color }};
      }}));
    }}

    document.querySelectorAll('.lg-item').forEach(function (el) {{
      el.addEventListener('mouseenter', function () {{ highlight(el.dataset.cat); }});
      el.addEventListener('mouseleave', reset);
    }});
  }});
}})();
</script>
"""

    return html.replace("</body>", panel + "\n</body>")


# ─────────────────────────────────────────────
# MAIN PAGE
# ─────────────────────────────────────────────

def init_page():
    ensure_session_state_initialized()
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    render_sidebar()


PAGE_CSS = """
<style>
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff;
    border: 1px solid #e6e9f2 !important;
    border-radius: 16px !important;
    box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 8px 20px -6px rgba(15,23,42,.07);
    padding: 1.25rem 1.4rem 1.3rem 1.4rem;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { border: none !important; }

.ng-section-label {
    display: inline-flex; align-items: center; gap: 8px;
    font-size: 11px; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: #94a3b8; margin-bottom: 6px;
}
.ng-card-divider { height: 1px; background: #eef1f7; margin: 0.95rem 0 0.15rem 0; }
.ng-chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 0.3rem 0 0.85rem 0; }
.ng-chip {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 5px 13px; border-radius: 999px;
    background: #f6f7fb; border: 1px solid #e6e9f2;
    font-size: 12px; font-weight: 600; color: #475569;
}
.ng-chip b { color: #0f172a; font-weight: 700; }
.ng-chip .dot { width: 7px; height: 7px; border-radius: 50%; }
</style>
"""


def main():
    init_page()

    selected_key = get_selected_key()
    rules = get_rules_for_selected()

    if selected_key == "all":
        title = "Network Graph"
        subtitle = "Visualisasi jaringan asosiasi hashtag dari semua universitas"
    else:
        univ_cfg = UNIVERSITIES.get(selected_key, {})
        title = f"Network Graph — {univ_cfg.get('name_short', '')}"
        subtitle = f"Pola asosiasi hashtag {univ_cfg.get('name', '')}"

    render_page_header(title=title, subtitle=subtitle, badge="pyvis")

    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div style="margin:0.25rem 0 0.9rem 0;">
            <div class="ng-section-label">Eksplorasi Jaringan</div>
            <div style="font-size:17px;font-weight:800;color:#0f172a;letter-spacing:-0.02em;">Jaringan Asosiasi Hashtag</div>
            <div style="font-size:13px;color:#64748b;margin-top:4px;line-height:1.55;max-width:820px;">
                Pasangan hashtag dengan <b>asosiasi terkuat</b> berdasarkan nilai <b>lift</b>.
                Bulatan mewakili hashtag, panah menunjukkan arah asosiasi.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(
            """
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <span style="font-size:15px;font-weight:700;color:#0f172a;">Hashtag Network</span>
                <span style="font-size:12px;color:#94a3b8;background:#f6f7fb;border:1px solid #e6e9f2;
                             padding:4px 12px;border-radius:999px;">Drag untuk menggeser (Scroll untuk zoom) </span>
            </div>
            <div class="ng-card-divider"></div>
            """,
            unsafe_allow_html=True,
        )

        ctrl1, ctrl2, _ = st.columns([1, 1, 2], gap="medium")
        with ctrl1:
            top_n_rules = st.slider("Jumlah koneksi (Top-N by lift)", 3, 100, 8, 1)
        with ctrl2:
            min_lift = st.slider("Min. lift", 1.0, 10.0, 1.0, 0.5)

        nodes, edges = build_graph_data(rules, top_n_rules, min_lift)

        if not rules:
            st.info("Belum ada data rules. Jalankan preprocessing terlebih dahulu.")
        elif not nodes:
            st.warning("Tidak ada rules yang memenuhi kriteria filter.")
        else:
            lifts = [e["lift"] for e in edges]
            st.markdown(
                f"""
                <div class="ng-chip-row">
                    <span class="ng-chip"><span class="dot" style="background:#8b5cf6;"></span>
                        <b>{len(nodes)}</b>&nbsp;hashtag</span>
                    <span class="ng-chip"><span class="dot" style="background:#6366f1;"></span>
                        <b>{len(edges)}</b>&nbsp;koneksi</span>
                    <span class="ng-chip"><span class="dot" style="background:#22d3ee;"></span>
                        rata-rata lift&nbsp;<b>{sum(lifts)/len(lifts):.2f}</b></span>
                    <span class="ng-chip"><span class="dot" style="background:#10b981;"></span>
                        lift tertinggi&nbsp;<b>{max(lifts):.2f}</b></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # height="content" membuat iframe menyesuaikan tinggi isinya
            # secara native, sehingga legenda tidak terpotong.
            st.iframe(
                build_network_html(nodes, edges, height=520),
                height="content",
            )


main()

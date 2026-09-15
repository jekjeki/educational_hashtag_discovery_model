"""
pages/05_rekomendasi.py
Halaman Rekomendasi Hashtag — ARM mining + GPT enrichment + Viral Scoring
Grounded Recommendation System untuk rekomendasi berbasis data historis.
"""

import streamlit as st

st.set_page_config(
    page_title="Rekomendasi | HashBI",
    page_icon="#",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
from config import UNIVERSITIES, ASSETS_DIR
from components.metric_card import render_rule_item, render_page_header
from components.sidebar import render_sidebar
from core.data_service import ensure_session_state_initialized
from services import get_sumopod_service

# Check if viral scoring is available (bypass core/__init__.py to avoid mlxtend dependency)
VIRAL_SCORING_AVAILABLE = False
enrich_recommendations_with_viral_scores = None

try:
    import importlib.util
    import sys
    from pathlib import Path

    # Get the path to viral_scoring.py
    current_dir = Path(__file__).parent.parent
    viral_scoring_path = current_dir / "core" / "viral_scoring.py"

    if viral_scoring_path.exists():
        spec = importlib.util.spec_from_file_location("viral_scoring", viral_scoring_path)
        viral_scoring_module = importlib.util.module_from_spec(spec)
        sys.modules["viral_scoring"] = viral_scoring_module
        spec.loader.exec_module(viral_scoring_module)

        enrich_recommendations_with_viral_scores = viral_scoring_module.enrich_recommendations_with_viral_scores
        VIRAL_SCORING_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not load viral_scoring module: {e}")
    VIRAL_SCORING_AVAILABLE = False

# ─── Daftar kata kampus yang harus difilter dari rekomendasi ───
_UNIV_KEYWORDS = {
    # BINUS
    "binus", "binusian", "binusuniversity", "binussemarang", "binusmalang",
    "binusbandung", "binusbekasi", "binuslife",
    # Telkom
    "telkom", "telu", "telkomuniversity", "telkomedu", "telunews",
    "telucampuslife", "telukampus", "telulife", "iamtelu",
    # Atma Jaya
    "atmajaya", "uajy", "atma", "atmajayayogyakarta", "unikaatmajaya",
    # UII
    "uii", "uiiyogyakarta", "uiiofficial", "islamicindonesia",
    # UMY
    "umy", "umyogya", "umygm", "muhammadiyahyogyakarta",
    # PCU / Petra
    "pcu", "petra", "lifeatpcu", "petrachristian", "petrauniversity", "ukpetra",
    # UMS
    "ums", "umsofficial", "umsofficialid", "muhammadiyahsurakarta",
    # Generic
    "universitas", "univ", "kampus",
}


def extract_keywords_from_text(text: str) -> list:
    """
    Ekstrak keyword potensial dari deskripsi konten sebagai fallback input ARM.

    Prioritas pengambilan:
    1. Hashtag yang tertulis di caption (#...) lebih dahulu, karena hashtag
       adalah sinyal tema paling kuat dan umumnya diletakkan di AKHIR caption
       sehingga rawan terpotong bila memakai urutan kata biasa.
    2. Kata biasa (> 3 huruf, bukan stopword) sesuai urutan kemunculan.

    Batas dinaikkan menjadi 30 keyword agar kata kunci di bagian akhir caption
    (termasuk hashtag seperti #Wisuda73...) tidak lagi terbuang.
    """
    import re
    stopwords = {
        "dan", "di", "ke", "dari", "yang", "ini", "itu", "dengan", "untuk",
        "pada", "adalah", "akan", "dalam", "telah", "tidak", "saya", "kami",
        "kita", "mereka", "oleh", "sebagai", "secara", "atau", "serta",
        "lebih", "antara", "setelah", "seperti", "sudah", "bisa", "juga",
        "hal", "bagi", "tentang", "karena", "saat", "semua", "sangat",
        "ada", "banyak", "satu", "dapat", "lain", "masih", "baru",
        "acara", "kegiatan", "program", "melalui", "hingga", "sebuah",
        "the", "and", "for", "with", "from", "that", "this",
    }
    text_lower = text.lower()
    keywords = []
    seen = set()

    def _add(word: str):
        w = word.strip().lower()
        if len(w) > 3 and w not in stopwords and w not in seen:
            seen.add(w)
            keywords.append(w)

    # 1) Hashtag lebih dulu: hashtag utuh + potongan katanya.
    #    "#Wisuda73BINUSUniversity" -> "wisuda73binusuniversity", "wisuda",
    #    "binusuniversity" (regex memisah pada karakter non-huruf).
    for tag in re.findall(r'#(\w+)', text_lower):
        _add(tag)
        for part in re.findall(r'[a-z]+', tag):
            _add(part)

    # 2) Kata biasa sesuai urutan kemunculan.
    for w in re.findall(r'[a-zA-Z]+', text_lower):
        _add(w)

    return keywords[:30]  # maksimum 30 keyword



def recommend_from_hashtag(input_tags: list, rules: list, top_n: int = 10) -> list:
    if not input_tags or not rules:
        return []

    input_set = set(tag.lstrip("#").lower() for tag in input_tags)
    matches   = []

    for rule in rules:
        ant_set = set(rule.get("antecedents", []))
        if ant_set & input_set:
            con_set = set(rule.get("consequents", [])) - input_set
            if con_set:
                matches.append({
                    "antecedents" : sorted(ant_set),
                    "consequents" : sorted(con_set),
                    "antecedents_str": rule.get("antecedents_str", ""),
                    "consequents_str": ", ".join([f"#{t}" for t in sorted(con_set)]),
                    "confidence"  : rule.get("confidence", 0),
                    "lift"        : rule.get("lift", 0),
                    "support"     : rule.get("support", 0),
                })

    matches = sorted(matches, key=lambda x: x["lift"], reverse=True)
    seen_cons = set()
    unique    = []
    for m in matches:
        key_str = str(sorted(m["consequents"]))
        if key_str not in seen_cons:
            seen_cons.add(key_str)
            unique.append(m)
        if len(unique) >= top_n:
            break

    return unique


def init_page():
    ensure_session_state_initialized()
    # Apply global CSS
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    render_sidebar()


@st.cache_resource(show_spinner=False)
def _get_llm_service():
    """Bangun client Sumopod sekali saja, bukan setiap rerun."""
    try:
        svc = get_sumopod_service()
        return svc, svc.is_configured()
    except Exception:
        return None, False


@st.cache_data(show_spinner=False)
def _flatten_sort_rules(signature: tuple, _rules_per_univ: dict) -> list:
    """Gabungkan rules seluruh universitas lalu urutkan menurun berdasarkan lift.

    Hanya `signature` yang dipakai sebagai kunci cache. Parameter
    `_rules_per_univ` diberi prefix underscore agar Streamlit melewatkan
    proses hashing dict berukuran besar tersebut.
    """
    all_rules = []
    for univ_data in _rules_per_univ.values():
        all_rules.extend(univ_data.get("rules", []))
    return sorted(all_rules, key=lambda x: x.get("lift", 0), reverse=True)


def main():
    init_page()

    # Custom CSS untuk halaman rekomendasi
    st.markdown("""
    <style>
    /* Style untuk st.container(border=True) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff !important;
        border-radius: 12px !important;
        padding: 24px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
        border: 1px solid #e2e8f0 !important;
    }

    /* Empty state card */
    .empty-state-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 44px 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border: 1px solid #e2e8f0;
        text-align: center;
        margin-top: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # HEADER
    render_page_header(
        title="Rekomendasi Hashtag",
        subtitle="Rekomendasi hashtag optimal berbasis pola asosiasi historis (ARM) yang diperkuat LLM",
    )

    # CHECK API LLM — client di-cache agar tidak dibangun ulang tiap rerun
    sumopod, api_configured = _get_llm_service()

    # LOCAL HELPERS
    def get_all_univ_rules() -> list:
        rules_per_univ = st.session_state.get("rules_per_univ", {})
        # Penggabungan + pengurutan ~94.000 rules cukup mahal untuk diulang
        # setiap rerun, jadi hasilnya di-cache berdasarkan jumlah rules per
        # universitas (berubah hanya bila data diproses ulang).
        signature = tuple(
            (k, len(v.get("rules", []))) for k, v in sorted(rules_per_univ.items())
        )
        return _flatten_sort_rules(signature, rules_per_univ)

    def extract_arm_candidates(hashtags: list, rules: list, top_n: int = 30) -> tuple:
        if not hashtags:
            return [], {}
        input_set = set(tag.lstrip("#").lower() for tag in hashtags)
        candidates = []
        candidates_with_metrics = {}
        for rule in rules:
            ant_set = set(rule.get("antecedents", []))
            if ant_set & input_set:
                for con in rule.get("consequents", []):
                    if con not in input_set and con not in candidates_with_metrics:
                        con_lower = con.lower()
                        if con_lower not in _UNIV_KEYWORDS and not any(keyword in con_lower for keyword in _UNIV_KEYWORDS):
                            candidates_with_metrics[con] = {
                                "confidence": rule.get("confidence", 0),
                                "lift": rule.get("lift", 0),
                                "support": rule.get("support", 0),
                            }
                            candidates.append(con)
        candidates = sorted(candidates, key=lambda x: candidates_with_metrics[x]["lift"], reverse=True)
        return candidates[:top_n], candidates_with_metrics

    def get_rules_from_selected(keys: list) -> list:
        rules_per_univ = st.session_state.get("rules_per_univ", {})
        all_r = []
        for key in keys:
            all_r.extend(rules_per_univ.get(key, {}).get("rules", []))
        return sorted(all_r, key=lambda x: x.get("lift", 0), reverse=True)

    # ─── INPUT CARD ───
    with st.container(border=True):
        st.markdown("<h4 style='font-size:16px;font-weight:600;color:#0f172a;margin:0 0 16px 0'>Input Konten</h4>", unsafe_allow_html=True)

        # Universitas + Tipe Konten
        col_u, col_t = st.columns([2, 1], gap="large")

        with col_u:
            st.markdown('<p style="font-size:13px;color:#64748b;margin-bottom:8px;font-weight:500">Universitas Referensi</p>', unsafe_allow_html=True)

            # st.pills menangani state secara native — tidak perlu st.rerun()
            # manual seperti pendekatan tombol sebelumnya yang memicu dua kali
            # rerun setiap klik sehingga terasa lambat.
            ALL_LABEL = "Semua Universitas"
            label_to_key = {UNIVERSITIES[k]["name_short"]: k for k in UNIVERSITIES}
            options = [ALL_LABEL] + list(label_to_key.keys())

            picked = st.pills(
                "Universitas Referensi",
                options=options,
                selection_mode="multi",
                default=[ALL_LABEL],
                label_visibility="collapsed",
                key="univ_pills",
            )
            picked = picked or []

            if ALL_LABEL in picked:
                selected_univs = list(UNIVERSITIES.keys())
                st.caption(f"Menggunakan seluruh {len(selected_univs)} universitas sebagai referensi.")
            else:
                selected_univs = [label_to_key[p] for p in picked if p in label_to_key]
                if not selected_univs:
                    st.caption("Pilih minimal satu universitas, atau pilih Semua Universitas.")

            st.session_state.selected_univs_ai = set(selected_univs)

        with col_t:
            st.markdown('<p style="font-size:13px;color:#64748b;margin-bottom:8px;font-weight:500">Tipe Konten</p>', unsafe_allow_html=True)
            content_type = st.radio(
                "content_type",
                options=["foto", "video"],
                format_func=lambda x: "Foto" if x == "foto" else "Video",
                horizontal=True,
                label_visibility="collapsed"
            )

        st.markdown("<div style='margin:16px 0'></div>", unsafe_allow_html=True)

        # Hashtag + Deskripsi
        col_h, col_d = st.columns([1, 2], gap="large")

        with col_h:
            st.markdown('<p style="font-size:13px;color:#64748b;margin-bottom:8px;font-weight:500">Hashtag Rencana (opsional)</p>', unsafe_allow_html=True)
            user_hashtags_input = st.text_input("user_tags", placeholder="wisuda, kampus, mahasiswa", label_visibility="collapsed")

        with col_d:
            st.markdown('<p style="font-size:13px;color:#64748b;margin-bottom:8px;font-weight:500">Deskripsi Konten</p>', unsafe_allow_html=True)
            caption_input = st.text_area("caption_desc", placeholder="Contoh: Hari ini kami menggelar Wisuda...", height=80, label_visibility="collapsed")

        st.markdown("<div style='margin:16px 0'></div>", unsafe_allow_html=True)

        # Mode selection
        col_mode, col_btn = st.columns([2, 1], gap="large")

        with col_mode:
            use_grounded = st.toggle(
                "Grounded Recommendation (dengan Viral Score)",
                value=True,
                help="Aktifkan untuk rekomendasi berbasis data historis dengan viral potential scoring. GPT hanya memilih dari vocabulary yang terbukti efektif."
            )

        with col_btn:
            gen_disabled = not bool(caption_input.strip()) or not bool(selected_univs)
            generate_clicked = st.button(
                "Generate Rekomendasi",
                type="primary",
                disabled=gen_disabled,
                use_container_width=True
            )

    # ─── RESULTS ───
    if not generate_clicked:
        st.markdown("""
        <div class="empty-state-card">
            <div style='width:44px;height:44px;border-radius:12px;background:#eef2ff;margin:0 auto 16px auto;
                        display:flex;align-items:center;justify-content:center;'>
                <div style='width:18px;height:18px;border-radius:50%;border:3px solid #6c4ae0;'></div>
            </div>
            <h3 style='font-size:18px;font-weight:600;color:#0f172a;margin:0 0 6px 0'>Hasil rekomendasi akan muncul di sini</h3>
            <p style='font-size:14px;color:#94a3b8;margin:0'>Isi form di atas, lalu klik <strong>Generate Rekomendasi</strong></p>
            <div style='margin-top:22px;padding:16px 18px;background:#f8fafc;border:1px solid #eef2f7;border-radius:10px;text-align:left;max-width:380px'>
                <p style='font-size:12px;color:#64748b;margin:0;line-height:1.7'>
                    <strong style='color:#475569'>Alur kerja:</strong><br>
                    1&nbsp;&middot;&nbsp;ARM Mining — ambil pola hashtag dari data historis<br>
                    2&nbsp;&middot;&nbsp;LLM Enrichment — evaluasi &amp; augmentasi semantik<br>
                    3&nbsp;&middot;&nbsp;Output — rekomendasi + sumber + alasan
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        gpt_result = {}
        recommendations = []
        summary = ""

        # STEP 1: ARM Mining
        all_rules = get_all_univ_rules()
        selected_universities = list(selected_univs)
        user_hashtags = [t.strip() for t in user_hashtags_input.split(",") if t.strip()] if user_hashtags_input.strip() else []

        # Fallback: jika user tidak input hashtag, ekstrak keyword dari deskripsi konten
        arm_input_tags = user_hashtags
        if not arm_input_tags and caption_input.strip():
            arm_input_tags = extract_keywords_from_text(caption_input)

        arm_candidates, candidates_metrics = extract_arm_candidates(arm_input_tags, all_rules, top_n=30)

        # Fallback kedua: jika masih kosong, ambil top hashtag dari seluruh rules
        if not arm_candidates and all_rules:
            top_tags = {}
            for rule in all_rules:
                for tag in rule.get("antecedents", []) + rule.get("consequents", []):
                    top_tags[tag] = top_tags.get(tag, 0) + 1
            sorted_tags = sorted(top_tags.items(), key=lambda x: x[1], reverse=True)[:30]
            arm_candidates = [tag for tag, _ in sorted_tags]
            # Also build basic metrics for these
            candidates_metrics = {}
            for tag in arm_candidates:
                for rule in all_rules:
                    if tag in rule.get("antecedents", []) or tag in rule.get("consequents", []):
                        if tag not in candidates_metrics:
                            candidates_metrics[tag] = {
                                "confidence": rule.get("confidence", 0),
                                "lift": rule.get("lift", 0),
                                "support": rule.get("support", 0),
                            }
                        else:
                            # Take best metrics
                            cm = candidates_metrics[tag]
                            cm["confidence"] = max(cm["confidence"], rule.get("confidence", 0))
                            cm["lift"] = max(cm["lift"], rule.get("lift", 0))
                            cm["support"] = max(cm["support"], rule.get("support", 0))

        # STEP 2: GPT with optional grounding
        if not api_configured:
            st.warning("API Key Sumopod belum dikonfigurasi. Hasil hanya dari ARM Mining.")
            recommendations = [{
                "hashtag": tag,
                "source": "arm",
                "confidence": candidates_metrics.get(tag, {}).get("confidence"),
                "lift": candidates_metrics.get(tag, {}).get("lift"),
                "reasoning": f"Lift: {candidates_metrics.get(tag, {}).get('lift', 0):.2f}"
            } for tag in arm_candidates[:15]]
            # Enrich with viral scores if available
            if VIRAL_SCORING_AVAILABLE and enrich_recommendations_with_viral_scores:
                recommendations = enrich_recommendations_with_viral_scores(
                    recommendations, university_keys=selected_universities
                )
            summary = "Rekomendasi hanya dari ARM (GPT tidak dikonfigurasi)."
        else:
            university_names = [UNIVERSITIES[key]["name_short"] for key in selected_universities]

            if use_grounded:
                # Use grounded recommendation system
                with st.spinner("Sedang memproses, mohon ditunggu"):
                    try:
                        gpt_result = sumopod.grounded_hashtag_recommendation(
                            content_description=caption_input,
                            university_keys=selected_universities,
                            content_type=content_type,
                            user_hashtags=user_hashtags if user_hashtags else None,
                            arm_candidates=arm_candidates,
                            max_recommendations=15,
                            vocabulary_size=150
                        )
                        recommendations = gpt_result.get("recommendations", [])
                        summary = gpt_result.get("summary", "")
                        confidence = gpt_result.get("confidence", "medium")
                    except Exception as e:
                        summary = f"Error: {str(e)}"
            else:
                # Use original enrichment
                with st.spinner("GPT sedang mengevaluasi dan enrich rekomendasi..."):
                    try:
                        gpt_result = sumopod.enrich_hashtag_recommendations(
                            arm_candidates=arm_candidates,
                            content_description=caption_input,
                            university_names=university_names,
                            content_type=content_type,
                            user_hashtags=user_hashtags if user_hashtags else None,
                            max_recommendations=15
                        )
                        recommendations = gpt_result.get("recommendations", [])
                        summary = gpt_result.get("summary", "")
                        # Enrich with viral scores if available
                        if VIRAL_SCORING_AVAILABLE and enrich_recommendations_with_viral_scores:
                            recommendations = enrich_recommendations_with_viral_scores(
                                recommendations, university_keys=selected_universities
                            )
                    except Exception as e:
                        summary = f"Error: {str(e)}"

        # ─── RESULT CARD ───
        with st.container(border=True):
            # Step badges
            st.markdown("""
            <div style='display:flex;align-items:center;gap:8px;margin-bottom:20px'>
                <span style='background:#3b82f6;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600'>Step 1</span>
                <span style='color:#64748b;font-size:14px'>ARM Mining</span>
                <span style='color:#d1d5db'>→</span>
                <span style='background:#10b981;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600'>Step 2</span>
                <span style='color:#64748b;font-size:14px'>GPT Enrichment</span>
            </div>
            """, unsafe_allow_html=True)

            # ARM status
            if arm_candidates:
                st.markdown(f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:12px;margin-bottom:20px"><p style="font-size:13px;color:#1e40af;margin:0">📊 ARM Mining: Ditemukan <strong>{len(arm_candidates)}</strong> hashtag kandidat dari Instagram</p></div>', unsafe_allow_html=True)

            if not recommendations:
                st.warning("Tidak ada rekomendasi yang dihasilkan.")
                with st.expander("Debug: Informasi Troubleshooting"):
                    if api_configured:
                        st.markdown("**Debug Info:**")
                        col_d1, col_d2, col_d3 = st.columns(3)
                        col_d1.metric("Vocabulary Size", gpt_result.get("_vocabulary_size", 0))
                        col_d2.metric("ARM Candidates", gpt_result.get("_arm_candidates_count", 0))
                        col_d3.metric("GPT Suggested", gpt_result.get("_gpt_suggested", 0))

                        if gpt_result.get("_error"):
                            st.error(f"Error: {gpt_result.get('_error')}")

                        st.markdown("**Raw GPT Response:**")
                        raw = gpt_result.get("_raw_response", "(tidak ada)")
                        st.code(raw, language="json")
                    else:
                        st.info("API tidak dikonfigurasi")
            else:
                # Title + unified badge
                mode_badge = "Grounded + Viral" if use_grounded else "ARM+GPT"
                badge_color = "#10b981" if use_grounded else "#8b5cf6"
                st.markdown(f"""
                <div style='display:flex;align-items:center;gap:10px;margin-bottom:16px'>
                    <h3 style='font-size:18px;font-weight:700;color:#0f172a;margin:0'>🎯 Rekomendasi Hashtag Final</h3>
                    <span style='background:{badge_color}20;color:{badge_color};padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600'>{mode_badge}</span>
                </div>
                """, unsafe_allow_html=True)

                # Summary - hanya tampilkan jika ada dan bukan error message
                if summary and not summary.startswith("Gagal") and not summary.startswith("Error") and not summary.startswith("Fallback"):
                    st.markdown(f"""
                    <div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px;margin-bottom:20px'>
                        <div style='display:flex;align-items:center;gap:8px;margin-bottom:8px'>
                            <span style='font-size:16px'>💭</span>
                            <span style='font-size:13px;font-weight:600;color:#166534'>Analisis Rekomendasi</span>
                        </div>
                        <p style='font-size:13px;color:#166534;margin:0;line-height:1.6'>{summary}</p>
                    </div>
                    """, unsafe_allow_html=True)

                # Hashtag chips with source badges
                chips = []
                for rec in recommendations:
                    tag = rec.get("hashtag", "")
                    source = rec.get("source", "").lower()
                    viral_score = rec.get("viral_score", 0)

                    # High viral badge
                    viral_badge = ""
                    if viral_score and viral_score >= 50:
                        viral_badge = f'<span style="font-size:10px;margin-left:4px" title="Viral Score: {viral_score:.1f}">🔥</span>'

                    chips.append(f'<span style="display:inline-flex;align-items:center;background:#eff6ff;color:#1e40af;padding:6px 16px;border-radius:20px;font-size:14px;font-family:monospace;font-weight:600;margin:4px;border:1px solid #bfdbfe">#{tag}{viral_badge}</span>')
                st.markdown(f'<div style="line-height:2.5;margin-bottom:16px">{"".join(chips)}</div>', unsafe_allow_html=True)

                # Legend for badges
                st.markdown("""
                <div style='display:flex;gap:16px;margin-bottom:16px;font-size:11px;color:#64748b'>
                    <span>🔥 High viral (score ≥50)</span>
                </div>
                """, unsafe_allow_html=True)

                # Detailed table with viral scores (if available)
                has_viral_scores = any(r.get("viral_score") for r in recommendations)

                if has_viral_scores:
                    st.markdown("<h4 style='font-size:14px;font-weight:600;color:#0f172a;margin:16px 0 8px 0'>📊 Detail Rekomendasi</h4>", unsafe_allow_html=True)

                    table_data = []
                    for rec in recommendations:
                        row = {
                            "Hashtag": f"#{rec.get('hashtag', '')}",
                            "Viral Score": rec.get("viral_score", 0),
                            "Avg Likes": int(rec.get("avg_likes", 0)),
                            "Lift": rec.get("lift", 1.0),
                        }
                        table_data.append(row)

                    df_table = pd.DataFrame(table_data)

                    # Display with column config
                    st.dataframe(
                        df_table,
                        column_config={
                            "Hashtag": st.column_config.TextColumn("Hashtag", width="medium"),
                            "Viral Score": st.column_config.ProgressColumn(
                                "Viral Score",
                                format="%.1f",
                                min_value=0,
                                max_value=100,
                            ),
                            "Avg Likes": st.column_config.NumberColumn("Avg Likes", format="%d"),
                            "Lift": st.column_config.NumberColumn("Lift", format="%.2f"),
                        },
                        hide_index=True,
                        use_container_width=True,
                    )

                # Stats
                st.markdown("<hr style='margin:20px 0;border:none;border-top:1px solid #e5e7eb'>", unsafe_allow_html=True)

                # Calculate stats
                avg_viral = 0
                viral_vals = [r.get("viral_score", 0) for r in recommendations if r.get("viral_score")]
                if viral_vals:
                    avg_viral = sum(viral_vals) / len(viral_vals)

                avg_lift = 0
                lift_vals = [r.get("lift") for r in recommendations if r.get("lift") is not None]
                if lift_vals:
                    avg_lift = sum(lift_vals) / len(lift_vals)

                arm_count = sum(1 for r in recommendations if r.get("source") in ("arm", "both"))
                vocab_count = sum(1 for r in recommendations if r.get("source") == "vocabulary")
                high_viral = sum(1 for r in recommendations if r.get("viral_score", 0) >= 50)

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total", len(recommendations))
                c2.metric("Avg Viral", f"{avg_viral:.1f}" if avg_viral else "-")
                c3.metric("Avg Lift", f"{avg_lift:.2f}" if avg_lift else "-")
                c4.metric("ARM Verified", arm_count)
                c5.metric("High Viral 🔥", high_viral)

                # Copy all
                all_tags = [f"#{rec['hashtag']}" for rec in recommendations]
                st.markdown("<hr style='margin:20px 0;border:none;border-top:1px solid #e5e7eb'>", unsafe_allow_html=True)
                st.markdown("<h4 style='font-size:14px;font-weight:600;color:#0f172a;margin:0 0 8px 0'>📋 Copy Semua Hashtag</h4>", unsafe_allow_html=True)
                st.text_area("copy_tags", value=" ".join(all_tags), height=60, label_visibility="collapsed")

        # SUPPLEMENTARY: Top Kombinasi
        selected_rules = get_rules_from_selected(selected_universities)
        with st.expander("\U0001f4ca Lihat Top Kombinasi Hashtag dari ARM"):
            if selected_rules:
                top_n = st.slider("Jumlah kombinasi", 5, 30, 10, key="top_n_slider")
                for rule in sorted(selected_rules, key=lambda x: x.get("lift", 0), reverse=True)[:top_n]:
                    render_rule_item(
                        antecedent=rule.get("antecedents_str", ""),
                        consequent=rule.get("consequents_str", ""),
                        lift=rule.get("lift", 0),
                    )

                df_dl = pd.DataFrame([{
                    "Antecedent": r.get("antecedents_str", ""),
                    "Consequent": r.get("consequents_str", ""),
                    "Support": r.get("support", 0),
                    "Confidence": r.get("confidence", 0),
                    "Lift": r.get("lift", 0),
                } for r in sorted(selected_rules, key=lambda x: x.get("lift", 0), reverse=True)[:top_n]])
                csv = df_dl.to_csv(index=False).encode("utf-8")
                st.download_button("\u2b07 Download CSV", csv, "top_kombinasi.csv", "text/csv")
            else:
                st.info("Tidak ada rules tersedia.")


main()

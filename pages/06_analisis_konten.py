"""
pages/06_analisis_konten.py
Halaman Analisis Konten — fitur pendukung berbasis LLM (Sumopod API).
Menganalisis kekurangan konten Instagram dan memberikan saran berbasis data.
"""

import streamlit as st

st.set_page_config(
    page_title="Analisis Konten | HashBI",
    page_icon="#",
    layout="wide",
    initial_sidebar_state="expanded",
)

import json
import os
from config import UNIVERSITIES, SUMOPOD_CONFIG, SUMOPOD_SYSTEM_PROMPT, ASSETS_DIR
from components.metric_card import render_page_header
from components.sidebar import render_sidebar
from core.data_service import ensure_session_state_initialized


# ─────────────────────────────────────────────
# SUMOPOD SERVICE (inline — tidak butuh import services/)
# ─────────────────────────────────────────────

def get_llm_client():
    """Init client Sumopod (OpenAI-compatible) dari API key di environment atau st.secrets."""
    try:
        from openai import OpenAI
        api_key = os.getenv("SUMOPOD_API_KEY") or st.secrets.get("SUMOPOD_API_KEY", "")
        if not api_key:
            return None
        return OpenAI(api_key=api_key, base_url=SUMOPOD_CONFIG["base_url"])
    except ImportError:
        return None


def analyze_with_llm(client, prompt: str) -> tuple[str, str]:
    """
    Kirim prompt ke Sumopod API.

    Returns: (isi, pesan_error). Salah satu selalu kosong.
    Balasan kosong ikut dideteksi agar tidak tampil sebagai hasil kosong
    tanpa penjelasan — kasus ini terjadi bila seluruh jatah token habis
    dipakai reasoning sehingga finish_reason bernilai "length".
    """
    try:
        response = client.chat.completions.create(
            model=SUMOPOD_CONFIG["model"],
            messages=[
                {"role": "system", "content": SUMOPOD_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=SUMOPOD_CONFIG["max_tokens"],
            temperature=SUMOPOD_CONFIG["temperature"],
        )
        choice = response.choices[0]
        isi = (choice.message.content or "").strip()

        if not isi:
            if choice.finish_reason == "length":
                return "", (
                    "Model kehabisan jatah token sebelum sempat menuliskan jawaban. "
                    "Naikkan nilai max_tokens pada SUMOPOD_CONFIG di config.py."
                )
            return "", f"Model tidak mengembalikan isi apa pun (finish_reason: {choice.finish_reason})."

        return isi, ""
    except Exception as e:
        return "", f"Gagal menghubungi Sumopod API: {e}"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_selected_key() -> str:
    return st.session_state.get("selected_university", "all")


def build_analysis_prompt(
    university_name: str,
    total_posts: int,
    avg_likes: float,
    avg_comments: float,
    avg_hashtags: float,
    top_hashtags: list,
    top_rules: list,
    low_engagement_posts: list = None,
) -> str:
    """Build prompt untuk analisis konten Instagram."""

    hashtag_str = ", ".join([f"#{h['hashtag']}" for h in top_hashtags[:10]])
    rules_str   = "\n".join([
        f"  - {r.get('antecedents_str', '')} → {r.get('consequents_str', '')} "
        f"(lift: {r.get('lift', 0):.2f}, confidence: {r.get('confidence', 0):.2f})"
        for r in top_rules[:5]
    ])

    prompt = f"""
Analisis data Instagram berikut untuk {university_name}:

DATA STATISTIK:
- Total post yang dianalisis: {total_posts}
- Rata-rata likes per post: {avg_likes:.1f}
- Rata-rata komentar per post: {avg_comments:.1f}
- Rata-rata jumlah hashtag per post: {avg_hashtags:.1f}

TOP HASHTAG YANG SERING DIGUNAKAN:
{hashtag_str}

POLA ASOSIASI HASHTAG TERKUAT (dari analisis Apriori):
{rules_str}

Berikan analisis mengenai:
1. Kekurangan strategi hashtag yang teridentifikasi dari data di atas
2. Pola hashtag mana yang sudah baik dan perlu dipertahankan
3. Kombinasi hashtag yang direkomendasikan berdasarkan pola asosiasi
4. Saran konkret untuk meningkatkan engagement konten Instagram {university_name}

Format jawaban dengan poin-poin yang jelas dan actionable.
"""
    return prompt.strip()


# ─────────────────────────────────────────────
# MAIN PAGE
# ─────────────────────────────────────────────

def main():
    # Init
    ensure_session_state_initialized()
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    render_sidebar()

    selected_key = get_selected_key()

    render_page_header(
        title="Analisis Konten",
        subtitle="Evaluasi kekurangan konten Instagram berbasis data historis",
        badge="AI Powered",
    )

    # ── API Key Check ──
    llm_client = get_llm_client()

    if not llm_client:
        st.warning(
            "Sumopod API key belum dikonfigurasi. "
            "Tambahkan `SUMOPOD_API_KEY` di environment variable atau `.streamlit/secrets.toml`.",
            icon="⚠️"
        )
        st.code("""
# .streamlit/secrets.toml
SUMOPOD_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxx"
        """, language="toml")

        st.markdown("""
        <div style="padding:1rem;background:#161b27;border-radius:8px;
        border:1px solid #252d3d;margin-top:0.5rem">
            <p style="font-size:13px;color:#7a8ba6;margin:0">
                Dapatkan API key di:
                <a href="https://sumopod.com" target="_blank"
                style="color:#3b82f6">sumopod.com</a>
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.stop()

    # ── Pilih Universitas ──
    # st.container(border=True) dipakai agar kartu benar-benar membungkus
    # widget di dalamnya. Menulis <div> lewat st.markdown tidak bisa
    # membungkus widget Streamlit karena tiap elemen dirender pada
    # container-nya sendiri, sehingga div-nya berakhir kosong.
    with st.container(border=True):
        st.markdown(
            "<h4 style='font-size:15px;font-weight:700;color:#0f172a;margin:0 0 14px 0'>Konfigurasi Analisis</h4>",
            unsafe_allow_html=True,
        )

        col_cfg1, col_cfg2 = st.columns(2, gap="medium")

        with col_cfg1:
            # Jika sudah pilih di sidebar, pakai itu; kalau "all", minta pilih spesifik
            if selected_key == "all":
                univ_options = {v["name"]: k for k, v in UNIVERSITIES.items()}
                selected_name = st.selectbox(
                    "Pilih Universitas untuk Dianalisis",
                    options=list(univ_options.keys()),
                )
                analysis_key = univ_options[selected_name]
            else:
                analysis_key  = selected_key
                selected_name = UNIVERSITIES[analysis_key]["name"]
                st.info(f"Menganalisis: **{selected_name}**")

        with col_cfg2:
            analysis_focus = st.multiselect(
                "Fokus Analisis",
                options=[
                    "Strategi Hashtag",
                    "Engagement Rate",
                    "Kombinasi Hashtag Optimal",
                    "Perbandingan dengan Tren Umum",
                ],
                default=["Strategi Hashtag", "Kombinasi Hashtag Optimal"],
            )

    # ── Load Data untuk Universitas Terpilih ──
    rules_per_univ   = st.session_state.get("rules_per_univ", {})
    freq_data        = st.session_state.get("hashtag_frequency", {})
    engagement_df    = st.session_state.get("engagement_summary", None)

    univ_rules  = rules_per_univ.get(analysis_key, {})
    rules_list  = univ_rules.get("rules", [])
    freq_list   = freq_data.get(analysis_key, [])
    total_posts = univ_rules.get("total_transactions", 0)

    # Engagement dari summary
    avg_likes    = 0.0
    avg_comments = 0.0
    avg_hashtags = 0.0

    if engagement_df is not None and not engagement_df.empty:
        row = engagement_df[engagement_df["university_key"] == analysis_key]
        if not row.empty:
            avg_likes    = float(row["avg_likes"].values[0])
            avg_comments = float(row["avg_comments"].values[0])
            avg_hashtags = float(row["avg_hashtags_per_post"].values[0])

    # ── Preview Data ──
    with st.expander("Lihat data yang akan dianalisis"):
        col_prev1, col_prev2 = st.columns(2, gap="medium")
        with col_prev1:
            st.markdown("**Statistik Engagement**")
            st.json({
                "total_posts"     : total_posts,
                "avg_likes"       : round(avg_likes, 2),
                "avg_comments"    : round(avg_comments, 2),
                "avg_hashtags"    : round(avg_hashtags, 2),
                "total_rules"     : len(rules_list),
            })
        with col_prev2:
            st.markdown("**Top 10 Hashtag**")
            st.write([f"#{h['hashtag']}" for h in freq_list[:10]])

    # ── Tombol Analisis ──
    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)

    if st.button(
        "Analisis Konten dengan AI",
        type="primary",
        use_container_width=False,
    ):
        if not freq_list and not rules_list:
            st.error("Data untuk universitas ini belum tersedia. Jalankan dulu generate_processed_data.py")
            st.stop()

        prompt = build_analysis_prompt(
            university_name  = selected_name,
            total_posts      = total_posts,
            avg_likes        = avg_likes,
            avg_comments     = avg_comments,
            avg_hashtags     = avg_hashtags,
            top_hashtags     = freq_list,
            top_rules        = rules_list,
        )

        with st.spinner(f"Menganalisis konten Instagram {selected_name}..."):
            result, err = analyze_with_llm(llm_client, prompt)

        if err:
            st.session_state.pop(f"analysis_result_{analysis_key}", None)
            st.error(err)
        else:
            st.session_state[f"analysis_result_{analysis_key}"] = result

    # ── Tampilkan Hasil ──
    result_key = f"analysis_result_{analysis_key}"
    if st.session_state.get(result_key):
        result = st.session_state[result_key]

        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            flex-wrap:wrap;gap:8px;margin-bottom:0.9rem;">
                    <span style="font-size:15px;font-weight:700;color:#0f172a;">
                        Hasil Analisis — {selected_name}</span>
                    <span style="font-size:12px;color:#94a3b8;background:#f6f7fb;
                                 border:1px solid #e6e9f2;padding:4px 12px;border-radius:999px;">
                        Sumopod &middot; {SUMOPOD_CONFIG['model']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Keluaran model berformat Markdown (daftar bernomor, penebalan).
            # Dirender dengan st.markdown agar formatnya tampil, sekaligus
            # memakai warna teks bawaan yang kontras pada latar terang.
            st.markdown(result)

        st.markdown("<div style='margin-top:0.75rem'></div>", unsafe_allow_html=True)

        # Download hasil
        st.download_button(
            label="Unduh Hasil Analisis (.txt)",
            data=result.encode("utf-8"),
            file_name=f"analisis_konten_{analysis_key}.txt",
            mime="text/plain",
        )


main()
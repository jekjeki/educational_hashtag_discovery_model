"""
config.py
Konfigurasi global HashBI Dashboard
Semua konstanta, path, warna, dan parameter Apriori didefinisikan di sini.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent

SCRAPED_DATA_DIR = BASE_DIR / "dataset"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
ASSETS_DIR = BASE_DIR / "assets"
METADATA_PATH = PROCESSED_DATA_DIR / "metadata.json"

# Output files dari pipeline Apriori
RULES_ALL_PATH = PROCESSED_DATA_DIR / "rules_all.csv"
RULES_PER_UNIV_PATH = PROCESSED_DATA_DIR / "rules_per_univ.json"
ENGAGEMENT_SUMMARY_PATH = PROCESSED_DATA_DIR / "engagement_summary.csv"


UNIVERSITIES = {
    "binus": {
        "name": "Binus University",
        "name_short": "BINUS",
        "file": "binusuniversityofficial_posts.json",
        "color": "#e53935",
        "qs_tier": 1,
        "qs_rank": "951–1.000",
    },
    "telkom": {
        "name": "Telkom University",
        "name_short": "Tel-U",
        "file": "telkomuniversity_posts.json",
        "color": "#f57c00",
        "qs_tier": 1,
        "qs_rank": "1.001–1.200",
    },
    "atmajaya": {
        "name": "Unika Atma Jaya",
        "name_short": "Atma Jaya",
        "file": "unikaatmajaya_posts.json",
        "color": "#8e24aa",
        "qs_tier": 2,
        "qs_rank": "1.201–1.400",
    },
    "uii": {
        "name": "Universitas Islam Indonesia",
        "name_short": "UII",
        "file": "uiiyogyakarta_posts.json",
        "color": "#1e88e5",
        "qs_tier": 2,
        "qs_rank": "1.201–1.400",
    },
    "umy": {
        "name": "Universitas Muhammadiyah Yogyakarta",
        "name_short": "UMY",
        "file": "umyogya_posts.json",
        "color": "#e53935",
        "qs_tier": 2,
        "qs_rank": "1.201–1.400",
    },
    "pcu": {
        "name": "Universitas Kristen Petra",
        "name_short": "UK Petra",
        "file": "lifeatpcu_posts.json",
        "color": "#00897b",
        "qs_tier": 3,
        "qs_rank": "1.401+",
    },
    "ums": {
        "name": "Universitas Muhammadiyah Surakarta",
        "name_short": "UMS",
        "file": "umsofficialid_posts.json",
        "color": "#c62828",
        "qs_tier": 3,
        "qs_rank": "1.401+",
    },
}

# ─────────────────────────────────────────────
# JUMLAH FOLLOWERS AKUN INSTAGRAM
# ─────────────────────────────────────────────
# Dicatat manual karena proses scraping tidak menyertakan jumlah followers.
# Dipakai untuk menghitung engagement rate sesuai definisi pada sub-bab 2.2:
#     ER = (likes + comments) / followers x 100%
# Nilai merupakan snapshot pada satu titik waktu pencatatan, bukan nilai
# historis saat masing-masing konten diunggah, sehingga ER bersifat perkiraan.
FOLLOWERS_SNAPSHOT_DATE = "Agustus 2026"

FOLLOWERS = {
    "binus": 206_000,
    "telkom": 295_000,
    "atmajaya": 53_000,
    "uii": 189_000,
    "umy": 139_000,
    "pcu": 34_600,
    "ums": 136_000,
}


QS_TIERS = {
    1: ["binus", "telkom"],
    2: ["atmajaya", "uii", "umy"],
    3: ["pcu", "ums"],
}

QS_TIER_COLORS = {
    1: "#f59e0b",
    2: "#3b82f6",
    3: "#10b981",
}

def get_university_options(include_all: bool = True) -> list:
    options = [{"key": k, "label": v["name"]} for k, v in UNIVERSITIES.items()]
    if include_all:
        options.insert(0, {"key": "all", "label": "Semua Universitas"})
    return options

def get_university_colors() -> dict:
    """Return dict {key: color} untuk semua universitas"""
    return {k: v["color"] for k, v in UNIVERSITIES.items()}

def get_university_names() -> dict:
    """Return dict {key: name_short} untuk semua universitas"""
    return {k: v["name_short"] for k, v in UNIVERSITIES.items()}



APRIORI_CONFIG = {

    "min_support": 0.02,
    "min_confidence": 0.4,
    "min_lift": 1.0,
    
    "support_range": (0.01, 0.5),
    "confidence_range": (0.1, 1.0),

    "top_n_rules": 20,
    "top_n_itemsets": 20,
    "top_n_hashtags": 15,
}


CAMPUS_KEYWORDS = {
    # BINUS
    "binus", "binusian", "binusuniversity",
    # Telkom — "telkom" mencakup varian salah ketik (#telkomuniverstiy),
    # "telu" mencakup akronim resmi Tel-U (#telunews, #teluproud, dst.)
    "telkom", "telkomuniversity", "telkomedu", "telkomsel", "telu",
    # Atma Jaya — "uaj" adalah akronim resmi (#uaj, #eventuaj, #pascasarjanauaj, dst.)
    "atmajaya", "unikaatmajaya", "atma", "uaj",
    # UII — termasuk varian penulisan "ii" -> "ll"/"li" dan "islam" -> "lslam"
    # yang muncul pada data hasil scraping (#kampusull, #ullyogyakarta, #uliyogyakarta)
    "uii", "uiiyogyakarta", "islamicindonesia",
    "islamindonesia", "lslamindonesia",
    "kampusull", "ullyogyakarta", "uliyogyakarta", "imull",
    # UMY
    "umy", "muhammadiyahyogyakarta",
    # PCU / Petra — "ukp" akronim Universitas Kristen Petra
    "pcu", "petra", "lifeatpcu", "petrachristian", "ukpetra", "ukp",
    # UMS
    "ums", "muhammadiyahsurakarta", "umsurakarta",
}

# Hashtag yang secara kebetulan mengandung substring pada CAMPUS_KEYWORDS
# namun bukan merupakan identitas kampus, sehingga dikecualikan dari filter.
# Contoh: "pendidikanuntukperadaban" mengandung substring "ukp".
CAMPUS_KEYWORD_EXCEPTIONS = {
    "pendidikanuntukperadaban",
}


# ─────────────────────────────────────────────
# SUMOPOD LLM CONFIG
# ─────────────────────────────────────────────
# Satu sumber kebenaran untuk seluruh fitur berbasis LLM pada sistem:
#   - pages/05_rekomendasi.py  (rekomendasi hashtag, via services/sumopod_service.py)
#   - pages/06_analisis_konten.py (analisis evaluatif konten)
# Sumopod menyediakan endpoint yang kompatibel dengan OpenAI SDK.
SUMOPOD_CONFIG = {
    "model": "gpt-5-mini",
    "base_url": "https://ai.sumopod.com/v1",
    # gpt-5-mini memakai sebagian jatah token untuk reasoning (teramati
    # 700-1024 token) yang tidak ikut tampil pada jawaban. Dengan batas 1024
    # seluruh jatah habis untuk reasoning sehingga balasan kembali kosong
    # (finish_reason "length"). Batas dinaikkan agar tersisa ruang untuk isi.
    "max_tokens": 4000,
    "temperature": 0.4,
}

# System prompt untuk analisis konten
SUMOPOD_SYSTEM_PROMPT = """Kamu adalah analis konten media sosial Instagram yang ahli dalam strategi hashtag untuk institusi pendidikan tinggi di Indonesia.
Berdasarkan data konten Instagram yang diberikan, analisis kekurangan konten tersebut dan berikan rekomendasi yang spesifik, praktis, dan berbasis data.
Gunakan Bahasa Indonesia yang profesional namun mudah dipahami oleh tim pemasaran universitas.
Format jawaban dalam poin-poin yang jelas dan actionable."""


# ─────────────────────────────────────────────
# DASHBOARD UI CONFIG
# ─────────────────────────────────────────────
DASHBOARD_CONFIG = {
    "title": "HashBI",
    "subtitle": "Hashtag Intelligence · Universitas Swasta Indonesia",
    "page_icon": "#",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# Warna untuk visualisasi network graph
NETWORK_CONFIG = {
    "node_color_default": "#3b82f6",
    "edge_color": "#374151",
    "node_size_min": 10,
    "node_size_max": 50,
    "top_n_edges": 30,        # Jumlah edges yang ditampilkan di network graph
}
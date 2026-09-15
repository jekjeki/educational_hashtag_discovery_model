"""
core/data_service.py
Service layer untuk mengakses data dari Streamlit session state.
Memisahkan logic pengambilan data dari UI layer.
"""

import streamlit as st
import pandas as pd
import json
from config import (
    UNIVERSITIES,
    APRIORI_CONFIG,
    PROCESSED_DATA_DIR,
    RULES_PER_UNIV_PATH,
    RULES_ALL_PATH,
    ENGAGEMENT_SUMMARY_PATH,
)


# ─────────────────────────────────────────────
# CACHED DATA LOADERS
# ─────────────────────────────────────────────

@st.cache_data
def _load_metadata() -> dict:
    """Load metadata dari file JSON."""
    path = PROCESSED_DATA_DIR / "metadata.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@st.cache_data
def _load_rules_all() -> pd.DataFrame:
    """Load semua rules dari CSV."""
    if RULES_ALL_PATH.exists():
        return pd.read_csv(RULES_ALL_PATH)
    return pd.DataFrame()

@st.cache_data
def _load_rules_per_univ() -> dict:
    """Load rules per universitas dari JSON."""
    if RULES_PER_UNIV_PATH.exists():
        with open(RULES_PER_UNIV_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@st.cache_data
def _load_engagement_summary() -> pd.DataFrame:
    """Load engagement summary dari CSV."""
    if ENGAGEMENT_SUMMARY_PATH.exists():
        return pd.read_csv(ENGAGEMENT_SUMMARY_PATH)
    return pd.DataFrame()

@st.cache_data
def _load_hashtag_frequency() -> dict:
    """Load hashtag frequency dari JSON."""
    path = PROCESSED_DATA_DIR / "hashtag_frequency.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def ensure_session_state_initialized():
    """
    Pastikan session state sudah diinisialisasi dengan default values.
    Function ini dipanggil di awal setiap page untuk handle akses langsung.
    Akan auto-load data dari file jika belum ter-load.
    """
    defaults = {
        "selected_university": "all",
        "data_loaded": False,
        "metadata": {},
        "rules_all": pd.DataFrame(),
        "rules_per_univ": {},
        "engagement_summary": pd.DataFrame(),
        "hashtag_frequency": {},
    }

    # Set default values jika key tidak ada
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Load data dari file jika belum di-load (handle storage and safe to browser)
    if not st.session_state.get("data_loaded", False):
        st.session_state.metadata = _load_metadata()
        st.session_state.rules_all = _load_rules_all()
        st.session_state.rules_per_univ = _load_rules_per_univ()
        st.session_state.engagement_summary = _load_engagement_summary()
        st.session_state.hashtag_frequency = _load_hashtag_frequency()
        st.session_state.data_loaded = True


def get_selected_university() -> str:
    """Return key universitas yang sedang dipilih dari session state."""
    return st.session_state.get("selected_university", "all")


def get_rules(university_key: str = None) -> list:
    """
    Return list of association rules untuk universitas tertentu.
    Jika key='all', gabungkan semua rules dan sort by lift.
    """
    key = university_key or get_selected_university()
    rules_per_univ = st.session_state.get("rules_per_univ", {})

    if key == "all":
        all_rules = []
        for univ_data in rules_per_univ.values():
            all_rules.extend(univ_data.get("rules", []))
        return sorted(all_rules, key=lambda x: x.get("lift", 0), reverse=True)

    return rules_per_univ.get(key, {}).get("rules", [])


def get_metadata(university_key: str = None) -> dict:
    """
    Return metadata (total_posts, unique_hashtags, total_rules, avg_lift, max_confidence).
    """
    key = university_key or get_selected_university()
    meta = st.session_state.get("metadata", {})

    if key == "all":
        return meta

    rules_per_univ = st.session_state.get("rules_per_univ", {})
    univ_data = rules_per_univ.get(key, {})
    rules = univ_data.get("rules", [])

    return {
        "total_posts": univ_data.get("total_transactions", 0),
        "total_unique_hashtags": univ_data.get("total_unique_hashtags", 0),
        "total_rules_all": univ_data.get("total_rules", 0),
        "avg_lift": _calc_avg_lift(rules),
        "max_confidence": _calc_max_confidence(rules),
    }


def get_post_count_per_university() -> dict:
    """Return dict {university_key: post_count}."""
    rules_per_univ = st.session_state.get("rules_per_univ", {})
    return {
        k: v.get("total_transactions", 0)
        for k, v in rules_per_univ.items()
        if k in UNIVERSITIES
    }


def get_rules_count_per_university() -> dict:
    """Return dict {university_key: rules_count}."""
    rules_per_univ = st.session_state.get("rules_per_univ", {})
    return {
        k: v.get("total_rules", 0)
        for k, v in rules_per_univ.items()
        if k in UNIVERSITIES
    }


def get_hashtag_frequency(university_key: str = None) -> list:
    """Return list of hashtag frequency data."""
    key = university_key or get_selected_university()
    freq_data = st.session_state.get("hashtag_frequency", {})
    freq_key = key if key in freq_data else "all"
    return freq_data.get(freq_key, [])


def get_engagement_summary() -> pd.DataFrame:
    """Return engagement summary DataFrame dari session state."""
    return st.session_state.get("engagement_summary", pd.DataFrame())


def get_university_display_info(university_key: str = None) -> dict:
    """
    Return display info untuk header page.
    Returns: {title, subtitle}
    """
    key = university_key or get_selected_university()

    if key == "all":
        return {
            "title": "Overview",
            "subtitle": "Ringkasan analisis asosiasi hashtag dari 7 universitas swasta Indonesia",
        }

    univ_cfg = UNIVERSITIES.get(key, {})
    return {
        "title": f"Overview — {univ_cfg.get('name', '')}",
        "subtitle": f"QS WUR {univ_cfg.get('qs_rank', '')} · Tier {univ_cfg.get('qs_tier', '')}",
    }


def get_min_support_used() -> float:
    """Return min support yang digunakan (dari metadata atau default)."""
    meta = st.session_state.get("metadata", {})
    return meta.get("min_support_used", APRIORI_CONFIG["min_support"])


# ─────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────

def _calc_avg_lift(rules: list) -> float:
    if not rules:
        return 0.0
    return round(sum(r.get("lift", 0) for r in rules) / len(rules), 2)


def _calc_max_confidence(rules: list) -> float:
    if not rules:
        return 0.0
    return round(max(r.get("confidence", 0) for r in rules), 2)

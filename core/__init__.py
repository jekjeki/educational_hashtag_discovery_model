# core/__init__.py
from core.preprocessing import load_university_data, preprocess_hashtags, filter_campus_hashtags
from core.apriori_engine import run_apriori, run_apriori_all
from core.engagement import compute_engagement_summary
from core.data_service import (
    ensure_session_state_initialized,
    get_selected_university,
    get_rules,
    get_metadata,
    get_post_count_per_university,
    get_rules_count_per_university,
    get_hashtag_frequency,
    get_engagement_summary,
    get_university_display_info,
    get_min_support_used,
)
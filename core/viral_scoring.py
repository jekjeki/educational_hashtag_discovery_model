"""
core/viral_scoring.py
Modul untuk menghitung Viral Potential Score per hashtag.
Berdasarkan 3 faktor: engagement rata-rata, frekuensi penggunaan, dan lift dari ARM.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from config import SCRAPED_DATA_DIR, UNIVERSITIES, PROCESSED_DATA_DIR


# ─────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────

def load_raw_posts(university_keys: List[str] = None) -> pd.DataFrame:
    """
    Load raw posts dari dataset untuk universitas tertentu.

    Args:
        university_keys: List key universitas. None = semua universitas.

    Returns:
        DataFrame dengan kolom: university_key, likes, comments, hashtags, etc.
    """
    if university_keys is None:
        university_keys = list(UNIVERSITIES.keys())

    all_posts = []

    for key in university_keys:
        univ_config = UNIVERSITIES.get(key)
        if not univ_config:
            continue

        file_path = SCRAPED_DATA_DIR / univ_config["file"]
        if not file_path.exists():
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                posts = json.load(f)

            for post in posts:
                post["university_key"] = key
                all_posts.append(post)
        except Exception:
            continue

    if not all_posts:
        return pd.DataFrame()

    df = pd.DataFrame(all_posts)

    # Ensure numeric columns
    for col in ["likes", "comments"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def load_hashtag_frequency() -> Dict:
    """Load hashtag frequency dari processed data."""
    path = PROCESSED_DATA_DIR / "hashtag_frequency.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_rules_per_univ() -> Dict:
    """Load rules per universitas dari processed data."""
    path = PROCESSED_DATA_DIR / "rules_per_univ.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ─────────────────────────────────────────────
# ENGAGEMENT PER HASHTAG CALCULATOR
# ─────────────────────────────────────────────

def calculate_hashtag_engagement_stats(
    df: pd.DataFrame,
    university_keys: List[str] = None
) -> Dict[str, Dict]:
    """
    Hitung statistik engagement per hashtag.

    Args:
        df: DataFrame posts dengan kolom hashtags, likes, comments
        university_keys: Filter universitas (None = semua)

    Returns:
        Dict {hashtag: {avg_likes, avg_comments, avg_engagement, post_count, total_engagement}}
    """
    if df.empty or "hashtags" not in df.columns:
        return {}

    # Filter universitas jika diperlukan
    if university_keys:
        df = df[df["university_key"].isin(university_keys)]

    hashtag_stats = {}

    for _, row in df.iterrows():
        hashtags = row.get("hashtags", [])
        if not isinstance(hashtags, list):
            continue

        likes = row.get("likes", 0) or 0
        comments = row.get("comments", 0) or 0
        engagement = likes + comments

        for tag in hashtags:
            tag_lower = str(tag).lower().strip()
            if not tag_lower:
                continue

            if tag_lower not in hashtag_stats:
                hashtag_stats[tag_lower] = {
                    "total_likes": 0,
                    "total_comments": 0,
                    "total_engagement": 0,
                    "post_count": 0,
                }

            hashtag_stats[tag_lower]["total_likes"] += likes
            hashtag_stats[tag_lower]["total_comments"] += comments
            hashtag_stats[tag_lower]["total_engagement"] += engagement
            hashtag_stats[tag_lower]["post_count"] += 1

    # Calculate averages
    result = {}
    for tag, stats in hashtag_stats.items():
        count = stats["post_count"]
        if count > 0:
            result[tag] = {
                "avg_likes": round(stats["total_likes"] / count, 2),
                "avg_comments": round(stats["total_comments"] / count, 2),
                "avg_engagement": round(stats["total_engagement"] / count, 2),
                "post_count": count,
                "total_engagement": stats["total_engagement"],
            }

    return result


def get_lift_for_hashtag(
    hashtag: str,
    rules: List[Dict],
    default_lift: float = 1.0
) -> float:
    """
    Ambil nilai lift tertinggi untuk hashtag dari ARM rules.

    Args:
        hashtag: Nama hashtag (tanpa #)
        rules: List rules dari ARM
        default_lift: Nilai default jika tidak ditemukan

    Returns:
        Nilai lift tertinggi
    """
    hashtag_lower = hashtag.lower().strip()
    max_lift = default_lift

    for rule in rules:
        antecedents = [str(t).lower() for t in rule.get("antecedents", [])]
        consequents = [str(t).lower() for t in rule.get("consequents", [])]

        if hashtag_lower in antecedents or hashtag_lower in consequents:
            lift = rule.get("lift", default_lift)
            max_lift = max(max_lift, lift)

    return max_lift


# ─────────────────────────────────────────────
# VIRAL POTENTIAL SCORE CALCULATOR
# ─────────────────────────────────────────────

def calculate_viral_score(
    hashtag: str,
    engagement_stats: Dict[str, Dict],
    frequency_data: List[Dict],
    rules: List[Dict],
    total_posts: int = 1,
    weights: Dict[str, float] = None
) -> Dict:
    """
    Hitung viral potential score untuk satu hashtag.

    Formula:
    viral_score = (normalized_engagement * w1) + (frequency_score * w2) + (lift_bonus * w3)

    Args:
        hashtag: Nama hashtag (tanpa #)
        engagement_stats: Dict engagement per hashtag dari calculate_hashtag_engagement_stats
        frequency_data: List frequency data dari hashtag_frequency.json
        rules: List rules dari ARM
        total_posts: Total posts untuk normalisasi frekuensi
        weights: Optional custom weights {engagement, frequency, lift}

    Returns:
        Dict {
            viral_score, avg_likes, avg_comments, post_count,
            frequency, frequency_pct, lift, components
        }
    """
    if weights is None:
        weights = {
            "engagement": 0.50,  # Engagement paling penting
            "frequency": 0.30,   # Popularitas
            "lift": 0.20,        # Kekuatan asosiasi
        }

    hashtag_lower = hashtag.lower().strip()

    # 1. Engagement score
    stats = engagement_stats.get(hashtag_lower, {})
    avg_likes = stats.get("avg_likes", 0)
    avg_comments = stats.get("avg_comments", 0)
    avg_engagement = stats.get("avg_engagement", 0)
    post_count = stats.get("post_count", 0)

    # Normalize engagement (0-100 scale, capped at 5000 avg engagement)
    max_engagement = 5000  # Cap for normalization
    normalized_engagement = min(avg_engagement / max_engagement * 100, 100) if avg_engagement > 0 else 0

    # 2. Frequency score
    frequency = 0
    frequency_pct = 0.0
    for item in frequency_data:
        if item.get("hashtag", "").lower() == hashtag_lower:
            frequency = item.get("frequency", 0)
            frequency_pct = item.get("percentage", 0)
            break

    # Normalize frequency (0-100 scale)
    frequency_score = min(frequency_pct * 5, 100)  # 20% frequency = 100 score

    # 3. Lift bonus
    lift = get_lift_for_hashtag(hashtag_lower, rules)
    # Normalize lift (1.0 = 0, 3.0+ = 100)
    lift_bonus = min(max((lift - 1.0) / 2.0 * 100, 0), 100)

    # Calculate final viral score
    viral_score = (
        normalized_engagement * weights["engagement"] +
        frequency_score * weights["frequency"] +
        lift_bonus * weights["lift"]
    )

    return {
        "hashtag": hashtag_lower,
        "viral_score": round(viral_score, 2),
        "avg_likes": avg_likes,
        "avg_comments": avg_comments,
        "avg_engagement": avg_engagement,
        "post_count": post_count,
        "frequency": frequency,
        "frequency_pct": frequency_pct,
        "lift": round(lift, 2),
        "components": {
            "engagement_component": round(normalized_engagement * weights["engagement"], 2),
            "frequency_component": round(frequency_score * weights["frequency"], 2),
            "lift_component": round(lift_bonus * weights["lift"], 2),
        }
    }


def batch_calculate_viral_scores(
    hashtags: List[str],
    university_keys: List[str] = None,
    top_n: int = None
) -> List[Dict]:
    """
    Hitung viral scores untuk batch hashtags.

    Args:
        hashtags: List nama hashtag
        university_keys: List key universitas untuk context
        top_n: Jika diset, return hanya top N berdasarkan viral score

    Returns:
        List of viral score dicts, sorted by viral_score descending
    """
    # Load data
    df = load_raw_posts(university_keys)
    freq_data_all = load_hashtag_frequency()
    rules_data = load_rules_per_univ()

    # Combine frequency data dari universitas yang dipilih
    combined_freq = {}
    if university_keys:
        for key in university_keys:
            for item in freq_data_all.get(key, []):
                tag = item.get("hashtag", "").lower()
                if tag not in combined_freq:
                    combined_freq[tag] = {"hashtag": tag, "frequency": 0, "percentage": 0}
                combined_freq[tag]["frequency"] += item.get("frequency", 0)
                combined_freq[tag]["percentage"] += item.get("percentage", 0)
    else:
        # Gabungkan semua
        for key, freq_list in freq_data_all.items():
            for item in freq_list:
                tag = item.get("hashtag", "").lower()
                if tag not in combined_freq:
                    combined_freq[tag] = {"hashtag": tag, "frequency": 0, "percentage": 0}
                combined_freq[tag]["frequency"] += item.get("frequency", 0)
                combined_freq[tag]["percentage"] += item.get("percentage", 0)

    frequency_list = list(combined_freq.values())

    # Combine rules dari universitas yang dipilih
    combined_rules = []
    if university_keys:
        for key in university_keys:
            combined_rules.extend(rules_data.get(key, {}).get("rules", []))
    else:
        for key, data in rules_data.items():
            combined_rules.extend(data.get("rules", []))

    # Calculate engagement stats
    engagement_stats = calculate_hashtag_engagement_stats(df, university_keys)

    # Calculate viral scores
    results = []
    for tag in hashtags:
        score_data = calculate_viral_score(
            hashtag=tag,
            engagement_stats=engagement_stats,
            frequency_data=frequency_list,
            rules=combined_rules,
            total_posts=len(df) if not df.empty else 1,
        )
        results.append(score_data)

    # Sort by viral score
    results.sort(key=lambda x: x["viral_score"], reverse=True)

    if top_n:
        return results[:top_n]

    return results


def get_top_viral_hashtags(
    university_keys: List[str] = None,
    top_n: int = 50,
    min_post_count: int = 3
) -> List[Dict]:
    """
    Ambil top N hashtag dengan viral score tertinggi dari data historis.
    Berguna untuk membuat vocabulary grounding untuk GPT.

    Args:
        university_keys: List key universitas
        top_n: Jumlah hashtag yang diambil
        min_post_count: Minimum post count untuk dimasukkan

    Returns:
        List of viral score dicts
    """
    # Load data
    df = load_raw_posts(university_keys)
    freq_data_all = load_hashtag_frequency()
    rules_data = load_rules_per_univ()

    # Get all unique hashtags
    all_hashtags = set()
    if university_keys:
        for key in university_keys:
            for item in freq_data_all.get(key, []):
                all_hashtags.add(item.get("hashtag", "").lower())
    else:
        for key, freq_list in freq_data_all.items():
            for item in freq_list:
                all_hashtags.add(item.get("hashtag", "").lower())

    # Calculate scores for all
    scores = batch_calculate_viral_scores(
        hashtags=list(all_hashtags),
        university_keys=university_keys
    )

    # Filter by min post count
    filtered = [s for s in scores if s.get("post_count", 0) >= min_post_count]

    return filtered[:top_n]


def get_vocabulary_for_grounding(
    university_keys: List[str] = None,
    top_n: int = 100,
    min_post_count: int = 2
) -> Tuple[List[str], Dict[str, Dict]]:
    """
    Generate vocabulary hashtag untuk grounding GPT recommendation.

    Args:
        university_keys: List key universitas
        top_n: Jumlah hashtag vocabulary
        min_post_count: Minimum post count

    Returns:
        Tuple (list of hashtag strings, dict of hashtag to score data)
    """
    scores = get_top_viral_hashtags(
        university_keys=university_keys,
        top_n=top_n,
        min_post_count=min_post_count
    )

    vocabulary = [s["hashtag"] for s in scores]
    score_map = {s["hashtag"]: s for s in scores}

    return vocabulary, score_map


def enrich_recommendations_with_viral_scores(
    recommendations: List[Dict],
    university_keys: List[str] = None
) -> List[Dict]:
    """
    Enrich existing recommendations dengan viral scores.

    Args:
        recommendations: List of recommendation dicts dengan key 'hashtag'
        university_keys: List key universitas untuk context

    Returns:
        List of enriched recommendations dengan viral_score, avg_likes, dll
    """
    if not recommendations:
        return []

    hashtags = [r.get("hashtag", "") for r in recommendations if r.get("hashtag")]
    scores = batch_calculate_viral_scores(hashtags, university_keys)

    # Create score map
    score_map = {s["hashtag"].lower(): s for s in scores}

    # Enrich recommendations
    enriched = []
    for rec in recommendations:
        tag = rec.get("hashtag", "").lower()
        score_data = score_map.get(tag, {})

        enriched_rec = {**rec}
        enriched_rec["viral_score"] = score_data.get("viral_score", 0)
        enriched_rec["avg_likes"] = score_data.get("avg_likes", 0)
        enriched_rec["avg_comments"] = score_data.get("avg_comments", 0)
        enriched_rec["post_count"] = score_data.get("post_count", 0)
        enriched_rec["lift"] = score_data.get("lift", 1.0)
        enriched_rec["frequency"] = score_data.get("frequency", 0)

        enriched.append(enriched_rec)

    # Sort by viral score
    enriched.sort(key=lambda x: x.get("viral_score", 0), reverse=True)

    return enriched

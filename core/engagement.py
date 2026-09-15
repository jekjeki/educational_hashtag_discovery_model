import pandas as pd
import numpy as np
from config import UNIVERSITIES, FOLLOWERS


# ─────────────────────────────────────────────
# ENGAGEMENT METRICS
# ─────────────────────────────────────────────

def compute_engagement_rate(row: pd.Series) -> float:
    """
    Hitung engagement rate per post.
    Formula: (likes + comments) / followers * 100
    """
    likes = row.get("likes", 0) or 0
    comments = row.get("comments", 0) or 0
    followers = row.get("followers", 0) or 0

    total_engagement = likes + comments

    if followers > 0:
        return round((total_engagement / followers) * 100, 4)
    return float(total_engagement)


def compute_engagement_rate_per_university(
    avg_likes: float, avg_comments: float, university_key: str
) -> float:
    """
    Engagement rate satu universitas mengikuti definisi pada sub-bab 2.2:
        ER = (rata-rata likes + rata-rata comments) / followers x 100%

    Mengembalikan 0.0 bila jumlah followers universitas tersebut belum tercatat
    pada FOLLOWERS di config.py.
    """
    followers = FOLLOWERS.get(university_key, 0)
    if not followers:
        return 0.0
    return round(((avg_likes + avg_comments) / followers) * 100, 2)


def compute_engagement_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung ringkasan engagement per universitas.

    Returns DataFrame dengan kolom:
    - university_key, university_name
    - total_posts, avg_likes, avg_comments
    - avg_engagement, max_engagement
    - total_hashtags_used, avg_hashtags_per_post
    """
    if df.empty:
        return pd.DataFrame()

    for col in ["likes", "comments"]:
        if col not in df.columns:
            df[col] = 0


    if "hashtags" in df.columns:
        df["hashtag_count"] = df["hashtags"].apply(
            lambda x: len(x) if isinstance(x, list) else 0
        )
    else:
        df["hashtag_count"] = 0

    summary = df.groupby("university_key").agg(
        university_name=("university_name", "first"),
        university_short=("university_short", "first"),
        qs_tier=("qs_tier", "first"),
        total_posts=("university_key", "count"),
        avg_likes=("likes", "mean"),
        avg_comments=("comments", "mean"),
        total_hashtags_used=("hashtag_count", "sum"),
        avg_hashtags_per_post=("hashtag_count", "mean"),
    ).reset_index()

    numeric_cols = ["avg_likes", "avg_comments", "avg_hashtags_per_post"]
    summary[numeric_cols] = summary[numeric_cols].round(2)

    return summary


def get_engagement_trend(df: pd.DataFrame, university_key: str = None) -> pd.DataFrame:
    """
    Hitung tren engagement per bulan.

    Returns DataFrame dengan kolom: date, avg_likes, avg_comments, post_count
    """
    if df.empty:
        return pd.DataFrame()

    data = df.copy()

    if university_key and university_key != "all":
        data = data[data["university_key"] == university_key]

    # Parse tanggal
    if "date" not in data.columns:
        return pd.DataFrame()

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"])
    data["month"] = data["date"].dt.to_period("M")

    trend = data.groupby("month").agg(
        avg_likes=("likes", "mean"),
        avg_comments=("comments", "mean"),
        post_count=("university_key", "count"),
    ).reset_index()

    trend["month"] = trend["month"].astype(str)
    trend[["avg_likes", "avg_comments"]] = trend[["avg_likes", "avg_comments"]].round(2)

    return trend


def get_top_posts(
    df: pd.DataFrame,
    university_key: str = None,
    top_n: int = 10,
    sort_by: str = "likes"
) -> pd.DataFrame:
    """
    Return top N posts berdasarkan metrik engagement tertentu.
    """
    data = df.copy()

    if university_key and university_key != "all":
        data = data[data["university_key"] == university_key]

    if sort_by not in data.columns:
        sort_by = "likes"

    cols = ["university_short", "date", "likes", "comments", "hashtags", "url"]
    available_cols = [c for c in cols if c in data.columns]

    return (
        data[available_cols]
        .sort_values(sort_by, ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def get_hashtag_engagement_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analisis korelasi antara jumlah hashtag dan engagement.
    Return DataFrame dengan bucket jumlah hashtag dan rata-rata engagement.
    """
    data = df.copy()

    if "hashtags" not in data.columns or "likes" not in data.columns:
        return pd.DataFrame()

    data["hashtag_count"] = data["hashtags"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )

    # Buat bucket
    bins = [0, 3, 6, 10, 15, 20, 30]
    labels = ["1-3", "4-6", "7-10", "11-15", "16-20", "21-30"]
    data["hashtag_bucket"] = pd.cut(
        data["hashtag_count"],
        bins=bins,
        labels=labels,
        right=True
    )

    corr = data.groupby("hashtag_bucket", observed=True).agg(
        avg_likes=("likes", "mean"),
        avg_comments=("comments", "mean"),
        post_count=("university_key", "count"),
    ).reset_index()

    corr[["avg_likes", "avg_comments"]] = corr[["avg_likes", "avg_comments"]].round(2)

    return corr
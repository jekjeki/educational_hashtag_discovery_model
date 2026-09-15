import json
import pandas as pd
from pathlib import Path
from collections import Counter
from config import (
    SCRAPED_DATA_DIR,
    UNIVERSITIES,
    CAMPUS_KEYWORDS,
    CAMPUS_KEYWORD_EXCEPTIONS,
)

def load_raw_json(filepath: Path) -> list:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_university_data(university_key: str) -> pd.DataFrame:
    config = UNIVERSITIES.get(university_key)
    if not config:
        raise ValueError(f"University key '{university_key}' tidak ditemukan di config.")

    filepath = SCRAPED_DATA_DIR / config["file"]
    if not filepath.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {filepath}")

    raw = load_raw_json(filepath)
    df = pd.DataFrame(raw)

    # Tambahkan kolom universitas
    df["university_key"] = university_key
    df["university_name"] = config["name"]
    df["university_short"] = config["name_short"]
    df["qs_tier"] = config["qs_tier"]

    return df


def load_all_universities() -> pd.DataFrame:
    """
    Load dan gabungkan data semua universitas menjadi satu DataFrame.
    Universitas yang file JSON-nya belum ada akan di-skip dengan warning.
    """
    frames = []
    for key in UNIVERSITIES:
        try:
            df = load_university_data(key)
            frames.append(df)
            print(f"Loaded {key}: {len(df)} posts")
        except FileNotFoundError as e:
            print(f"Skip {key}: {e}")

    if not frames:
        raise RuntimeError("Tidak ada data yang berhasil dimuat.")

    combined = pd.concat(frames, ignore_index=True)
    print(f"\nTotal: {len(combined)} posts dari {len(frames)} universitas")
    return combined

def preprocess_hashtags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "hashtags" not in df.columns:
        raise ValueError("Kolom 'hashtags' tidak ditemukan di DataFrame.")

    df = df[df["hashtags"].apply(lambda x: isinstance(x, list) and len(x) > 0)]

    df["hashtags"] = df["hashtags"].apply(
        lambda tags: list(dict.fromkeys([t.lower().strip() for t in tags]))
    )

    return df.reset_index(drop=True)


def filter_campus_hashtags(
    transactions: list,
    campus_keywords: set = None,
    verbose: bool = True
) -> list:
    """
    Filter hashtag yang mengandung nama kampus spesifik
    supaya association rules yang dihasilkan lebih generik.

    Args:
        transactions: list of list hashtags (sudah lowercase)
        campus_keywords: set of keywords to filter (default dari config)
        verbose: print summary

    Returns:
        filtered_transactions: list of list hashtags tanpa campus keywords
    """
    if campus_keywords is None:
        campus_keywords = CAMPUS_KEYWORDS

    removed = Counter()
    filtered = []

    for transaction in transactions:
        clean = []
        for tag in transaction:
            is_campus = (
                tag not in CAMPUS_KEYWORD_EXCEPTIONS
                and any(kw in tag for kw in campus_keywords)
            )
            if is_campus:
                removed[tag] += 1
            else:
                clean.append(tag)

        if clean:
            filtered.append(clean)

    if verbose:
        print(f"\n── Campus Hashtag Filter ──")
        print(f"  Transactions sebelum : {len(transactions)}")
        print(f"  Transactions sesudah : {len(filtered)}")
        print(f"  Hashtag dihapus      : {sum(removed.values())} unik ({len(removed)} jenis)")
        if removed:
            print(f"  Top 10 yang dihapus  :")
            for tag, count in removed.most_common(10):
                print(f"    #{tag}: {count}x")

    return filtered


def get_transactions(
    df: pd.DataFrame,
    filter_campus: bool = True,
    campus_keywords: set = None
) -> list:
    df = preprocess_hashtags(df)
    transactions = df["hashtags"].tolist()

    if filter_campus:
        transactions = filter_campus_hashtags(
            transactions,
            campus_keywords=campus_keywords
        )

    return transactions


def get_hashtag_frequency(transactions: list, top_n: int = 20) -> pd.DataFrame:
    counter = Counter()
    for t in transactions:
        counter.update(t)

    df = pd.DataFrame(counter.most_common(top_n), columns=["hashtag", "frequency"])
    df["percentage"] = (df["frequency"] / len(transactions) * 100).round(2)
    return df
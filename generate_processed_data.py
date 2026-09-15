"""
generate_processed_data.py
─────────────────────────────────────────────
Script ini dijalankan SEKALI untuk:
1. Load semua data JSON dari dataset/
2. Preprocessing + filter campus hashtags
3. Jalankan Apriori per universitas dan gabungan
4. Simpan hasil ke data/processed/

Jalankan dengan:
    python generate_processed_data.py

Setelah selesai, dashboard tidak perlu jalankan Apriori lagi —
cukup load dari data/processed/.
"""

import json
import pandas as pd
from pathlib import Path
from config import (
    UNIVERSITIES,
    PROCESSED_DATA_DIR,
    RULES_ALL_PATH,
    RULES_PER_UNIV_PATH,
    ENGAGEMENT_SUMMARY_PATH,
    APRIORI_CONFIG,
)
from core.preprocessing import (
    load_university_data,
    load_all_universities,
    get_transactions,
    get_hashtag_frequency,
)
from core.apriori_engine import run_apriori, encode_transactions
from core.engagement import compute_engagement_summary


def setup_directories():
    # cek folder data/processed/
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {PROCESSED_DATA_DIR}")


def generate_rules_per_university(
    min_support: float,
    min_confidence: float,
    min_lift: float,
) -> dict:
    """
    Run Apriori untuk setiap universitas secara individual.

    CATATAN METODOLOGIS — filter_campus=False (berbeda dari analisis gabungan).
    Filter campus hashtag diperlukan pada analisis GABUNGAN agar identitas satu
    institusi tidak mendominasi pola lintas institusi. Pada analisis PER-UNIVERSITAS,
    hashtag identitas justru merupakan bagian sah dari strategi institusi tersebut
    dan menjadi salah satu hal yang membedakannya dari institusi lain, sehingga
    seluruh hashtag disertakan.
    """
    results = {}

    for key, cfg in UNIVERSITIES.items():
        print(f"\n{'─'*50}")
        print(f"Processing: {cfg['name']} ({key})")
        print(f"{'─'*50}")

        try:
            df = load_university_data(key)
            transactions = get_transactions(df, filter_campus=False)

            result = run_apriori(
                transactions,
                min_support=min_support,
                min_confidence=min_confidence,
                min_lift=min_lift,
                label=key.upper(),
            )

            # Tambahkan metadata universitas
            result["university_key"] = key
            result["university_name"] = cfg["name"]
            result["university_short"] = cfg["name_short"]
            result["qs_tier"] = cfg["qs_tier"]
            result["qs_rank"] = cfg["qs_rank"]
            result["color"] = cfg["color"]

            results[key] = result
            print(f"  ✓ {len(result['rules'])} rules generated")

        except FileNotFoundError as e:
            print(f"  ⚠ Skip: {e}")
            results[key] = {
                "university_key": key,
                "university_name": cfg["name"],
                "university_short": cfg["name_short"],
                "qs_tier": cfg["qs_tier"],
                "qs_rank": cfg["qs_rank"],
                "color": cfg["color"],
                "total_transactions": 0,
                "total_unique_hashtags": 0,
                "rules": pd.DataFrame(),
                "frequent_itemsets": pd.DataFrame(),
            }

    return results


def generate_rules_all(
    min_support: float,
    min_confidence: float,
    min_lift: float,
) -> dict:
    """Jalankan Apriori untuk gabungan semua universitas."""
    print(f"\n{'─'*50}")
    print(f"Processing: ALL UNIVERSITIES (gabungan)")
    print(f"{'─'*50}")

    df = load_all_universities()
    transactions = get_transactions(df, filter_campus=True)

    result = run_apriori(
        transactions,
        min_support=min_support,
        min_confidence=min_confidence,
        min_lift=min_lift,
        label="ALL",
    )

    result["university_key"] = "all"
    print(f"{len(result['rules'])} rules generated")

    return result


def generate_engagement_summary() -> pd.DataFrame:
    """Hitung engagement summary untuk semua universitas."""
    print(f"\n{'─'*50}")
    print(f"Processing: Engagement Summary")
    print(f"{'─'*50}")

    df = load_all_universities()
    summary = compute_engagement_summary(df)
    print(f"Engagement summary untuk {len(summary)} universitas")
    return summary


def generate_hashtag_frequency() -> dict:
    """
    Hitung top hashtags per universitas dan gabungan.
    Return dict {university_key: DataFrame}
    """
    print(f"\n{'─'*50}")
    print(f"Processing: Hashtag Frequency")
    print(f"{'─'*50}")

    freq_data = {}

    for key in UNIVERSITIES:
        try:
            df = load_university_data(key)
            # selaras dengan analisis per-universitas: tanpa filter campus hashtag
            transactions = get_transactions(df, filter_campus=False)
            freq_df = get_hashtag_frequency(transactions, top_n=30)
            freq_data[key] = freq_df
            print(f"{key}: {len(freq_df)} top hashtags")
        except FileNotFoundError:
            print(f"Skip {key}: file not found")

    # Gabungan semua
    df_all = load_all_universities()
    transactions_all = get_transactions(df_all, filter_campus=True)
    freq_data["all"] = get_hashtag_frequency(transactions_all, top_n=50)
    print(f"all: {len(freq_data['all'])} top hashtags")

    return freq_data


def save_rules_all(result: dict):
    """Simpan rules gabungan ke CSV."""
    rules = result.get("rules", pd.DataFrame())
    if not rules.empty:
        # Konversi frozenset ke string untuk CSV
        rules_save = rules.copy()
        rules_save["antecedents"] = rules_save["antecedents"].apply(
            lambda x: ", ".join(sorted(x))
        )
        rules_save["consequents"] = rules_save["consequents"].apply(
            lambda x: ", ".join(sorted(x))
        )
        rules_save.to_csv(RULES_ALL_PATH, index=False)
        print(f"Saved: {RULES_ALL_PATH} ({len(rules_save)} rules)")
    else:
        print(f"No rules to save for all universities")


def save_rules_per_university(results: dict):
    """Simpan rules per universitas ke JSON."""
    output = {}

    for key, result in results.items():
        rules = result.get("rules", pd.DataFrame())

        if not rules.empty:
            rules_list = []
            for _, row in rules.iterrows():
                rules_list.append({
                    "antecedents": sorted(list(row["antecedents"])),
                    "consequents": sorted(list(row["consequents"])),
                    "antecedents_str": row.get("antecedents_str", ""),
                    "consequents_str": row.get("consequents_str", ""),
                    "support": float(row["support"]),
                    "confidence": float(row["confidence"]),
                    "lift": float(row["lift"]),
                })
        else:
            rules_list = []

        output[key] = {
            "university_name": result.get("university_name", ""),
            "university_short": result.get("university_short", ""),
            "qs_tier": result.get("qs_tier", 0),
            "qs_rank": result.get("qs_rank", ""),
            "color": result.get("color", ""),
            "total_transactions": result.get("total_transactions", 0),
            "total_unique_hashtags": result.get("total_unique_hashtags", 0),
            "total_rules": len(rules_list),
            "rules": rules_list,
        }

    with open(RULES_PER_UNIV_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  ✓ Saved: {RULES_PER_UNIV_PATH}")


def save_engagement_summary(summary: pd.DataFrame):
    """Simpan engagement summary ke CSV."""
    if not summary.empty:
        summary.to_csv(ENGAGEMENT_SUMMARY_PATH, index=False)
        print(f"Saved: {ENGAGEMENT_SUMMARY_PATH}")
    else:
        print(f"No engagement summary to save")


def save_hashtag_frequency(freq_data: dict):
    """Simpan hashtag frequency per universitas ke JSON."""
    output = {}
    for key, df in freq_data.items():
        output[key] = df.to_dict(orient="records")

    path = PROCESSED_DATA_DIR / "hashtag_frequency.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Saved: {path}")


def save_metadata(
    result_all: dict,
    results_per_univ: dict,
):
    """Simpan metadata ringkasan ke JSON untuk ditampilkan di Overview."""
    meta = {
        "total_posts": result_all.get("total_transactions", 0),
        "total_unique_hashtags": result_all.get("total_unique_hashtags", 0),
        "total_rules_all": len(result_all.get("rules", pd.DataFrame())),
        "avg_lift": 0,
        "max_confidence": 0,
        "min_support_used": APRIORI_CONFIG["min_support"],
        "min_confidence_used": APRIORI_CONFIG["min_confidence"],
        "universities": {},
    }

    # Hitung avg lift dan max confidence dari rules all
    rules_all = result_all.get("rules", pd.DataFrame())
    if not rules_all.empty:
        meta["avg_lift"] = round(float(rules_all["lift"].mean()), 2)
        meta["max_confidence"] = round(float(rules_all["confidence"].max()), 2)

    # Per universitas
    for key, result in results_per_univ.items():
        meta["universities"][key] = {
            "total_posts": result.get("total_transactions", 0),
            "total_rules": len(result.get("rules", pd.DataFrame())),
            "name_short": result.get("university_short", ""),
        }

    path = PROCESSED_DATA_DIR / "metadata.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Saved: {path}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":

    print(f"\n{'='*50}")
    print(f"  HashBI — Generate Processed Data")
    print(f"{'='*50}")

    # Parameter Apriori — bisa diubah sesuai kebutuhan
    MIN_SUPPORT    = APRIORI_CONFIG["min_support"]      # 0.02 (2%)
    MIN_CONFIDENCE = APRIORI_CONFIG["min_confidence"]   # 0.40 (40%)
    MIN_LIFT       = APRIORI_CONFIG["min_lift"]         # 1.0

    print(f"\nParameter Apriori:")
    print(f"  min_support    = {MIN_SUPPORT}")
    print(f"  min_confidence = {MIN_CONFIDENCE}")
    print(f"  min_lift       = {MIN_LIFT}")

    # Setup folder output
    setup_directories()

    # Jalankan pipeline
    print(f"\n{'='*50}")
    print(f"  STEP 1 — Association Rules per Universitas")
    print(f"{'='*50}")
    results_per_univ = generate_rules_per_university(
        MIN_SUPPORT, MIN_CONFIDENCE, MIN_LIFT
    )

    print(f"\n{'='*50}")
    print(f"  STEP 2 — Association Rules Gabungan")
    print(f"{'='*50}")
    result_all = generate_rules_all(
        MIN_SUPPORT, MIN_CONFIDENCE, MIN_LIFT
    )

    print(f"\n{'='*50}")
    print(f"  STEP 3 — Engagement Summary")
    print(f"{'='*50}")
    engagement_summary = generate_engagement_summary()

    print(f"\n{'='*50}")
    print(f"  STEP 4 — Hashtag Frequency")
    print(f"{'='*50}")
    freq_data = generate_hashtag_frequency()

    # Simpan semua output
    print(f"\n{'='*50}")
    print(f"  SAVING OUTPUT")
    print(f"{'='*50}")
    save_rules_all(result_all)
    save_rules_per_university(results_per_univ)
    save_engagement_summary(engagement_summary)
    save_hashtag_frequency(freq_data)
    save_metadata(result_all, results_per_univ)

    print(f"\n{'='*50}")
    print(f"  Output tersimpan di: {PROCESSED_DATA_DIR}")
    print(f"{'='*50}\n")
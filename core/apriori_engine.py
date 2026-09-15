"""
Wrapper untuk apriori algorithm.
"""

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from config import UNIVERSITIES, APRIORI_CONFIG
from core.preprocessing import (
    load_university_data,
    load_all_universities,
    get_transactions
)

def encode_transactions(transactions: list) -> pd.DataFrame:
    """
    Transform list of transactions ke binary DataFrame
    menggunakan TransactionEncoder dari mlxtend.
    """
    te = TransactionEncoder()
    te_array = te.fit(transactions).transform(transactions)
    df_encoded = pd.DataFrame(te_array, columns=te.columns_)

    print(f"\n── Transaction Encoding ──")
    print(f"  Total transactions : {len(df_encoded)}")
    print(f"  Unique hashtags    : {len(df_encoded.columns)}")

    return df_encoded

def run_apriori(
    transactions: list,
    min_support: float = None,
    min_confidence: float = None,
    min_lift: float = None,
    label: str = ""
) -> dict:
    """
    Jalankan Apriori pada list of transactions.

    Returns dict:
        {
            'frequent_itemsets': DataFrame,
            'rules': DataFrame,
            'total_transactions': int,
            'total_unique_hashtags': int,
        }
    """
    min_support = min_support or APRIORI_CONFIG["min_support"]
    min_confidence = min_confidence or APRIORI_CONFIG["min_confidence"]
    min_lift = min_lift or APRIORI_CONFIG["min_lift"]

    if not transactions:
        print(f"⚠ [{label}] Tidak ada transaksi.")
        return _empty_result()

    # Encode
    df_encoded = encode_transactions(transactions)

    # Frequent itemsets
    frequent_itemsets = apriori(
        df_encoded,
        min_support=min_support,
        use_colnames=True
    )
    frequent_itemsets["length"] = frequent_itemsets["itemsets"].apply(len)

    print(f"\n── Apriori Results {f'[{label}]' if label else ''} ──")
    print(f"  Min support    : {min_support}")
    print(f"  Min confidence : {min_confidence}")
    print(f"  Min lift       : {min_lift}")
    print(f"  Frequent itemsets: {len(frequent_itemsets)}")

    # Association rules
    rules = pd.DataFrame()
    itemsets_min2 = frequent_itemsets[frequent_itemsets["length"] >= 2]

    if len(itemsets_min2) > 0:
        rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence
        )

        # Filter by lift
        rules = rules[rules["lift"] >= min_lift]

        # Sort by lift descending
        rules = rules.sort_values("lift", ascending=False).reset_index(drop=True)

        # Format antecedents & consequents ke string untuk kemudahan display
        rules["antecedents_str"] = rules["antecedents"].apply(
            lambda x: ", ".join([f"#{h}" for h in sorted(x)])
        )
        rules["consequents_str"] = rules["consequents"].apply(
            lambda x: ", ".join([f"#{h}" for h in sorted(x)])
        )

        # Round metrics
        rules["support"] = rules["support"].round(4)
        rules["confidence"] = rules["confidence"].round(4)
        rules["lift"] = rules["lift"].round(4)

        print(f"  Association rules: {len(rules)}")
    else:
        print(f"  ⚠ Tidak cukup frequent itemsets untuk generate rules")

    return {
        "frequent_itemsets": frequent_itemsets,
        "rules": rules,
        "total_transactions": len(transactions),
        "total_unique_hashtags": len(df_encoded.columns),
    }


# ─────────────────────────────────────────────
# PER UNIVERSITY
# ─────────────────────────────────────────────

def run_apriori_per_university(
    university_key: str,
    min_support: float = None,
    min_confidence: float = None,
    min_lift: float = None,
) -> dict:
    """
    Jalankan Apriori untuk satu universitas spesifik.
    """
    df = load_university_data(university_key)
    transactions = get_transactions(df, filter_campus=True)

    result = run_apriori(
        transactions,
        min_support=min_support,
        min_confidence=min_confidence,
        min_lift=min_lift,
        label=university_key.upper()
    )
    result["university_key"] = university_key
    return result


# ─────────────────────────────────────────────
# ALL UNIVERSITIES
# ─────────────────────────────────────────────

def run_apriori_all(
    min_support: float = None,
    min_confidence: float = None,
    min_lift: float = None,
) -> dict:
    """
    Jalankan Apriori untuk gabungan semua universitas.
    """
    df = load_all_universities()
    transactions = get_transactions(df, filter_campus=True)

    result = run_apriori(
        transactions,
        min_support=min_support,
        min_confidence=min_confidence,
        min_lift=min_lift,
        label="ALL UNIVERSITIES"
    )
    result["university_key"] = "all"
    return result


# ─────────────────────────────────────────────
# BATCH — semua universitas sekaligus
# ─────────────────────────────────────────────

def run_apriori_batch(
    min_support: float = None,
    min_confidence: float = None,
    min_lift: float = None,
) -> dict:
    """
    Jalankan Apriori untuk semua universitas secara individual
    sekaligus untuk gabungan semua universitas.

    Returns:
        {
            'all': result_all,
            'binus': result_binus,
            'telkom': result_telkom,
            ...
        }
    """
    results = {}

    # Per universitas
    for key in UNIVERSITIES:
        print(f"\n{'='*50}")
        print(f"Processing: {UNIVERSITIES[key]['name']}")
        print(f"{'='*50}")
        try:
            results[key] = run_apriori_per_university(
                key,
                min_support=min_support,
                min_confidence=min_confidence,
                min_lift=min_lift,
            )
        except FileNotFoundError as e:
            print(f"⚠ Skip {key}: {e}")
            results[key] = _empty_result()
            results[key]["university_key"] = key

    # Gabungan semua
    print(f"\n{'='*50}")
    print(f"Processing: ALL UNIVERSITIES")
    print(f"{'='*50}")
    results["all"] = run_apriori_all(
        min_support=min_support,
        min_confidence=min_confidence,
        min_lift=min_lift,
    )

    return results


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _empty_result() -> dict:
    return {
        "frequent_itemsets": pd.DataFrame(),
        "rules": pd.DataFrame(),
        "total_transactions": 0,
        "total_unique_hashtags": 0,
    }


def get_top_rules(rules: pd.DataFrame, top_n: int = None, sort_by: str = "lift") -> pd.DataFrame:
    """Return top N rules sorted by metric tertentu."""
    top_n = top_n or APRIORI_CONFIG["top_n_rules"]
    if rules.empty:
        return rules
    return rules.sort_values(sort_by, ascending=False).head(top_n)


def rules_to_display(rules: pd.DataFrame) -> pd.DataFrame:
    """
    Format rules DataFrame untuk ditampilkan di Streamlit tabel.
    Hanya ambil kolom yang relevan dan rename untuk keterbacaan.
    """
    if rules.empty:
        return pd.DataFrame()

    display_cols = {
        "antecedents_str": "Antecedent (X)",
        "consequents_str": "Consequent (Y)",
        "support": "Support",
        "confidence": "Confidence",
        "lift": "Lift",
    }

    available = {k: v for k, v in display_cols.items() if k in rules.columns}
    return rules[list(available.keys())].rename(columns=available)
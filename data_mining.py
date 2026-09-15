"""
data_mining.py — SKRIP EKSPLORASI AWAL (LEGACY, TIDAK DIPAKAI SISTEM)

Skrip ini adalah prototipe tahap eksplorasi yang dijalankan pada dataset awal
(11 universitas di folder scraped_data/) dan menghasilkan gambar di visualizations/.

PERHATIAN — parameter di skrip ini BUKAN parameter penelitian:
    skrip ini    : min_support 0.03-0.05, min_confidence 0.3
    penelitian   : min_support 0.02, min_confidence 0.40, min_lift 1.0
                   (lihat APRIORI_CONFIG di config.py)

Pipeline resmi penelitian ada di generate_processed_data.py yang membaca
parameter dari config.py. Parameter di sini sengaja tidak diubah agar gambar
yang sudah terlanjur dihasilkan di visualizations/ tetap dapat direproduksi.
"""

import json
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
import networkx as nx
import matplotlib.pyplot as plt
from collections import Counter
import seaborn as sns
import textwrap

# load json data
def load_data(filepath):
    """Load data from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


# get hashtag data
def get_hashtag_data(data):
    df = pd.DataFrame(data)
    
    # get only hashtag column
    hashtag_df = df[['hashtags']].copy()
    
    hashtag_df = hashtag_df[hashtag_df['hashtags'].apply(lambda x: len(x) > 0 if x else False)]
    
    print(f"Total posts: {len(df)}")
    print(f"Posts with hashtags: {len(hashtag_df)}")
    
    return hashtag_df

# preprocessing
def preprocessing_hashtag(hashtag_df):
    
    hashtag_df['hashtags'] = hashtag_df['hashtags'].apply(lambda x: [tag.lower() for tag in x] if x else [])
    
    # convert to transaction format
    transactions = hashtag_df['hashtags'].tolist()
    
    print(f'processing step')
    print(f'total transactions: {len(transactions)}')
    print(f'sample transaction: {transactions[0][:5] if transactions else None}')
    
    return transactions

def get_campus_keywords():
    return {
        'itenas', 'telkom', 'uii', 'pcu', 'atmajaya',
        'uph', 'sampoerna', 'parahyangan', 'trisakti', 'tarumanegara', 'petra',
        'untar', 'untarian', 'kampusull', 'ullyogyakarta', 'unparian',
        'lifeatunpar', 'unpar'
    }
    
def is_campus_hashtag(hashtag, campus_keywords):
    hashtag_lower = hashtag.lower()
    for keyword in campus_keywords:
        if keyword in hashtag_lower:
            return True
    return False

def filter_campus_hashtags(transactions, campus_keywords):
    
    total_hashtags_before = sum(len(t) for t in transactions)
    removed_hashtags = Counter()
    
    filtered_transactions = []
    for transaction in transactions:
        filtered = []
        for hashtag in transaction:
            if is_campus_hashtag(hashtag, campus_keywords):
                removed_hashtags[hashtag] += 1
            else:
                filtered.append(hashtag)
        
        if len(filtered) > 0:
            filtered_transactions.append(filtered)
    
    total_hashtags_after = sum(len(t) for t in filtered_transactions)
    
    print(f"\nFiltering Results:")
    print(f"  Transactions before: {len(transactions)}")
    print(f"  Transactions after: {len(filtered_transactions)}")
    print(f"  Total hashtags before: {total_hashtags_before}")
    print(f"  Total hashtags after: {total_hashtags_after}")
    print(f"  Hashtags removed: {total_hashtags_before - total_hashtags_after}")
    
    if removed_hashtags:
        print(f"\n  Top 10 Campus Hashtags Removed:")
        for i, (tag, count) in enumerate(removed_hashtags.most_common(10), 1):
            print(f"    {i:2d}. #{tag}: {count} times")
    
    return filtered_transactions


def apriori_analysis_universal(filepaths_dict, min_support=0.03, min_confidence=0.3):
    
    # Get campus keywords to filter
    campus_keywords = get_campus_keywords()
    print(f"\nCampus keywords to filter: {len(campus_keywords)}")
    
    # Combine all transactions
    all_transactions = []
    
    for institution_name, filepath in filepaths_dict.items():
        print(f"\nLoading {institution_name}...")
        
        data = load_data(filepath)
        hashtag_df = get_hashtag_data(data)
        transactions = preprocessing_hashtag(hashtag_df)
        all_transactions.extend(transactions)
        
        print(f"Loaded {len(transactions)} transactions")
    
    # Filter campus-specific hashtags
    filtered_transactions = filter_campus_hashtags(all_transactions, campus_keywords)
    
    # Transform for apriori
    df_encoded = transform_for_apriori(filtered_transactions)
    
    # Apply Apriori
    print(f"\n{'='*70}")
    print(f"Applying Universal Apriori Algorithm...")
    print(f"  Min Support: {min_support} ({min_support*100}%)")
    print(f"  Min Confidence: {min_confidence} ({min_confidence*100}%)")
    
    frequent_itemsets = apriori(df_encoded, min_support=min_support, use_colnames=True)
    frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(lambda x: len(x))
    
    print(f"\Found {len(frequent_itemsets)} frequent itemsets")
    
    # Display by size
    print(f"\nUniversal Frequent Itemsets by Size:")
    for length in sorted(frequent_itemsets['length'].unique()):
        count = len(frequent_itemsets[frequent_itemsets['length'] == length])
        print(f"  Size {length}: {count} itemsets")
    
    # Top 20 itemsets
    print(f"\n{'='*70}")
    print(f"TOP 20 UNIVERSAL FREQUENT ITEMSETS")
    print(f"{'='*70}")
    
    top_itemsets = frequent_itemsets.nlargest(20, 'support')
    for i, (idx, row) in enumerate(top_itemsets.iterrows(), 1):
        itemset_str = ', '.join([f"#{tag}" for tag in sorted(row['itemsets'])])
        print(f"{i:2d}. Support: {row['support']:.3f} | {itemset_str}")
    
    # Generate association rules
    if len(frequent_itemsets[frequent_itemsets['length'] >= 2]) > 0:
        print(f"\n{'='*70}")
        print(f"Generating Universal Association Rules...")
        
        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
        rules = rules.sort_values('lift', ascending=False)
        
        print(f"Found {len(rules)} universal association rules")
        
        # Display top rules
        print(f"\n{'='*70}")
        print(f"TOP 20 UNIVERSAL ASSOCIATION RULES")
        print(f"{'='*70}")
        print(f"{'No':<5} {'Antecedent':<30} {'Consequent':<30} {'Supp':<8} {'Conf':<8} {'Lift'}")
        print(f"{'-'*95}")
        
        for i, (idx, row) in enumerate(rules.head(20).iterrows(), 1):
            ant = ', '.join([f"#{tag}" for tag in sorted(row['antecedents'])])
            cons = ', '.join([f"#{tag}" for tag in sorted(row['consequents'])])
            print(f"{i:<5} {ant:<30} {cons:<30} {row['support']:<8.3f} {row['confidence']:<8.3f} {row['lift']:.3f}")
        
        return {
            'total_institutions': len(filepaths_dict),
            'total_transactions': len(filtered_transactions),
            'frequent_itemsets': frequent_itemsets,
            'association_rules': rules
        }
    else:
        print("\n⚠ Not enough frequent itemsets to generate rules")
        return {
            'total_institutions': len(filepaths_dict),
            'total_transactions': len(filtered_transactions),
            'frequent_itemsets': frequent_itemsets,
            'association_rules': pd.DataFrame()
        }
    

# modelling
def transform_for_apriori(transactions):
    te = TransactionEncoder()
    te_array = te.fit(transactions).transform(transactions)
    df_encoded = pd.DataFrame(te_array, columns=te.columns_)
    
    print(f"\nData transformation:")
    print(f"Unique hashtags: {len(df_encoded.columns)}")
    print(f"Transaction matrix shape: {df_encoded.shape}")
    
    return df_encoded

# show top frequent hashtags
def plot_top_hashtags(df_encoded, top_n=10, save_path='./visualizations/top_frequent_hashtag.png'):
    # calc frequency
    hashtag_frequency = df_encoded.sum().sort_values(ascending=False)
    top_hashtags = hashtag_frequency.head(top_n)
    
    # visualize
    plt.figure(figsize=(12, 8))
    sns.set_style('whitegrid')
    
    plot = sns.barplot(
        x=top_hashtags.values, 
        y=top_hashtags.index, 
        palette='magma'
    )
    
    plt.title(f'Top {top_n} Most Frequent Hashtags (All Data Institutions)', fontsize=16, fontweight='bold')
    plt.xlabel('Total Frequency', fontsize=12)
    plt.ylabel('Hashtags', fontsize=12)
    
    for i, v in enumerate(top_hashtags.values):
        plot.text(v + 3, i, str(int(v)), color='black', va='center', fontweight='bold')

    plt.tight_layout()
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n[INFO] Plot frekuensi hashtag berhasil disimpan di: {save_path}")
    plt.close()

# analysis for specific university
def apriori_analysis_specific_university(filepath, institution_name, min_support=0.05, min_confidence=0.3):
    """
    Menjalankan analisis Apriori untuk satu universitas spesifik
    dengan output tabel yang rapi dan mendukung text wrapping.
    """
    # 1. Load dan Preprocessing
    data = load_data(filepath)
    hashtag_df = get_hashtag_data(data)
    transactions = preprocessing_hashtag(hashtag_df)
    df_encoded = transform_for_apriori(transactions)
    
    # 2. save plot
    try:
        plot_top_hashtags(df_encoded=df_encoded, top_n=15, 
                          save_path=f'./visualizations/top_frequent_{institution_name}.png')
    except NameError:
        pass

    # 3. Apriori Algorithm
    frequent_itemsets = apriori(df_encoded, min_support=min_support, use_colnames=True)
    frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(lambda x: len(x))
    
    # 4. Generate Association Rules
    if len(frequent_itemsets[frequent_itemsets['length'] >= 2]) > 0:
        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
        rules = rules.sort_values('lift', ascending=False)
        
        # --- PRINT TABLE ---
        print(f"\n{'='*115}")
        print(f"TABLE: ASSOCIATION RULES (WRAPPED) - {institution_name.upper()}")
        print(f"{'='*115}")
        
        # Header Tabel
        header = f"{'No':<4} {'Antecedents (X)':<40} {'Consequents (Y)':<40} {'Supp':<8} {'Conf':<8} {'Lift':<8}"
        print(header)
        print(f"{'-'*115}")
        
        for i, (idx, row) in enumerate(rules.head(15).iterrows(), 1):

            ant_str = ', '.join([f"#{tag}" for tag in row['antecedents']])
            cons_str = ', '.join([f"#{tag}" for tag in row['consequents']])
            
            ant_wrapped = textwrap.wrap(ant_str, width=38)
            cons_wrapped = textwrap.wrap(cons_str, width=38)
            
            max_lines = max(len(ant_wrapped), len(cons_wrapped))
            
            for line_idx in range(max_lines):
                a_line = ant_wrapped[line_idx] if line_idx < len(ant_wrapped) else ""
                c_line = cons_wrapped[line_idx] if line_idx < len(cons_wrapped) else ""
                
                if line_idx == 0:
                
                    print(f"{i:<4} {a_line:<40} {c_line:<40} {row['support']:<8.3f} {row['confidence']:<8.3f} {row['lift']:<8.3f}")
                else:
                  
                    print(f"{' ':<4} {a_line:<40} {c_line:<40}")
            
            print(f"{'-'*115}")
        
        return {
            'institution': institution_name,
            'frequent_itemsets': frequent_itemsets,
            'association_rules': rules,
            'total_transactions': len(transactions)
        }
    else:
        print(f"\n[!] Not enough frequent itemsets to generate rules for {institution_name}")
        return {
            'institution': institution_name,
            'frequent_itemsets': frequent_itemsets,
            'association_rules': pd.DataFrame(),
            'total_transactions': len(transactions)
        }    

# networkx visualization
def visualization_networkx_university_assoc_rules(rules, institution_name, top_n=10, save_path='assoc_rules_network.png'):
    
    if len(rules) == 0:
        print("No association rules to visualize.")
        return

    # select top rules by lift
    top_rules = rules.nlargest(top_n, 'lift')
    
    # create network graph
    G = nx.DiGraph()
    
    for idx, row in top_rules.iterrows():
        ant = ', '.join(row['antecedents'])
        cons = ', '.join(row['consequents'])
        
        G.add_node(ant, node_type='antecedent')
        G.add_node(cons, node_type='consequent')
        G.add_edge(ant, cons, weight=row['lift'], confidence=row['confidence'])
    
    # draw the network
    plt.figure(figsize=(14, 10))
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    # draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=2000, alpha=0.8)
    
    # draw edges
    edges = G.edges()
    weights = [G[u][v]['weight'] for u, v in edges]
    nx.draw_networkx_edges(G, pos, width=[w*0.5 for w in weights], 
                          alpha=0.6, edge_color='gray', 
                          arrows=True, arrowsize=20)
    
    # draw labels
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
    
    plt.title(f'Top {top_n} Association Rules Network of {institution_name}', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n Network visualization saved to: {save_path}")
    plt.close()
    
def plot_rules_scatter(rules, save_path='./visualizations/universal_rules_scatter.png'):
    if rules.empty:
        print("No association rules to plot.")
        return

    plt.figure(figsize=(10, 7))
    
    scatter = plt.scatter(
        rules['support'], 
        rules['confidence'],
        c=rules['lift'], 
        cmap='viridis', 
        alpha=0.7,
        edgecolors='w',
        linewidth=0.5
    )
    
    plt.colorbar(scatter, label='Lift Ratio')
    
    plt.xlabel('Support', fontsize=12)
    plt.ylabel('Confidence', fontsize=12)
    plt.title('Universal Association Rules Analysis', fontsize=15, fontweight='bold')
    
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    


if __name__ == "__main__":
    
    # itenas university
    result_itenas = apriori_analysis_specific_university(
        filepath='./scraped_data/itenas.official_posts.json',
        institution_name='itenas',
    )
    
    # telkom university
    result_telkom = apriori_analysis_specific_university(
        filepath='./scraped_data/telkomuniversity_posts.json',
        institution_name='telkomuniversity',
    )
    
    # uii yogyakarta university
    result_uii = apriori_analysis_specific_university(
        filepath='./scraped_data/uiiyogyakarta_posts.json',
        institution_name='uiiyogyakarta',
    )
    
    # pcu university
    result_lifeatpcu = apriori_analysis_specific_university(
        filepath='./scraped_data/lifeatpcu_posts.json',
        institution_name='lifeatpcu',
    )
    
    # atmajaya university
    result_atmajaya = apriori_analysis_specific_university(
        filepath='./scraped_data/unikaatmajaya_posts.json',
        institution_name='unikaatmajaya',
    )
    
    # uph university
    result_uphimpactslives = apriori_analysis_specific_university(
        filepath='./scraped_data/uphimpactslives_posts.json',
        institution_name='uphimpactslives',
    )
    
    # sampoerna university
    result_sampoerna_university = apriori_analysis_specific_university(
        filepath='./scraped_data/sampoerna.university_posts.json',
        institution_name='sampoerna university'
    )
    
    # parahyangan university
    result_parahyangan_university = apriori_analysis_specific_university(
        filepath='./scraped_data/unparofficial_posts.json',
        institution_name='parahyangan university'
    )
    
    # trisakti university
    result_trisakti_university = apriori_analysis_specific_university(
        filepath='./scraped_data/usakti_official_posts.json',
        institution_name='trisakti university'
    )
    
    # tarumanegara university
    result_tarumanegara_university = apriori_analysis_specific_university(
        filepath='./scraped_data/untarjakarta_posts.json',
        institution_name='tarumanegara university'
    )
    
    # ==================================
    # Visualization
    # ==================================
    
    if not result_telkom['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_telkom['association_rules'],
            institution_name='telkomuniversity',
            top_n=10,
            save_path='./visualizations/telkom_assoc_rules_network.png'
        )
        
    if not result_itenas['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_itenas['association_rules'],
            institution_name='itenas',
            top_n=10,
            save_path='./visualizations/itenas_assoc_rules_network.png'
        )
        
    if not result_uii['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_uii['association_rules'],
            institution_name='uiiyogyakarta',
            top_n=10,
            save_path='./visualizations/uii_assoc_rules_network.png'
        )
    
    if not result_lifeatpcu['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_lifeatpcu['association_rules'],
            institution_name='petra university',
            top_n=10,
            save_path='./visualizations/pcu_assoc_rules_network.png'
        )
    
    if not result_atmajaya['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_atmajaya['association_rules'],
            institution_name='atmajaya university',
            top_n=10,
            save_path='./visualizations/atmajaya_assoc_rules_network.png'
        )
    
    if not result_uphimpactslives['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_uphimpactslives['association_rules'],
            institution_name='uph university',
            top_n=10,
            save_path='./visualizations/uph_assoc_rules_network.png'
        )
    
    if not result_sampoerna_university['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_sampoerna_university['association_rules'],
            institution_name='sampoerna university',
            top_n=10,
            save_path='./visualizations/sampoerna_assoc_rules_network.png'
        )
    
    if not result_parahyangan_university['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_parahyangan_university['association_rules'],
            institution_name='parahyangan university',
            top_n=10,
            save_path='./visualizations/parahyangan_assoc_rules_network.png'
        )
    
    if not result_trisakti_university['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_trisakti_university['association_rules'],
            institution_name='trisakti university',
            top_n=10,
            save_path='./visualizations/trisakti_assoc_rules_network.png'
        )
        
    if not result_tarumanegara_university['association_rules'].empty:
        visualization_networkx_university_assoc_rules(
            result_tarumanegara_university['association_rules'],
            institution_name='tarumanegara university',
            top_n=10,
            save_path='./visualizations/tarumanegara_assoc_rules_network.png'
        )
        
    file_path_dict = {
        'itenas': './scraped_data/itenas.official_posts.json',
        'petra university': './scraped_data/lifeatpcu_posts.json',
        'sampoerna university': './scraped_data/sampoerna.university_posts.json',
        'telkomuniversity': './scraped_data/telkomuniversity_posts.json',
        'uiiyogyakarta': './scraped_data/uiiyogyakarta_posts.json',
        'unikaatmajaya': './scraped_data/unikaatmajaya_posts.json',
        'parahyangan university': './scraped_data/unparofficial_posts.json',
        'tarumanegara university': './scraped_data/untarjakarta_posts.json',
        'uph university': './scraped_data/uphimpactslives_posts.json',
        'trisakti university': './scraped_data/usakti_official_posts.json'
    }
    
    print(f'\n{"="*40}')
    universal_result = apriori_analysis_universal(
        filepaths_dict=file_path_dict,
        min_support=0.03,
        min_confidence=0.3
    )
    
    plot_rules_scatter(rules=universal_result['association_rules'], save_path='./visualizations/universal_rules_scatter.png')
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.anova import anova_lm

# --- 1. 配置 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './nodal_statistical_results/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

GROUPS = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']

# --- 2. 数据加载 ---
def load_nodal_data():
    print(">>> 正在提取所有受试者的 Nodal Strength 数据...")
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    
    nodal_strengths = []
    metadata = []

    for idx, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'], f"{row['Original_SUB_ID']}_MIND.csv")
        if os.path.exists(f_path):
            mat = pd.read_csv(f_path, index_col=0).values
            # Nodal Strength = 矩阵每一行的和
            nodal_strengths.append(mat.sum(axis=1))
            metadata.append(row)
            
    return np.array(nodal_strengths), pd.DataFrame(metadata)

# --- 3. 执行分析 ---
def run_nodal_analysis():
    strengths, meta = load_nodal_data()
    meta['Group_MIND'] = pd.Categorical(meta['Group_MIND'], categories=GROUPS, ordered=True)
    num_nodes = strengths.shape[1] # 应为 68

    print(f">>> 开始对 {num_nodes} 个节点进行 ANCOVA 分析 (协变量: Age, Sex, Edu)...")
    
    # --- [A] 四组间整体 ANOVA ---
    anova_results = []
    for i in range(num_nodes):
        meta['node_val'] = strengths[:, i]
        model = ols('node_val ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=meta).fit()
        table = anova_lm(model, typ=2)
        anova_results.append({
            'ROI_Index': i + 1,
            'F_stat': table.loc['Group_MIND', 'F'],
            'P_raw': table.loc['Group_MIND', 'PR(>F)']
        })
    
    nodal_anova_df = pd.DataFrame(anova_results)
    _, nodal_anova_df['P_FDR'], _, _ = multipletests(nodal_anova_df['P_raw'], method='fdr_bh')
    nodal_anova_df.to_csv(os.path.join(OUTPUT_DIR, "Nodal_ANOVA_Results.csv"), index=False)

    # --- [B] 两两组间比较与 T-map ---
    all_pairs_t = {}
    for g1, g2 in combinations(GROUPS, 2):
        print(f"    对比: {g1} vs {g2}")
        pair_mask = meta['Group_MIND'].isin([g1, g2])
        pair_meta = meta[pair_mask].copy()
        pair_meta['Group_MIND'] = pd.Categorical(pair_meta['Group_MIND'], categories=[g1, g2])
        pair_strengths = strengths[pair_mask.values]
        
        pair_results = []
        for i in range(num_nodes):
            pair_meta['node_val'] = pair_strengths[:, i]
            model = ols('node_val ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=pair_meta).fit()
            pair_results.append({
                'ROI': i + 1,
                'T_stat': model.tvalues.iloc[1],
                'P_raw': model.pvalues.iloc[1]
            })
        
        pair_df = pd.DataFrame(pair_results)
        _, pair_df['P_FDR'], _, _ = multipletests(pair_df['P_raw'], method='fdr_bh')
        pair_df.to_csv(os.path.join(OUTPUT_DIR, f"Nodal_Pairwise_{g1}_vs_{g2}.csv"), index=False)
        all_pairs_t[f"{g1}_vs_{g2}"] = pair_df['T_stat'].values

    # --- [C] 可视化：T值热力图 (汇总所有对比) ---
    t_summary_df = pd.DataFrame(all_pairs_t)
    plt.figure(figsize=(12, 10))
    sns.heatmap(t_summary_df, cmap='RdBu_r', center=0, annot=False)
    plt.title("Nodal Strength T-statistics across all Pairwise Comparisons")
    plt.ylabel("ROI Index (1-68)")
    plt.savefig(os.path.join(OUTPUT_DIR, "Nodal_T_Summary_Heatmap.png"), dpi=300)

    # --- [D] 显著节点展示 ---
    # 找出 ANOVA 中最显著的前 10 个节点
    top_nodes = nodal_anova_df.nsmallest(10, 'P_raw')
    plt.figure(figsize=(10, 6))
    sns.barplot(x='F_stat', y='ROI_Index', data=top_nodes, orient='h', palette='magma')
    plt.title("Top 10 Most Differing Nodes (ANOVA F-statistic)")
    plt.savefig(os.path.join(OUTPUT_DIR, "Top_Significant_Nodes_Bar.png"))

    print(f"\n>>> 分析完成！Nodal 结果保存在: {OUTPUT_DIR}")
    plt.show()

if __name__ == "__main__":
    run_nodal_analysis()
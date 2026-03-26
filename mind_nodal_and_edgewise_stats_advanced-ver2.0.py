import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from scipy import stats
from config import *

apply_style()

# --- 1. 环境配置 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './statistical_results_advanced/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 2. 数据加载函数 ---
def load_comprehensive_data():
    print(">>> 正在加载矩阵并构建网络指标...")
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    
    mats, strengths, meta = [], [], []

    for idx, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'], f"{row['Original_SUB_ID']}_MIND.csv")
        if os.path.exists(f_path):
            mat = pd.read_csv(f_path, index_col=0).values
            mats.append(mat)
            strengths.append(mat.sum(axis=1)) # Nodal Strength
            meta.append(row)
            
    return np.array(mats), np.array(strengths), pd.DataFrame(meta)

# --- 3. 统计与分析 ---
def run_advanced_analysis():
    mats, strengths, meta = load_comprehensive_data()
    meta['Group_MIND'] = pd.Categorical(meta['Group_MIND'], categories=GROUP_ORDER, ordered=True)
    
    # 计算 Global Mean MIND
    global_mean = mats.mean(axis=(1, 2))
    meta['Global_MIND'] = global_mean

    # --- [A] 连边分布箱线图 (四组对比) ---
    print(">>> [1/4] 生成全局连接强度分布箱线图...")
    plt.figure(figsize=FIG_SINGLE)
    sns.violinplot(x='Group_MIND', y='Global_MIND', data=meta, palette=PALETTE_VIOLIN, inner="quart")
    sns.stripplot(x='Group_MIND', y='Global_MIND', data=meta, color=STRIP_COLOR, alpha=ALPHA_STRIP)
    plt.title("Edge-wise Global Mean MIND Distribution across 4 Groups")
    plt.savefig(os.path.join(OUTPUT_DIR, "Global_Edge_Boxplot.png"), dpi=DPI)

    # 计算 HC 组的基线 Nodal Strength (用于 Hub Vulnerability)
    hc_mask = (meta['Group_MIND'] == 'HC')
    hc_nodal_baseline = strengths[hc_mask].mean(axis=0)

    # --- [B] 两两组间深度统计 ---
    for g1, g2 in combinations(GROUP_ORDER, 2):
        print(f"\n>>> 深入对比: {g1} vs {g2}")
        mask = meta['Group_MIND'].isin([g1, g2])
        curr_meta = meta[mask].copy()
        curr_meta['Group_MIND'] = pd.Categorical(curr_meta['Group_MIND'], categories=[g1, g2])
        
        # 1. Nodal Strength ANCOVA
        nodal_results = []
        pair_strengths = strengths[mask.values]
        for i in range(68):
            curr_meta['y_node'] = pair_strengths[:, i]
            model = ols('y_node ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=curr_meta).fit()
            nodal_results.append({
                'ROI': i + 1,
                'T': model.tvalues.iloc[1],
                'P': model.pvalues.iloc[1]
            })
        
        nodal_df = pd.DataFrame(nodal_results)
        _, nodal_df['P_FDR'], _, _ = multipletests(nodal_df['P'], method='fdr_bh')
        nodal_df.to_csv(os.path.join(OUTPUT_DIR, f"Nodal_Stats_{g1}_vs_{g2}.csv"), index=False)

        # 2. Hub Vulnerability Pattern (节点 T值与 HC基线强度的相关性)
        # 解释：如果相关性为负，说明越是核心的 Hub，受损越严重
        r_val, p_val = stats.pearsonr(hc_nodal_baseline, nodal_df['T'])
        print(f"    Hub Vulnerability Correlation (r): {r_val:.3f}, p: {p_val:.3f}")

        # 3. Edge-wise T-matrix (NBS 基础)
        print("    正在计算 Edge-wise T-matrix...")
        edge_t_mat = np.zeros((68, 68))
        pair_mats = mats[mask.values]
        
        # 为了速度，这里演示核心逻辑：对每条边进行简化的组间 T 检验
        # 在实际 NBS 中，这步会配合置换检验
        g1_mats = pair_mats[curr_meta['Group_MIND'] == g1]
        g2_mats = pair_mats[curr_meta['Group_MIND'] == g2]
        
        t_img, p_img = stats.ttest_ind(g1_mats, g2_mats, axis=0)
        
        plt.figure(figsize=FIG_HEATMAP_SQ)
        sns.heatmap(t_img, cmap=CMAP_DIVERGING, center=0, xticklabels=10, yticklabels=10)
        plt.title(f"Edge-wise T-statistic Matrix: {g1} vs {g2}")
        plt.savefig(os.path.join(OUTPUT_DIR, f"Edge_Tmap_{g1}_vs_{g2}.png"), dpi=DPI)

    print(f"\n>>> 深度统计分析完成！结果保存在: {OUTPUT_DIR}")
    plt.show()

if __name__ == "__main__":
    run_advanced_analysis()
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.anova import anova_lm
from config import *

apply_style()

# --- 1. 配置 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './edge_statistical_results/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 2. 高效数据加载 ---
def load_edge_data():
    print(">>> 正在提取所有受试者的连边数据...")
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    
    edge_list = [] # 存储摊平的三角矩阵
    metadata = []
    
    # 提取上三角索引 (k=1 不含对角线)
    iu = np.triu_indices(68, k=1)

    for idx, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'], f"{row['Original_SUB_ID']}_MIND.csv")
        if os.path.exists(f_path):
            mat = pd.read_csv(f_path, index_col=0).values
            edge_list.append(mat[iu]) # 只取上三角，减少计算量
            metadata.append(row)
            
    return np.array(edge_list), pd.DataFrame(metadata), iu

# --- 3. 执行分析 ---
def run_edge_analysis():
    edges, meta, iu_idx = load_edge_data()
    meta['Group_MIND'] = pd.Categorical(meta['Group_MIND'], categories=GROUP_ORDER, ordered=True)
    num_edges = edges.shape[1]

    print(f">>> 开始对 {num_edges} 条连边进行 ANCOVA 分析 (协变量: Age, Sex, Edu)...")
    
    # --- [A] 四组间整体 ANOVA ---
    anova_p = []
    for e in range(num_edges):
        meta['edge_val'] = edges[:, e]
        # 构建模型
        model = ols('edge_val ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=meta).fit()
        # 获取 Group_MIND 的显著性 (Type II ANOVA)
        table = anova_lm(model, typ=2)
        anova_p.append(table.loc['Group_MIND', 'PR(>F)'])
    
    # FDR 校正
    _, anova_fdr, _, _ = multipletests(anova_p, method='fdr_bh')
    
    # 保存 ANOVA 结果矩阵
    anova_res_mat = np.zeros((68, 68))
    anova_res_mat[iu_idx] = anova_fdr
    anova_res_mat = anova_res_mat + anova_res_mat.T # 补全对称矩阵
    
    plt.figure(figsize=FIG_HEATMAP_SM)
    sns.heatmap(anova_res_mat, cmap=CMAP_PVAL, vmax=0.05)
    plt.title("Edge-wise ANCOVA FDR-corrected P-map (Across 4 Groups)")
    plt.savefig(os.path.join(OUTPUT_DIR, "Edge_ANCOVA_FDR_Map.png"))

    # --- [B] 两两组间 Post-hoc 比较 ---
    print(">>> 正在执行两两组间比较...")
    for g1, g2 in combinations(GROUP_ORDER, 2):
        print(f"    对比: {g1} vs {g2}")
        pair_mask = meta['Group_MIND'].isin([g1, g2])
        pair_meta = meta[pair_mask].copy()
        pair_meta['Group_MIND'] = pd.Categorical(pair_meta['Group_MIND'], categories=[g1, g2])
        pair_edges = edges[pair_mask.values]
        
        pair_t, pair_p = [], []
        for e in range(num_edges):
            pair_meta['edge_val'] = pair_edges[:, e]
            model = ols('edge_val ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=pair_meta).fit()
            pair_t.append(model.tvalues.iloc[1]) # Group 的 T 值
            pair_p.append(model.pvalues.iloc[1])
            
        _, p_fdr, _, _ = multipletests(pair_p, method='fdr_bh')
        
        # 保存 T 值矩阵图
        t_mat = np.zeros((68, 68))
        t_mat[iu_idx] = pair_t
        t_mat = t_mat + t_mat.T
        
        plt.figure(figsize=FIG_HEATMAP_SM)
        sns.heatmap(t_mat, cmap=CMAP_DIVERGING, center=0)
        plt.title(f"Edge-wise T-stat: {g1} vs {g2} (Covariates Adjusted)")
        plt.savefig(os.path.join(OUTPUT_DIR, f"Edge_T_Map_{g1}_vs_{g2}.png"))

    # --- [C] 显著连边的箱线图示例 ---
    # 选取 ANOVA 最显著的一条边展示四组分布
    best_edge_idx = np.argmin(anova_p)
    meta['best_edge'] = edges[:, best_edge_idx]
    plt.figure(figsize=FIG_SINGLE)
    sns.boxplot(x='Group_MIND', y='best_edge', data=meta, palette=GROUP_PALETTE)
    sns.swarmplot(x='Group_MIND', y='best_edge', data=meta, color=STRIP_COLOR, size=STRIP_SIZE)
    plt.title(f"Distribution of Most Significant Edge (ROI Index: {iu_idx[0][best_edge_idx]}-{iu_idx[1][best_edge_idx]})")
    plt.savefig(os.path.join(OUTPUT_DIR, "Top_Significant_Edge_Boxplot.png"))

    print(f"\n>>> 分析完成！所有矩阵图和统计表已存至: {OUTPUT_DIR}")
    plt.show()

if __name__ == "__main__":
    run_edge_analysis()
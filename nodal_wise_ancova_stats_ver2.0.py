import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.anova import anova_lm
from nilearn import plotting, datasets
from config import *

apply_style()

# --- 1. 配置 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './nodal_statistical_results/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 2. 3D 渲染辅助函数 ---
def plot_nodal_surface(t_values, title):
    fsaverage = datasets.fetch_surf_fsaverage()
    destrieux = datasets.fetch_atlas_surf_destrieux()
    left_map = np.zeros(destrieux['map_left'].shape)
    right_map = np.zeros(destrieux['map_right'].shape)
    
    for i in range(34):
        left_map[destrieux['map_left'] == i+1] = t_values[i]
        right_map[destrieux['map_right'] == i+1] = t_values[i+34]

    fig, axes = plt.subplots(1, 2, figsize=FIG_BRAIN_SURFACE_SM, subplot_kw={'projection': '3d'})
    plotting.plot_surf_stat_map(fsaverage.infl_left, left_map, hemi='left', view='lateral',
                                colorbar=True, cmap=CMAP_DIVERGING, threshold=BRAIN_THRESHOLD, darkness=None,
                                bg_map=fsaverage.sulc_left, axes=axes[0])
    plotting.plot_surf_stat_map(fsaverage.infl_right, right_map, hemi='right', view='lateral',
                                colorbar=True, cmap=CMAP_DIVERGING, threshold=BRAIN_THRESHOLD, darkness=None,
                                bg_map=fsaverage.sulc_right, axes=axes[1])
    plt.suptitle(title)
    plt.savefig(os.path.join(OUTPUT_DIR, f"Surface_{title}.png"), dpi=DPI)

# --- 3. 数据加载 ---
def load_nodal_data():
    print(">>> 正在计算所有受试者的 Nodal Strength...")
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    
    nodal_strengths = []
    metadata = []

    for idx, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'], f"{row['Original_SUB_ID']}_MIND.csv")
        if os.path.exists(f_path):
            mat = pd.read_csv(f_path, index_col=0).values
            nodal_strengths.append(mat.sum(axis=1)) # 行求和得到 Nodal Strength
            metadata.append(row)
            
    return np.array(nodal_strengths), pd.DataFrame(metadata)

# --- 4. 执行分析 ---
def run_nodal_analysis():
    strengths, meta = load_nodal_data()
    meta['Group_MIND'] = pd.Categorical(meta['Group_MIND'], categories=GROUP_ORDER, ordered=True)
    num_nodes = strengths.shape[1]

    # --- [A] 四组间整体 ANCOVA ---
    print(">>> 正在进行 68 个节点的全局 ANCOVA (校正 Age, Sex, Edu)...")
    anova_p = []
    for i in range(num_nodes):
        meta['node_val'] = strengths[:, i]
        model = ols('node_val ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=meta).fit()
        table = anova_lm(model, typ=2)
        anova_p.append(table.loc['Group_MIND', 'PR(>F)'])
    
    _, anova_fdr, _, _ = multipletests(anova_p, method='fdr_bh')

    # 可视化 ANOVA 显著性
    plt.figure(figsize=FIG_WIDE_BAR)
    plt.bar(range(1, 69), -np.log10(anova_fdr), color=COLOR_BAR_SIG)
    plt.axhline(-np.log10(0.05), color=COLOR_REF_LINE, linestyle='--', label='p < 0.05 (FDR)')
    plt.xlabel('ROI Index')
    plt.ylabel('-log10(P-FDR)')
    plt.title('Nodal Strength ANCOVA Significance Across 4 Groups')
    plt.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "Nodal_ANCOVA_Significance.png"))

    # --- [B] 两两组间 Post-hoc 与 3D 渲染 ---
    print(">>> 正在进行两两组间比较与 3D 绘图...")
    for g1, g2 in combinations(GROUP_ORDER, 2):
        pair_mask = meta['Group_MIND'].isin([g1, g2])
        pair_meta = meta[pair_mask].copy()
        pair_meta['Group_MIND'] = pd.Categorical(pair_meta['Group_MIND'], categories=[g1, g2])
        pair_strengths = strengths[pair_mask.values]
        
        pair_t, pair_p = [], []
        for i in range(num_nodes):
            pair_meta['node_val'] = pair_strengths[:, i]
            model = ols('node_val ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=pair_meta).fit()
            pair_t.append(model.tvalues.iloc[1])
            pair_p.append(model.pvalues.iloc[1])
            
        _, p_fdr, _, _ = multipletests(pair_p, method='fdr_bh')
        
        # 统计存档
        stats_df = pd.DataFrame({'ROI': range(1, 69), 'T': pair_t, 'P_raw': pair_p, 'P_FDR': p_fdr})
        stats_df.to_csv(os.path.join(OUTPUT_DIR, f"Nodal_Stats_{g1}_vs_{g2}.csv"), index=False)
        
        # 3D 渲染 T-map
        plot_nodal_surface(pair_t, f"Nodal_Tmap_{g1}_vs_{g2}")

    # --- [C] 显著节点箱线图 ---
    best_node_idx = np.argmin(anova_p)
    meta['best_node'] = strengths[:, best_node_idx]
    plt.figure(figsize=FIG_SINGLE)
    sns.boxplot(x='Group_MIND', y='best_node', data=meta, palette=GROUP_PALETTE, hue='Group_MIND', legend=False)
    sns.stripplot(x='Group_MIND', y='best_node', data=meta, color=STRIP_COLOR, alpha=ALPHA_STRIP)
    plt.title(f"Distribution of Most Significant Node (ROI: {best_node_idx + 1})")
    plt.savefig(os.path.join(OUTPUT_DIR, "Top_Significant_Node_Boxplot.png"))

    print(f"\n>>> 节点水平分析完成！结果保存在: {OUTPUT_DIR}")
    plt.show()

if __name__ == "__main__":
    run_nodal_analysis()
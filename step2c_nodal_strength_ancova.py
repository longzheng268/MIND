import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.anova import anova_lm
from scipy import stats
from nilearn import plotting, datasets
from config import *

apply_style()

# --- 配置 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './nodal_statistical_results/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 3D 脑表面渲染 ---
def _plot_nodal_surface(t_values, title):
    """将 68 个 ROI 的 T 值映射到 Destrieux 脑表面并保存。"""
    fsaverage = datasets.fetch_surf_fsaverage()
    destrieux = datasets.fetch_atlas_surf_destrieux()
    left_map  = np.zeros(destrieux['map_left'].shape)
    right_map = np.zeros(destrieux['map_right'].shape)
    for i in range(34):
        left_map[destrieux['map_left']  == i + 1] = t_values[i]
        right_map[destrieux['map_right'] == i + 1] = t_values[i + 34]

    fig, axes = plt.subplots(1, 2, figsize=FIG_BRAIN_SURFACE_SM, subplot_kw={'projection': '3d'})
    plotting.plot_surf_stat_map(
        fsaverage.infl_left, left_map, hemi='left', view='lateral',
        colorbar=True, cmap=CMAP_DIVERGING, threshold=BRAIN_THRESHOLD,
        darkness=None, bg_map=fsaverage.sulc_left, axes=axes[0])
    plotting.plot_surf_stat_map(
        fsaverage.infl_right, right_map, hemi='right', view='lateral',
        colorbar=True, cmap=CMAP_DIVERGING, threshold=BRAIN_THRESHOLD,
        darkness=None, bg_map=fsaverage.sulc_right, axes=axes[1])
    plt.suptitle(title, fontsize=FONT_SUPTITLE)
    plt.savefig(os.path.join(OUTPUT_DIR, f"Surface_{title}.png"), dpi=DPI)

# --- 数据加载 ---
def load_nodal_data():
    print(">>> 正在提取所有受试者的 Nodal Strength 数据...")
    df    = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    nodal_strengths, metadata = [], []
    for _, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'],
                              f"{row['Original_SUB_ID']}_MIND.csv")
        if os.path.exists(f_path):
            mat = pd.read_csv(f_path, index_col=0).values
            nodal_strengths.append(mat.sum(axis=1))
            metadata.append(row)
    return np.array(nodal_strengths), pd.DataFrame(metadata)

# --- 主分析 ---
def run_nodal_analysis():
    strengths, meta = load_nodal_data()
    meta['Group_MIND'] = pd.Categorical(
        meta['Group_MIND'], categories=GROUP_ORDER, ordered=True)
    num_nodes = strengths.shape[1]   # 68

    # ── [A] 四组整体 ANCOVA ─────────────────────────────────────────────────
    print(f">>> 开始对 {num_nodes} 个节点进行四组 ANCOVA (协变量: Age, Sex, Edu)...")
    anova_rows = []
    anova_p    = []
    for i in range(num_nodes):
        meta['node_val'] = strengths[:, i]
        model = ols('node_val ~ Group_MIND + Age_at_Visit + C(Sex) + Education',
                    data=meta).fit()
        table  = anova_lm(model, typ=2)
        f_val  = table.loc['Group_MIND', 'F']
        p_val  = table.loc['Group_MIND', 'PR(>F)']
        anova_rows.append({'ROI_Index': i + 1, 'F_stat': f_val, 'P_raw': p_val})
        anova_p.append(p_val)

    nodal_anova_df = pd.DataFrame(anova_rows)
    _, nodal_anova_df['P_FDR'], _, _ = multipletests(anova_p, method='fdr_bh')
    nodal_anova_df.to_csv(
        os.path.join(OUTPUT_DIR, "Nodal_ANOVA_Results.csv"), index=False)

    # 图 A1：显著性条形图 (−log10 FDR)
    anova_fdr = nodal_anova_df['P_FDR'].values
    plt.figure(figsize=FIG_WIDE_BAR)
    plt.bar(range(1, 69), -np.log10(anova_fdr), color=COLOR_BAR_SIG)
    plt.axhline(-np.log10(0.05), color=COLOR_REF_LINE,
                linestyle='--', label='p < 0.05 (FDR)')
    plt.xlabel('ROI Index')
    plt.ylabel('-log10(P-FDR)')
    plt.title('Nodal Strength ANCOVA Significance Across 4 Groups')
    plt.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "Nodal_ANCOVA_Significance.png"), dpi=DPI)

    # 图 A2：Top-10 节点 F 统计条形图
    top_nodes = nodal_anova_df.nsmallest(10, 'P_raw')
    plt.figure(figsize=FIG_SINGLE)
    sns.barplot(x='F_stat', y='ROI_Index', data=top_nodes,
                orient='h', color=COLOR_BAR_SIG)
    plt.title("Top 10 Most Differing Nodes (ANOVA F-statistic)")
    plt.savefig(os.path.join(OUTPUT_DIR, "Top_Significant_Nodes_Bar.png"), dpi=DPI)

    # ── [B] 两两组间 Post-hoc ANCOVA ──────────────────────────────────────
    print(">>> 正在进行两两组间比较与 3D 脑图渲染...")
    hc_mask           = (meta['Group_MIND'] == 'HC')
    hc_nodal_baseline = strengths[hc_mask.values].mean(axis=0)
    all_pairs_t       = {}

    for g1, g2 in combinations(GROUP_ORDER, 2):
        print(f"    对比: {g1} vs {g2}")
        pair_mask = meta['Group_MIND'].isin([g1, g2])
        pair_meta = meta[pair_mask].copy()
        pair_meta['Group_MIND'] = pd.Categorical(
            pair_meta['Group_MIND'], categories=[g1, g2])
        pair_strengths = strengths[pair_mask.values]

        pair_results = []
        for i in range(num_nodes):
            pair_meta['node_val'] = pair_strengths[:, i]
            model = ols('node_val ~ Group_MIND + Age_at_Visit + C(Sex) + Education',
                        data=pair_meta).fit()
            pair_results.append({
                'ROI': i + 1,
                'T_stat': model.tvalues.iloc[1],
                'P_raw':  model.pvalues.iloc[1]
            })

        pair_df = pd.DataFrame(pair_results)
        _, pair_df['P_FDR'], _, _ = multipletests(pair_df['P_raw'], method='fdr_bh')
        pair_df.to_csv(
            os.path.join(OUTPUT_DIR, f"Nodal_Pairwise_{g1}_vs_{g2}.csv"), index=False)
        all_pairs_t[f"{g1}_vs_{g2}"] = pair_df['T_stat'].values

        # Hub 脆弱性相关（T 值与 HC 基线强度负相关 → Hub 受损更重）
        r_val, p_val = stats.pearsonr(hc_nodal_baseline, pair_df['T_stat'])
        print(f"    Hub Vulnerability (r={r_val:.3f}, p={p_val:.3f})")

        # 3D 脑表面 T-map
        _plot_nodal_surface(pair_df['T_stat'].values, f"Nodal_Tmap_{g1}_vs_{g2}")

    # 图 B1：所有对比 T 值汇总热力图
    t_summary_df = pd.DataFrame(all_pairs_t)
    plt.figure(figsize=FIG_HEATMAP_LG)
    sns.heatmap(t_summary_df, cmap=CMAP_DIVERGING, center=0, annot=False)
    plt.title("Nodal Strength T-statistics across all Pairwise Comparisons")
    plt.ylabel("ROI Index (1-68)")
    plt.savefig(os.path.join(OUTPUT_DIR, "Nodal_T_Summary_Heatmap.png"), dpi=DPI)

    # ── [C] 最显著节点箱线图 ──────────────────────────────────────────────
    best_node_idx = np.argmin(anova_p)
    meta['best_node'] = strengths[:, best_node_idx]
    plt.figure(figsize=FIG_SINGLE)
    sns.boxplot(x='Group_MIND', y='best_node', data=meta,
                palette=GROUP_PALETTE, hue='Group_MIND', legend=False)
    sns.stripplot(x='Group_MIND', y='best_node', data=meta,
                  color=STRIP_COLOR, alpha=ALPHA_STRIP)
    plt.title(f"Distribution of Most Significant Node (ROI: {best_node_idx + 1})")
    plt.savefig(os.path.join(OUTPUT_DIR, "Top_Significant_Node_Boxplot.png"), dpi=DPI)

    print(f"\n>>> 节点分析完成！结果保存在: {OUTPUT_DIR}")
    plt.show()

if __name__ == "__main__":
    run_nodal_analysis()

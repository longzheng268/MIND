import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from itertools import combinations
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multitest import multipletests
from scipy import stats
from config import *

apply_style()

# --- 配置路径 ---
BASE_DIR   = Path(__file__).resolve().parent
DATA_FILE  = BASE_DIR / 'scale' / 'MIND_baseline_with_followup_V04_V12.csv'
MIND_ROOT  = BASE_DIR / 'data' / 'MIND-Networks_newgroup'
OUTPUT_DIR = BASE_DIR / 'edgewise_results'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 上三角索引（k=1 不含对角线，共 2278 条边）
IU = np.triu_indices(68, k=1)


# ─────────────────────────────────────────────
# 数据加载
# ─────────────────────────────────────────────
def load_all_data():
    """
    加载全部受试者基线矩阵，同时计算：
      - 全矩阵 (N, 68, 68)
      - 节点强度 (N, 68)
      - 上三角连边向量 (N, 2278)
      - Betweenness Centrality (N, 68)  ← Hub 代理指标
      - 模块内 / 模块间平均连接强度 (N, 14*7)
    """
    print(">>> 正在加载矩阵并计算多层网络指标（含 Betweenness，耗时较长）...")
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"未找到数据文件: {DATA_FILE}")
    df    = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()

    all_mats, all_strengths, all_edges = [], [], []
    all_hubs, all_module_data, valid_meta = [], [], []

    for _, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'],
                              f"{row['Original_SUB_ID']}_MIND.csv")
        if not os.path.exists(f_path):
            continue

        mat = pd.read_csv(f_path, index_col=0).values
        mat = (mat + mat.T) / 2        # 强制对称
        np.fill_diagonal(mat, 0)       # 清除自环

        # Betweenness Centrality（Hub 脆弱性的代理指标）
        G = nx.from_numpy_array(mat)
        betweenness = np.array(
            list(nx.betweenness_centrality(G, weight='weight').values())
        )

        # 模块内（Intra）/ 模块间（Inter）平均连接
        module_metrics = {}
        for net_name, nodes in YEO7_MAP.items():
            idx   = [n - 1 for n in nodes]
            other = [i for i in range(68) if i not in idx]
            module_metrics[f'Intra_{net_name}'] = mat[np.ix_(idx, idx)].mean()
            module_metrics[f'Inter_{net_name}'] = mat[np.ix_(idx, other)].mean()

        all_mats.append(mat)
        all_strengths.append(mat.sum(axis=1))
        all_edges.append(mat[IU])
        all_hubs.append(betweenness)
        all_module_data.append(module_metrics)
        valid_meta.append(row)

    mat_arr      = np.array(all_mats)       # (N, 68, 68)
    strength_arr = np.array(all_strengths)  # (N, 68)
    edge_arr     = np.array(all_edges)      # (N, 2278)
    hub_arr      = np.array(all_hubs)       # (N, 68)  ← 暂存备用
    module_df    = pd.DataFrame(all_module_data)
    meta         = pd.DataFrame(valid_meta).reset_index(drop=True)
    meta['Group_MIND'] = pd.Categorical(
        meta['Group_MIND'], categories=GROUP_ORDER, ordered=True
    )
    return mat_arr, strength_arr, edge_arr, hub_arr, module_df, meta


# ─────────────────────────────────────────────
# 主分析流程
# ─────────────────────────────────────────────
def run_edgewise_analysis():
    mat_arr, strength_arr, edge_arr, hub_arr, module_df, meta = load_all_data()
    N, num_edges = len(meta), edge_arr.shape[1]
    print(f"    共加载 {N} 位受试者，{num_edges} 条连边。\n")

    # HC 组基线节点强度（用于 Hub Vulnerability 参照）
    hc_mask = (meta['Group_MIND'] == 'HC').values
    hc_nodal_baseline = strength_arr[hc_mask].mean(axis=0)

    # ═══ [A] 全局连接强度小提琴图 ════════════════════════════════════
    print(">>> [A] 绘制全局连接强度分布小提琴图...")
    meta['Global_MIND'] = mat_arr.mean(axis=(1, 2))
    plt.figure(figsize=FIG_SINGLE)
    sns.violinplot(x='Group_MIND', y='Global_MIND', data=meta,
                   palette=PALETTE_VIOLIN, inner="quart")
    sns.stripplot(x='Group_MIND', y='Global_MIND', data=meta,
                  color=STRIP_COLOR, alpha=ALPHA_STRIP)
    plt.title("Edge-wise Global Mean MIND Distribution across 4 Groups")
    plt.xlabel("Group")
    plt.ylabel("Mean MIND Connectivity")
    plt.savefig(os.path.join(OUTPUT_DIR, "Global_Edge_Boxplot.png"), dpi=DPI)
    plt.close()

    # ═══ [B] 最强连边箱线图 ══════════════════════════════════════════
    print(">>> [B] 绘制样本均值最高连边的分布箱线图...")
    mean_mat = mat_arr.mean(axis=0)
    flat_idx = np.argmax(np.triu(mean_mat, k=1))
    r_top, c_top = np.unravel_index(flat_idx, (68, 68))
    meta['Top_Edge_Strength'] = mat_arr[:, r_top, c_top]

    plt.figure(figsize=FIG_SINGLE)
    sns.boxplot(x='Group_MIND', y='Top_Edge_Strength', data=meta,
                order=GROUP_ORDER, palette=PALETTE_BOX)
    sns.stripplot(x='Group_MIND', y='Top_Edge_Strength', data=meta,
                  color=STRIP_COLOR, alpha=ALPHA_STRIP, order=GROUP_ORDER)
    plt.title(f"Edge Connection Strength: ROI {r_top+1} – ROI {c_top+1}"
              f" (Strongest Mean Edge)")
    plt.savefig(os.path.join(OUTPUT_DIR, "Edge_Strength_Boxplot.png"), dpi=DPI)
    plt.close()

    # ═══ [C] 节点强度 ANCOVA + 模块层统计 ════════════════════════════
    print(">>> [C] 计算节点强度 ANCOVA 及模块层统计...")
    nodal_rows = []
    for i in range(68):
        meta['_s'] = strength_arr[:, i]
        m = ols('_s ~ Group_MIND + Age_at_Visit + C(Sex) + Education',
                data=meta).fit()
        nodal_rows.append({
            'ROI': i + 1,
            'Strength_T': m.tvalues.iloc[1],
            'Strength_P': m.pvalues.iloc[1]
        })
    nodal_res = pd.DataFrame(nodal_rows)
    _, nodal_res['Strength_P_FDR'], _, _ = multipletests(
        nodal_res['Strength_P'], method='fdr_bh'
    )
    nodal_res.to_csv(os.path.join(OUTPUT_DIR, "Nodal_Statistical_Results.csv"),
                     index=False)

    module_rows = []
    for col_name in module_df.columns:
        meta['_m'] = module_df[col_name].values
        m = ols('_m ~ Group_MIND + Age_at_Visit + C(Sex) + Education',
                data=meta).fit()
        module_rows.append({
            'Metric': col_name,
            'T':      m.tvalues.iloc[1],
            'P':      m.pvalues.iloc[1]
        })
    pd.DataFrame(module_rows).to_csv(
        os.path.join(OUTPUT_DIR, "Module_Level_Stats.csv"), index=False
    )

    # ═══ [D] 四组连边 ANOVA（协变量校正，FDR 修正） ════════════════════
    print(f"\n>>> [D] 四组连边 ANCOVA（{num_edges} 条，FDR 校正中，请耐心等待）...")
    anova_p = []
    for e in range(num_edges):
        meta['_e'] = edge_arr[:, e]
        m = ols('_e ~ Group_MIND + Age_at_Visit + C(Sex) + Education',
                data=meta).fit()
        table = anova_lm(m, typ=2)
        anova_p.append(table.loc['Group_MIND', 'PR(>F)'])
    _, anova_fdr, _, _ = multipletests(anova_p, method='fdr_bh')

    # FDR p 值矩阵热力图
    anova_mat = np.zeros((68, 68))
    anova_mat[IU] = anova_fdr
    anova_mat = anova_mat + anova_mat.T
    plt.figure(figsize=FIG_HEATMAP_SM)
    sns.heatmap(anova_mat, cmap=CMAP_PVAL, vmax=0.05)
    plt.title("Edge-wise ANCOVA FDR-corrected P-map (Across 4 Groups)")
    plt.savefig(os.path.join(OUTPUT_DIR, "Edge_ANCOVA_FDR_Map.png"), dpi=DPI)
    plt.close()

    # 最显著连边四组箱线图
    best_edge_idx = int(np.argmin(anova_p))
    meta['Best_Edge'] = edge_arr[:, best_edge_idx]
    plt.figure(figsize=FIG_SINGLE)
    sns.boxplot(x='Group_MIND', y='Best_Edge', data=meta, palette=GROUP_PALETTE)
    sns.swarmplot(x='Group_MIND', y='Best_Edge', data=meta,
                  color=STRIP_COLOR, size=STRIP_SIZE)
    roi_a = IU[0][best_edge_idx] + 1
    roi_b = IU[1][best_edge_idx] + 1
    plt.title(f"Most Significant Edge Distribution (ROI {roi_a} – ROI {roi_b})")
    plt.savefig(os.path.join(OUTPUT_DIR, "Top_Significant_Edge_Boxplot.png"),
                dpi=DPI)
    plt.close()

    # ═══ [E] 两两组间深度分析 ════════════════════════════════════════
    print("\n>>> [E] 两两组间深度分析（均值差异 + T 矩阵 + 节点 ANCOVA + Hub 脆弱性）...")
    for g1, g2 in combinations(GROUP_ORDER, 2):
        print(f"\n    ── {g1} vs {g2} ──")
        pair_mask = meta['Group_MIND'].isin([g1, g2])
        curr_meta  = meta[pair_mask].copy().reset_index(drop=True)
        curr_meta['Group_MIND'] = pd.Categorical(
            curr_meta['Group_MIND'], categories=[g1, g2]
        )
        curr_mats     = mat_arr[pair_mask.values]
        curr_strengths = strength_arr[pair_mask.values]
        curr_edges    = edge_arr[pair_mask.values]

        # E1. 节点强度 ANCOVA（逐节点，FDR 校正）
        pair_nodal = []
        for i in range(68):
            curr_meta['_y'] = curr_strengths[:, i]
            m = ols('_y ~ Group_MIND + Age_at_Visit + C(Sex) + Education',
                    data=curr_meta).fit()
            pair_nodal.append({
                'ROI': i + 1,
                'T':   m.tvalues.iloc[1],
                'P':   m.pvalues.iloc[1]
            })
        pair_nodal_df = pd.DataFrame(pair_nodal)
        _, pair_nodal_df['P_FDR'], _, _ = multipletests(
            pair_nodal_df['P'], method='fdr_bh'
        )
        pair_nodal_df.to_csv(
            os.path.join(OUTPUT_DIR, f"Nodal_ANCOVA_{g1}_vs_{g2}.csv"),
            index=False
        )

        # E2. Hub Vulnerability：节点 T 值与 HC 基线强度的 Pearson 相关
        r_val, p_val = stats.pearsonr(hc_nodal_baseline, pair_nodal_df['T'])
        print(f"      Hub Vulnerability Correlation: r={r_val:.3f}, p={p_val:.3f}")

        # E3. 均值差异热力图（g1 – g2）
        mean_g1  = curr_mats[curr_meta['Group_MIND'] == g1].mean(axis=0)
        mean_g2  = curr_mats[curr_meta['Group_MIND'] == g2].mean(axis=0)
        diff_mat = mean_g1 - mean_g2
        plt.figure(figsize=FIG_HEATMAP_SM)
        sns.heatmap(diff_mat, cmap=CMAP_DIVERGING, center=0,
                    xticklabels=5, yticklabels=5)
        plt.title(f"Edge-wise Mean Difference: {g1} minus {g2}")
        plt.xlabel("ROI Index")
        plt.ylabel("ROI Index")
        plt.savefig(
            os.path.join(OUTPUT_DIR, f"Edge_Diff_{g1}_vs_{g2}.png"), dpi=DPI
        )
        plt.close()

        # E4. T 矩阵（scipy 独立 t 检验，未校正协变量）
        g1_mats = curr_mats[curr_meta['Group_MIND'] == g1]
        g2_mats = curr_mats[curr_meta['Group_MIND'] == g2]
        t_img, _ = stats.ttest_ind(g1_mats, g2_mats, axis=0)
        plt.figure(figsize=FIG_HEATMAP_SQ)
        sns.heatmap(t_img, cmap=CMAP_DIVERGING, center=0,
                    xticklabels=10, yticklabels=10)
        plt.title(f"Edge-wise T-statistic (Independent t-test): {g1} vs {g2}")
        plt.savefig(
            os.path.join(OUTPUT_DIR, f"Edge_Tmap_{g1}_vs_{g2}.png"), dpi=DPI
        )
        plt.close()

        # E5. T 矩阵（ANCOVA 协变量校正）
        pair_t_ancova = []
        for e in range(num_edges):
            curr_meta['_e'] = curr_edges[:, e]
            m = ols('_e ~ Group_MIND + Age_at_Visit + C(Sex) + Education',
                    data=curr_meta).fit()
            pair_t_ancova.append(m.tvalues.iloc[1])
        t_ancova_mat = np.zeros((68, 68))
        t_ancova_mat[IU] = pair_t_ancova
        t_ancova_mat = t_ancova_mat + t_ancova_mat.T
        plt.figure(figsize=FIG_HEATMAP_SM)
        sns.heatmap(t_ancova_mat, cmap=CMAP_DIVERGING, center=0)
        plt.title(f"Edge-wise T-stat (ANCOVA adjusted): {g1} vs {g2}")
        plt.savefig(
            os.path.join(OUTPUT_DIR, f"Edge_T_Map_{g1}_vs_{g2}.png"), dpi=DPI
        )
        plt.close()

    print(f"\n>>> 全部连边分析完成！结果保存至: {OUTPUT_DIR}")


if __name__ == "__main__":
    run_edgewise_analysis()

import os
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from config import *

# 注：本脚本为纯统计文件，不生成可视化图形
# 合并自：step2_stats_connectome_anova_3group.py + step2_stats_connectome_anova_4group.py

# ─────────────────────────────────────────────
# 公共工具函数
# ─────────────────────────────────────────────
def _run_anova(result_dir, mind_root, groups, label):
    """
    通用连边 ANOVA 函数：
      - 从指定目录按组加载 MIND 矩阵
      - 对每条连边（上三角 2278 条）做单因素 F-test
      - 筛选 p < 0.05 的边，构建对称 F 矩阵
      - 保存 ANOVA_F_Matrix.csv 到 result_dir
    """
    os.makedirs(result_dir, exist_ok=True)
    all_data, labels, roi_names = [], [], None

    print(f"\n>>> [{label}] 正在读取 {len(groups)} 组 MIND 矩阵...")
    for group in groups:
        path = os.path.join(mind_root, group)
        if not os.path.exists(path):
            print(f"    [!] 警告：找不到路径 {path}，已跳过。")
            continue
        files = [f for f in os.listdir(path) if f.endswith('.csv')]
        for f in files:
            df = pd.read_csv(os.path.join(path, f), index_col=0)
            if roi_names is None:
                roi_names = df.columns
            all_data.append(df.values[np.triu_indices(68, k=1)])
            labels.append(group)

    feature_matrix = np.array(all_data)
    labels         = np.array(labels)
    num_edges      = feature_matrix.shape[1]

    print(f"    共 {len(labels)} 位受试者，{num_edges} 条连边，开始 ANOVA 检验...")
    f_stats, p_values = [], []
    for i in range(num_edges):
        group_samples = [feature_matrix[labels == g, i] for g in groups]
        # 剔除空组（路径不存在时 labels 可能缺组）
        group_samples = [s for s in group_samples if len(s) > 0]
        f_val, p_val  = stats.f_oneway(*group_samples)
        f_stats.append(f_val)
        p_values.append(p_val)

    # FDR 校正
    _, p_fdr, _, _ = multipletests(p_values, method='fdr_bh')

    # 构建对称 F 矩阵（仅保留 FDR p < 0.05 的边）
    iu            = np.triu_indices(68, k=1)
    diff_matrix   = np.zeros((68, 68))
    sig_count     = 0
    for idx, p in enumerate(p_fdr):
        if p < 0.05:
            r, c = iu[0][idx], iu[1][idx]
            diff_matrix[r, c] = f_stats[idx]
            diff_matrix[c, r] = f_stats[idx]
            sig_count += 1

    out_path = os.path.join(result_dir, "ANOVA_F_Matrix.csv")
    pd.DataFrame(diff_matrix, index=roi_names, columns=roi_names).to_csv(out_path)

    # 同时保存完整的逐边结果表
    full_df = pd.DataFrame({
        'edge_idx': range(num_edges),
        'f_stat':   f_stats,
        'p_raw':    p_values,
        'p_fdr':    p_fdr
    })
    full_df.to_csv(os.path.join(result_dir, "ANOVA_Full_Edge_Table.csv"), index=False)

    print(f"    [{label}] 发现 {sig_count} 条 FDR 显著差异连边（FDR p < 0.05）。")
    print(f"    结果已保存至: {result_dir}")
    return diff_matrix, full_df


# ─────────────────────────────────────────────
# 分析入口
# ─────────────────────────────────────────────
def run_connectome_anova():
    # ── 分析 1：三组（HC / prodromal / PD）────────────────────────────
    _run_anova(
        result_dir = './analysis_results_3group/',
        mind_root  = './data/MIND-Networks/',
        groups     = ['HC', 'prodromal', 'PD'],
        label      = '3-Group ANOVA'
    )

    # ── 分析 2：四组（按 SAA 分层）────────────────────────────────────
    _run_anova(
        result_dir = './analysis_results_4group/',
        mind_root  = './data/MIND-Networks_newgroup/',
        groups     = GROUP_ORDER,   # 来自 config.py
        label      = '4-Group ANOVA'
    )

    print("\n>>> 两批次 Connectome ANOVA 全部完成。")


if __name__ == "__main__":
    run_connectome_anova()

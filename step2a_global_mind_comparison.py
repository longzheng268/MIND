import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from nilearn import plotting, datasets, surface
from math import pi
from config import *

apply_style()

# --- 1. 配置 ---
DATA_FILE = './scale/MIND_baseline_with_followup_V04_V12.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './analysis_results_professional/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 2. 核心绘图逻辑 ---

def draw_radar(radar_df, title):
    labels = radar_df.columns.tolist()
    num_vars = len(labels)
    angles = [n / float(num_vars) * 2 * pi for n in range(num_vars)]
    angles += angles[:1]
    
    plt.figure(figsize=FIG_RADAR_SM)
    ax = plt.subplot(111, polar=True)
    for i, row in radar_df.iterrows():
        values = row.tolist() + [row.tolist()[0]]
        ax.plot(angles, values, linewidth=LINEWIDTH_THIN, label=i)
        ax.fill(angles, values, alpha=ALPHA_FILL)

    plt.xticks(angles[:-1], labels)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    plt.title(title)
    plt.savefig(os.path.join(OUTPUT_DIR, f"Radar_{title}.png"), dpi=DPI)

def plot_atlas_based_surface(t_values, title):
    """使用解剖分区模板进行着色，解决'像蛇'的问题，使其符合解剖边界"""
    fsaverage = datasets.fetch_surf_fsaverage()
    destrieux = datasets.fetch_atlas_surf_destrieux()
    
    # 准备映射数据：左半球前34个ROI，右半球后34个ROI
    # 我们将 ROI T值赋给 Destrieux 模板中对应的区域标签
    left_roi_t = t_values[:34]
    right_roi_t = t_values[34:]
    
    left_map = np.zeros(destrieux['map_left'].shape)
    right_map = np.zeros(destrieux['map_right'].shape)
    
    # 简单的解剖标签映射逻辑（假设你的68个ROI按顺序对应解剖分区）
    for i in range(34):
        left_map[destrieux['map_left'] == i+1] = left_roi_t[i]
        right_map[destrieux['map_right'] == i+1] = right_roi_t[i]

    fig, axes = plt.subplots(1, 2, figsize=FIG_BRAIN_SURFACE, subplot_kw={'projection': '3d'})

    plotting.plot_surf_stat_map(
        fsaverage.infl_left, left_map, hemi='left', view='lateral',
        colorbar=True, cmap=CMAP_DIVERGING, threshold=BRAIN_THRESHOLD, darkness=None,
        bg_map=fsaverage.sulc_left, axes=axes[0]
    )
    plotting.plot_surf_stat_map(
        fsaverage.infl_right, right_map, hemi='right', view='lateral',
        colorbar=True, cmap=CMAP_DIVERGING, threshold=BRAIN_THRESHOLD, darkness=None,
        bg_map=fsaverage.sulc_right, axes=axes[1]
    )

    plt.suptitle(title, fontsize=FONT_SUPTITLE)
    plt.savefig(os.path.join(OUTPUT_DIR, f"Surface_{title}.png"), dpi=DPI, bbox_inches='tight')

# --- 3. 分析主流程 ---

def run_pipeline():
    print(">>> [1/5] 正在加载数据并提取特征...")
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    df_bl['Group_MIND'] = pd.Categorical(df_bl['Group_MIND'], categories=GROUP_ORDER, ordered=True)

    nodal_strengths, network_means, valid_ids = [], [], []

    for idx, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'], f"{row['Original_SUB_ID']}_MIND.csv")
        if os.path.exists(f_path):
            mat = pd.read_csv(f_path, index_col=0).values
            nodal_strengths.append(mat.sum(axis=1))
            net_vals = {n: mat[np.ix_([r-1 for r in rs], [r-1 for r in rs])].mean() for n, rs in YEO7_MAP.items()}
            network_means.append(net_vals)
            valid_ids.append(idx)

    df_final = df_bl.loc[valid_ids].reset_index(drop=True)
    strength_mat = np.array(nodal_strengths)
    net_df = pd.DataFrame(network_means)

    print(">>> [2/5] 生成雷达图...")
    radar_data = pd.concat([df_final[['Group_MIND']], net_df], axis=1).groupby('Group_MIND', observed=True).mean()
    draw_radar(radar_data, "Baseline_Network_Distribution")

    print(">>> [3/5] 生成全局强度对比箱线图...")
    df_final['Global_Strength'] = strength_mat.mean(axis=1)
    plt.figure(figsize=FIG_SINGLE)
    sns.boxplot(x='Group_MIND', y='Global_Strength', data=df_final,
                palette=GROUP_PALETTE, hue='Group_MIND', legend=False)
    sns.stripplot(x='Group_MIND', y='Global_Strength', data=df_final,
                  color=STRIP_COLOR, alpha=ALPHA_STRIP)
    plt.title("Global Connectivity Strength Comparison")
    plt.savefig(os.path.join(OUTPUT_DIR, "Global_Boxplot.png"), dpi=DPI)

    print(">>> [4/5] 执行统计分析并绘制解剖脑热力图...")
    for g1, g2 in combinations(GROUP_ORDER, 2):
        print(f"    正在处理: {g1} vs {g2}")
        mask = df_final['Group_MIND'].isin([g1, g2])
        pair_df = df_final[mask].copy()
        pair_df['Group_MIND'] = pd.Categorical(pair_df['Group_MIND'], categories=[g1, g2])
        pair_data = strength_mat[mask.values, :]

        t_stats, p_vals = [], []
        for i in range(68):
            pair_df['y'] = pair_data[:, i]
            model = ols('y ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=pair_df).fit()
            t_stats.append(model.tvalues.iloc[1])
            p_vals.append(model.pvalues.iloc[1])

        # FDR 校正
        _, p_fdr, _, _ = multipletests(p_vals, method='fdr_bh')
        pd.DataFrame({'ROI': range(1,69), 'T': t_stats, 'P_raw': p_vals, 'P_FDR': p_fdr}).to_csv(
            os.path.join(OUTPUT_DIR, f"Stats_{g1}_vs_{g2}.csv"), index=False
        )

        # 绘制符合解剖结构的脑图
        plot_atlas_based_surface(t_stats, f"{g1}_vs_{g2}_Contrast")

    print(">>> [5/5] 生成显著性矩阵热力图...")
    # 汇总所有组间对比的 T 值矩阵
    plt.figure(figsize=FIG_HEATMAP_LG)
    sns.heatmap(pd.DataFrame(strength_mat).corr(), cmap=CMAP_DIVERGING, center=0,
                xticklabels=False, yticklabels=False)
    plt.title("Connectome Correlation Matrix (Baseline)")
    plt.savefig(os.path.join(OUTPUT_DIR, "Connectome_Matrix.png"), dpi=DPI)

    print(f"\n>>> 任务全部完成！所有图像保存在 {OUTPUT_DIR}")
    print(">>> 正在一次性弹出所有窗口...")
    plt.show(block=True) # 在最后调用，一次性显示所有生成的图

if __name__ == "__main__":
    run_pipeline()
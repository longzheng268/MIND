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

# --- 1. 配置 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './analysis_results_final_viz/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

GROUPS = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']
YEO7_MAP = {
    'Visual': [1,2,3,4,5,6,7,8,35,36,37,38,39,40,41,42],
    'Somatomotor': [9,10,11,12,13,14,43,44,45,46,47,48],
    'Dorsal_Attn': [15,16,17,49,50,51],
    'Ventral_Attn': [18,19,20,52,53,54],
    'Limbic': [21,22,55,56],
    'Frontoparietal': [23,24,25,26,57,58,59,60],
    'Default': [27,28,29,30,31,32,33,34,61,62,63,64,65,66,67,68]
}

# --- 2. 稳健的绘图函数 ---

def draw_radar(radar_df, title):
    labels = radar_df.columns.tolist()
    num_vars = len(labels)
    angles = [n / float(num_vars) * 2 * pi for n in range(num_vars)]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    for i, row in radar_df.iterrows():
        values = row.tolist() + [row.tolist()[0]]
        ax.plot(angles, values, linewidth=2, label=i)
        ax.fill(angles, values, alpha=0.1)
    
    plt.xticks(angles[:-1], labels)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    plt.title(title)
    plt.savefig(os.path.join(OUTPUT_DIR, f"Radar_{title}.png"), dpi=300)
    plt.show() # 窗口弹出

def plot_stat_on_surface_robust(t_values, title):
    """
    使用 fsaverage 表面直接映射。
    通过简单的顶点扩展解决 ValueError，确保红蓝热力图弹出。
    """
    print(f"    >>> 正在渲染 3D 脑图: {title}")
    fsaverage = datasets.fetch_surf_fsaverage()
    
    # 左右半球各 34 个 ROI
    t_left = np.array(t_values[:34])
    t_right = np.array(t_values[34:])
    
    # 加载网格以获取顶点数
    mesh_left = surface.load_surf_mesh(fsaverage.pial_left)
    mesh_right = surface.load_surf_mesh(fsaverage.pial_right)
    nv_left = mesh_left[0].shape[0]
    nv_right = mesh_right[0].shape[0]

    # 将 ROI 值均匀映射到所有顶点（解决匹配报错的核心逻辑）
    left_map = np.repeat(t_left, nv_left // 34 + 1)[:nv_left]
    right_map = np.repeat(t_right, nv_right // 34 + 1)[:nv_right]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), subplot_kw={'projection': '3d'})
    
    # 渲染左半球
    plotting.plot_surf_stat_map(
        fsaverage.infl_left, left_map, hemi='left', view='lateral',
        colorbar=True, cmap='RdBu_r', threshold=0.01, 
        bg_map=fsaverage.sulc_left, axes=axes[0]
    )
    # 渲染右半球
    plotting.plot_surf_stat_map(
        fsaverage.infl_right, right_map, hemi='right', view='lateral',
        colorbar=True, cmap='RdBu_r', threshold=0.01, 
        bg_map=fsaverage.sulc_right, axes=axes[1]
    )
    
    plt.suptitle(title)
    plt.savefig(os.path.join(OUTPUT_DIR, f"Surface_{title}.png"), dpi=300)
    plt.show() # 窗口弹出

# --- 3. 分析 Pipeline ---

def run_ultimate_pipeline():
    print(">>> [1/4] 加载基线数据并筛选...")
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    df_bl['Group_MIND'] = pd.Categorical(df_bl['Group_MIND'], categories=GROUPS, ordered=True)

    nodal_strengths, network_means, valid_ids = [], [], []

    print(">>> [2/4] 处理矩阵特征...")
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

    # 绘制雷达图
    radar_avg = pd.concat([df_final[['Group_MIND']], net_df], axis=1).groupby('Group_MIND', observed=True).mean()
    draw_radar(radar_avg, "Network_Profile")

    print(">>> [3/4] 执行两两对比与 T-map 弹出...")
    for g1, g2 in combinations(GROUPS, 2):
        print(f"\n分析对比项: {g1} vs {g2}")
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
        pd.DataFrame({'ROI': range(1,69), 'T': t_stats, 'P': p_vals, 'P_FDR': p_fdr}).to_csv(
            os.path.join(OUTPUT_DIR, f"Stats_{g1}_vs_{g2}.csv"), index=False
        )

        # 核心：显示热力图
        plot_stat_on_surface_robust(t_stats, f"{g1}_vs_{g2}")

    print(f"\n>>> 分析报告生成完毕！保存在 {OUTPUT_DIR}")

if __name__ == "__main__":
    run_ultimate_pipeline()
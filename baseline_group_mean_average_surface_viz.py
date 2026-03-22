import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from nilearn import plotting, datasets, surface

# --- 1. 配置与路径 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './analysis_results_means/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

GROUPS = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']

def plot_mean_surface(mean_values, group_name):
    """
    为每一组生成独立的解剖分区平均脑图
    """
    print(f"    >>> 正在渲染组平均图: {group_name}")
    fsaverage = datasets.fetch_surf_fsaverage()
    destrieux = datasets.fetch_atlas_surf_destrieux()
    
    # 映射逻辑：前34左，后34右
    left_vals = mean_values[:34]
    right_vals = mean_values[34:]
    
    left_map = np.zeros(destrieux['map_left'].shape)
    right_map = np.zeros(destrieux['map_right'].shape)
    
    for i in range(34):
        left_map[destrieux['map_left'] == i+1] = left_vals[i]
        right_map[destrieux['map_right'] == i+1] = right_vals[i]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), subplot_kw={'projection': '3d'})
    
    # 保持颜色规划一致 (RdBu_r)，如果想突出强度也可以考虑用 'YlOrRd'
    plotting.plot_surf_stat_map(
        fsaverage.infl_left, left_map, hemi='left', view='lateral',
        colorbar=True, cmap='RdBu_r', threshold=None, darkness=None,
        bg_map=fsaverage.sulc_left, axes=axes[0]
    )
    plotting.plot_surf_stat_map(
        fsaverage.infl_right, right_map, hemi='right', view='lateral',
        colorbar=True, cmap='RdBu_r', threshold=None, darkness=None,
        bg_map=fsaverage.sulc_right, axes=axes[1]
    )
    
    plt.suptitle(f"Mean Spatial Distribution: {group_name}", fontsize=16)
    file_name = f"Mean_Spatial_Map_{group_name}.png"
    plt.savefig(os.path.join(OUTPUT_DIR, file_name), dpi=300, bbox_inches='tight')

def run_mean_pipeline():
    print(">>> [1/3] 正在加载基线数据...")
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    
    nodal_data = []
    group_labels = []

    print(">>> [2/3] 提取各组原始矩阵...")
    for idx, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'], f"{row['Original_SUB_ID']}_MIND.csv")
        if os.path.exists(f_path):
            mat = pd.read_csv(f_path, index_col=0).values
            nodal_data.append(mat.sum(axis=1)) # 提取 Nodal Strength
            group_labels.append(row['Group_MIND'])

    # 转为 DataFrame 方便按组计算均值
    res_df = pd.DataFrame(nodal_data)
    res_df['Group'] = group_labels

    print(">>> [3/3] 计算各组均值并绘图...")
    # 计算每组在68个ROI上的平均值
    group_means = res_df.groupby('Group').mean()

    # 循环渲染四张图
    for group in GROUPS:
        if group in group_means.index:
            mean_vals = group_means.loc[group].values
            plot_mean_surface(mean_vals, group)
        else:
            print(f"    [警告] 数据中未找到组: {group}")

    print(f"\n>>> 任务完成！平均分布图已保存至 {OUTPUT_DIR}")
    print(">>> 正在弹出窗口查看...")
    plt.show()

if __name__ == "__main__":
    run_mean_pipeline()
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from config import *

apply_style()

# --- 1. 环境配置 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './statistical_results_nodal_edge/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 2. 数据加载与预处理 ---
def load_all_matrices():
    print(">>> 正在加载所有受试者矩阵并提取特征...")
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    
    all_matrices = []
    all_nodal_strength = []
    valid_metadata = []

    for idx, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'], f"{row['Original_SUB_ID']}_MIND.csv")
        if os.path.exists(f_path):
            mat = pd.read_csv(f_path, index_col=0).values
            all_matrices.append(mat)
            all_nodal_strength.append(mat.sum(axis=1))
            valid_metadata.append(row)
            
    return np.array(all_matrices), np.array(all_nodal_strength), pd.DataFrame(valid_metadata)

# --- 3. 统计执行函数 ---
def run_statistical_analysis():
    mats, strengths, meta = load_all_matrices()
    meta['Group_MIND'] = pd.Categorical(meta['Group_MIND'], categories=GROUP_ORDER, ordered=True)

    # 遍历所有两两组合
    for g1, g2 in combinations(GROUP_ORDER, 2):
        print(f"\n>>> 正在对比: {g1} vs {g2}")
        mask = meta['Group_MIND'].isin([g1, g2])
        curr_meta = meta[mask].copy()
        curr_meta['Group_MIND'] = pd.Categorical(curr_meta['Group_MIND'], categories=[g1, g2])
        
        # A. Nodal Strength 统计 (68个节点)
        print("    正在进行 Nodal Strength ANCOVA...")
        curr_strengths = strengths[mask.values]
        nodal_results = []
        for i in range(68):
            curr_meta['y'] = curr_strengths[:, i]
            # 引入协变量：年龄、性别、教育程度
            model = ols('y ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=curr_meta).fit()
            nodal_results.append({
                'ROI_ID': i + 1,
                'T_stat': model.tvalues.iloc[1],
                'P_raw': model.pvalues.iloc[1]
            })
        
        nodal_df = pd.DataFrame(nodal_results)
        _, nodal_df['P_FDR'], _, _ = multipletests(nodal_df['P_raw'], method='fdr_bh')
        nodal_df.to_csv(os.path.join(OUTPUT_DIR, f"Nodal_Stats_{g1}_vs_{g2}.csv"), index=False)
        
        # B. Edge-wise Pattern 统计 (68x68 矩阵)
        print("    正在生成 Edge-wise 差异矩阵图...")
        curr_mats = mats[mask.values]
        # 计算两组间的平均矩阵差值
        mean_mat_g1 = curr_mats[curr_meta['Group_MIND'] == g1].mean(axis=0)
        mean_mat_g2 = curr_mats[curr_meta['Group_MIND'] == g2].mean(axis=0)
        diff_mat = mean_mat_g1 - mean_mat_g2 # 正值表示 g1 > g2
        
        plt.figure(figsize=FIG_HEATMAP_SM)
        sns.heatmap(diff_mat, cmap=CMAP_DIVERGING, center=0, xticklabels=5, yticklabels=5)
        plt.title(f"Edge-wise Difference: {g1} minus {g2}")
        plt.xlabel("ROI Index")
        plt.ylabel("ROI Index")
        plt.savefig(os.path.join(OUTPUT_DIR, f"Edge_Diff_{g1}_vs_{g2}.png"), dpi=DPI)
        
    print(f"\n>>> 统计完成！结果已保存至: {OUTPUT_DIR}")
    plt.show()

if __name__ == "__main__":
    run_statistical_analysis()
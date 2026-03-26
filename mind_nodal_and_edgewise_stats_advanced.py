import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
import networkx as nx
from config import *

apply_style()

# --- 1. 配置与路径 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
MIND_ROOT = './data/MIND-Networks_newgroup/'
OUTPUT_DIR = './analysis_results_advanced_network/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Yeo 7 模块定义 (用于计算模块内/间连接)

# --- 2. 核心计算函数 ---

def calculate_network_metrics(mat):
    """计算单个矩阵的高级拓扑指标"""
    # Nodal Strength
    strength = mat.sum(axis=1)
    
    # Hub Vulnerability: 这里用 Betweenness Centrality 作为代理
    G = nx.from_numpy_array(mat)
    betweenness = np.array(list(nx.betweenness_centrality(G, weight='weight').values()))
    
    # 模块间/模块内连接
    module_metrics = {}
    for name, nodes in YEO7_MAP.items():
        idx = [n-1 for n in nodes]
        # 模块内 (Intra-module)
        intra = mat[np.ix_(idx, idx)].mean()
        module_metrics[f'Intra_{name}'] = intra
        
        # 模块间 (Inter-module: 该模块到其他所有节点的平均值)
        other_idx = [i for i in range(68) if i not in idx]
        inter = mat[np.ix_(idx, other_idx)].mean()
        module_metrics[f'Inter_{name}'] = inter
        
    return strength, betweenness, module_metrics

# --- 3. 运行流水线 ---

def run_advanced_analysis():
    print(">>> [1/4] 加载数据并计算多层网络指标...")
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()
    
    all_mats = []
    all_nodal_strengths = []
    all_hubs = []
    all_module_data = []
    valid_info = []

    for idx, row in df_bl.iterrows():
        f_path = os.path.join(MIND_ROOT, row['Group_MIND'], f"{row['Original_SUB_ID']}_MIND.csv")
        if os.path.exists(f_path):
            mat = pd.read_csv(f_path, index_col=0).values
            # 确保矩阵对称且无自环
            mat = (mat + mat.T) / 2
            np.fill_diagonal(mat, 0)
            
            s, b, m = calculate_network_metrics(mat)
            
            all_mats.append(mat)
            all_nodal_strengths.append(s)
            all_hubs.append(b)
            all_module_data.append(m)
            valid_info.append(row)

    df_final = pd.DataFrame(valid_info).reset_index(drop=True)
    mat_stack = np.array(all_mats) # (N, 68, 68)
    nodal_stack = np.array(all_nodal_strengths)
    hub_stack = np.array(all_hubs)
    module_df = pd.DataFrame(all_module_data)

    print(">>> [2/4] 执行组间连边 (Edge-wise) 统计与箱线图绘制...")
    # 选取一个具有代表性的连边进行箱线图绘制 (例如平均值最高的边)
    mean_mat = mat_stack.mean(axis=0)
    flat_idx = np.argmax(np.triu(mean_mat, k=1))
    row, col = np.unravel_index(flat_idx, (68, 68))
    
    df_final['Edge_Strength'] = mat_stack[:, row, col]
    
    plt.figure(figsize=FIG_SINGLE)
    sns.boxplot(x='Group_MIND', y='Edge_Strength', data=df_final, order=GROUP_ORDER, palette=PALETTE_BOX)
    sns.stripplot(x='Group_MIND', y='Edge_Strength', data=df_final, color=STRIP_COLOR, alpha=ALPHA_STRIP, order=GROUP_ORDER)
    plt.title(f"Edge Connection Strength: ROI {row+1} - ROI {col+1}")
    plt.savefig(os.path.join(OUTPUT_DIR, "Edge_Strength_Boxplot.png"))

    print(">>> [3/4] 节点层差异分析 (Nodal Strength & Hubs)...")
    nodal_results = []
    for i in range(68):
        df_final['target_s'] = nodal_stack[:, i]
        df_final['target_h'] = hub_stack[:, i]
        
        # ANCOVA 校正
        model_s = ols('target_s ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=df_final).fit()
        nodal_results.append({
            'ROI': i+1,
            'Strength_T': model_s.tvalues.iloc[1],
            'Strength_P': model_s.pvalues.iloc[1]
        })
    
    nodal_res_df = pd.DataFrame(nodal_results)
    _, nodal_res_df['Strength_P_FDR'], _, _ = multipletests(nodal_res_df['Strength_P'], method='fdr_bh')
    nodal_res_df.to_csv(os.path.join(OUTPUT_DIR, "Nodal_Statistical_Results.csv"), index=False)

    print(">>> [4/4] 模块间/模块内连接差异分析...")
    module_stats = []
    for col in module_df.columns:
        df_final['m_val'] = module_df[col].values
        model = ols('m_val ~ Group_MIND + Age_at_Visit + C(Sex) + Education', data=df_final).fit()
        module_stats.append({'Metric': col, 'T': model.tvalues.iloc[1], 'P': model.pvalues.iloc[1]})
    
    pd.DataFrame(module_stats).to_csv(os.path.join(OUTPUT_DIR, "Module_Level_Stats.csv"), index=False)

    print(f"\n>>> 分析报告已生成！请查看: {OUTPUT_DIR}")
    plt.show()

if __name__ == "__main__":
    run_advanced_analysis()
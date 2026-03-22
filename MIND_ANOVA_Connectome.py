import os
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

# 1. 配置路径
RESULT_DIR = './data/MIND-Networks/'
GROUPS = ['HC', 'prodromal', 'PD']  # 按病程顺序排列
OUTPUT_DIR = './analysis_results/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def collect_and_analyze():
    all_data = []
    labels = []
    
    # --- 数据汇总 ---
    for group in GROUPS:
        path = os.path.join(RESULT_DIR, group)
        if not os.path.exists(path): continue
        files = [f for f in os.listdir(path) if f.endswith('.csv')]
        
        for f in files:
            df = pd.read_csv(os.path.join(path, f), index_col=0)
            # 提取上三角作为特征 (2278条边)
            upper_tri = df.values[np.triu_indices(68, k=1)]
            all_data.append(upper_tri)
            labels.append(group)
            
    feature_matrix = np.array(all_data)
    roi_names = pd.read_csv(os.path.join(path, files[0]), index_col=0).columns
    
    # --- 统计分析：ANOVA ---
    print(f"开始进行三组间 ANOVA 检验 (共 {feature_matrix.shape[1]} 条连接)...")
    p_values = []
    f_stats = []
    
    for i in range(feature_matrix.shape[1]):
        # 获取每一条边在三组中的分布
        samples = [feature_matrix[np.array(labels) == g, i] for g in GROUPS]
        f_val, p_val = stats.f_oneway(*samples)
        f_stats.append(f_val)
        p_values.append(p_val)
    
    # --- 筛选显著连接 (p < 0.05) ---
    results_df = pd.DataFrame({
        'edge_idx': range(len(p_values)),
        'f_stat': f_stats,
        'p_raw': p_values
    })
    
    # 导出显著差异矩阵用于脑图绘制
    # 我们只保留 p < 0.05 的 F 值，其余设为 0
    diff_matrix = np.zeros((68, 68))
    sig_indices = np.where(np.array(p_values) < 0.05)[0]
    
    upper_indices = np.triu_indices(68, k=1)
    for idx in sig_indices:
        r, c = upper_indices[0][idx], upper_indices[1][idx]
        diff_matrix[r, c] = f_stats[idx]
        diff_matrix[c, r] = f_stats[idx] # 对称
        
    # 保存结果
    pd.DataFrame(diff_matrix, index=roi_names, columns=roi_names).to_csv(f"{OUTPUT_DIR}/ANOVA_F_Matrix.csv")
    print(f"分析完成。找到 {len(sig_indices)} 条显著差异连接。差异矩阵已保存。")

if __name__ == "__main__":
    collect_and_analyze()
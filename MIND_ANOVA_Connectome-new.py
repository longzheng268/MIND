import os
import numpy as np
import pandas as pd
from scipy import stats

# 1. 配置路径 - 指向你分好 4 组的目录
RESULT_DIR = './data/MIND-Networks_newgroup/'
# 按照你 Aim 1 的假设顺序排列，方便后续观察趋势
GROUPS = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+'] 
OUTPUT_DIR = './analysis_results-new/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_4group_anova():
    all_data = []
    labels = []
    
    # --- 数据汇总 ---
    print(">>> 正在读取 4 组 MIND 矩阵...")
    roi_names = None
    for group in GROUPS:
        path = os.path.join(RESULT_DIR, group)
        if not os.path.exists(path): 
            print(f" [!] 警告：找不到路径 {path}")
            continue
        files = [f for f in os.listdir(path) if f.endswith('.csv')]
        
        for f in files:
            df = pd.read_csv(os.path.join(path, f), index_col=0)
            if roi_names is None: roi_names = df.columns
            # 提取上三角 (2278条边)
            upper_tri = df.values[np.triu_indices(68, k=1)]
            all_data.append(upper_tri)
            labels.append(group)
            
    feature_matrix = np.array(all_data)
    labels = np.array(labels)
    
    # --- 统计分析：ANOVA ---
    print(f">>> 开始进行四组间 ANOVA 检验 (共 {feature_matrix.shape[1]} 条连接)...")
    f_stats = []
    p_values = []
    
    for i in range(feature_matrix.shape[1]):
        # 提取当前连接在四组中的所有值
        group_samples = [feature_matrix[labels == g, i] for g in GROUPS]
        f_val, p_val = stats.f_oneway(*group_samples)
        f_stats.append(f_val)
        p_values.append(p_val)
    
    # --- 构建差异矩阵 (F-map) ---
    # 只保留 p < 0.05 的位置，用于后续特征提取的“掩模 (Mask)”
    diff_matrix = np.zeros((68, 68))
    upper_indices = np.triu_indices(68, k=1)
    sig_count = 0
    
    for idx, p in enumerate(p_values):
        if p < 0.05:
            r, c = upper_indices[0][idx], upper_indices[1][idx]
            diff_matrix[r, c] = f_stats[idx]
            diff_matrix[c, r] = f_stats[idx]
            sig_count += 1
            
    # 保存结果
    out_path = os.path.join(OUTPUT_DIR, "ANOVA_F_Matrix.csv")
    pd.DataFrame(diff_matrix, index=roi_names, columns=roi_names).to_csv(out_path)
    print(f"\n>>> 分析完成！")
    print(f"在四组间发现 {sig_count} 条具有显著差异的连接。")
    print(f"显著性矩阵已保存至: {out_path}")

if __name__ == "__main__":
    run_4group_anova()
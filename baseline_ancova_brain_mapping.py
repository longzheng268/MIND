import os
import numpy as np
import pandas as pd
import glob
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
import re

# --- 路径配置 ---
MIND_ROOT = './data/MIND-Networks_newgroup/'
LONG_DATA_FILE = './MIND_Longitudinal_Clean_Data.csv' # 使用之前生成的融合表
OUTPUT_DIR = './analysis_results_ancova/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

GROUPS = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']

def clean_id(s):
    match = re.search(r'sub\d+', str(s).lower())
    return match.group(0) if match else s.strip()

def run_full_brain_ancova():
    # 1. 加载融合后的基线量表数据（含协变量）
    print(">>> 正在加载基线协变量数据...")
    df_all = pd.read_csv(LONG_DATA_FILE)
    df_bl = df_all[df_all['EVENT_ID'] == 'BL'].copy()
    
    # 确保 Group 是分类变量
    df_bl['Group_MIND'] = pd.Categorical(df_bl['Group_MIND'], categories=GROUPS, ordered=True)

    # 2. 读取所有被试的原始 MIND 矩阵 (2278条边)
    print(">>> 正在读取原始 MIND 矩阵并对齐被试...")
    all_matrices = []
    valid_patnos = []
    roi_names = None

    for _, row in df_bl.iterrows():
        # 寻找对应的原始 CSV 文件
        # 注意：这里根据你的 Original_SUB_ID 去找文件
        group_path = os.path.join(MIND_ROOT, row['Group_MIND'])
        file_pattern = os.path.join(group_path, f"{row['Original_SUB_ID']}_MIND*.csv")
        target_files = glob.glob(file_pattern)
        
        if target_files:
            f = target_files[0]
            mat_df = pd.read_csv(f, index_col=0)
            if roi_names is None: roi_names = mat_df.columns
            all_matrices.append(mat_df.values[np.triu_indices(68, k=1)])
            valid_patnos.append(row['PATNO'])
    
    # 将矩阵转为 NumPy 数组 [被试数, 2278条边]
    feature_matrix = np.array(all_matrices)
    # 仅保留矩阵和量表都能对上的被试
    df_final = df_bl[df_bl['PATNO'].isin(valid_patnos)].reset_index(drop=True)

    # 3. 逐边进行 ANCOVA 统计 (带协变量)
    print(f">>> 开始对 {feature_matrix.shape[1]} 条边进行 ANCOVA 检验...")
    f_stats = np.zeros(feature_matrix.shape[1])
    p_values = np.ones(feature_matrix.shape[1])

    for i in range(feature_matrix.shape[1]):
        # 将当前边的数值加入临时 DataFrame
        df_final['current_edge'] = feature_matrix[:, i]
        
        # 构建模型: 边强度 ~ 组别 + 年龄 + 性别 + 教育
        model = ols('current_edge ~ C(Group_MIND) + Age_at_Visit + C(Sex) + Education', data=df_final).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)
        
        f_stats[i] = anova_table.loc['C(Group_MIND)', 'F']
        p_values[i] = anova_table.loc['C(Group_MIND)', 'PR(>F)']
        
        if i % 500 == 0: print(f" 已完成 {i}/{feature_matrix.shape[1]} 条边...")

    # 4. 构建并保存 F-Matrix 结果 (未校正 p < 0.05 的作为掩模)
    print(">>> 正在生成 F-统计量空间矩阵...")
    f_map = np.zeros((68, 68))
    p_map = np.ones((68, 68))
    upper_idx = np.triu_indices(68, k=1)
    
    sig_count = 0
    for idx, p in enumerate(p_values):
        r, c = upper_idx[0][idx], upper_idx[1][idx]
        p_map[r, c] = p_map[c, r] = p
        if p < 0.05:
            f_map[r, c] = f_map[c, r] = f_stats[idx]
            sig_count += 1

    # 保存文件
    pd.DataFrame(f_map, index=roi_names, columns=roi_names).to_csv(os.path.join(OUTPUT_DIR, "ANCOVA_F_Matrix_p05.csv"))
    pd.DataFrame(p_map, index=roi_names, columns=roi_names).to_csv(os.path.join(OUTPUT_DIR, "ANCOVA_P_Matrix_Raw.csv"))

    print(f"\n>>> 分析完成！")
    print(f"在考虑协变量后，共发现 {sig_count} 条连接具有显著组间差异 (p < 0.05, uncorrected)。")
    print(f"结果已保存至: {OUTPUT_DIR}")

if __name__ == "__main__":
    run_full_brain_ancova()
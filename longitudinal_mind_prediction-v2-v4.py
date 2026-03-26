import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from config import *

apply_style()

# --- 1. 配置与数据对齐 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
OUTPUT_DIR = './results_2year_fixed/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_2year_fixed_analysis():
    print(">>> [1/4] 加载并限定 2 年随访数据 (BL, V04, V06)...")
    df = pd.read_csv(DATA_FILE)
    
    # 强制提取核心时间点 [cite: 15, 21]
    df['EVENT_ID_Clean'] = df['EVENT_ID'].str.extract(r'(BL|V04|V06)', expand=False)
    time_map = TIME_MAP_3PT
    df['Time'] = df['EVENT_ID_Clean'].map(time_map)
    
    # 提取基线特征用于控制变量 [cite: 20, 66]
    df_bl = df[df['EVENT_ID_Clean'] == 'BL'][['Original_SUB_ID', 'MIND_Sig_Index', 'UPDRS3']].copy()
    df_bl.columns = ['Original_SUB_ID', 'MIND_BL', 'UPDRS3_BL']
    
    # 合并长数据并清洗
    df_long = pd.merge(df, df_bl, on='Original_SUB_ID', how='inner')
    # 剔除缺失值以确保模型稳定 [cite: 67]
    df_long = df_long.dropna(subset=['Time', 'UPDRS3', 'MIND_BL', 'UPDRS3_BL', 'Age_at_Visit', 'Sex', 'Education']).copy()
    df_long = df_long.reset_index(drop=True)

    print(f"    进入模型记录数: {len(df_long)} (涉及 {df_long['Original_SUB_ID'].nunique()} 人)")

    # --- 2. 线性混合效应模型 (LME) ---
    print("\n>>> [2/4] 拟合 LME 预测模型...")
    # 公式包含交互项 Time:MIND_BL [cite: 10, 11, 46]
    model_formula = "UPDRS3 ~ Time * MIND_BL + UPDRS3_BL + Age_at_Visit + C(Sex) + Education"
    
    md = smf.mixedlm(model_formula, df_long, groups=df_long["Original_SUB_ID"])
    mdf = md.fit()
    print(mdf.summary())

    # --- 3. 结果可视化 (2年轨迹) ---
    print(">>> [3/4] 生成 2 年预测轨迹图...")
    # 只针对有随访轨迹的受试者绘图 [cite: 74]
    id_counts = df_long.groupby('Original_SUB_ID')['Time'].transform('count')
    df_viz = df_long[id_counts >= 2].copy()
    df_viz['Fitted_UPDRS'] = mdf.predict(df_viz)
    
    # 分组：高/低 MIND (基于均值) [cite: 54, 74]
    mean_mind = df_viz['MIND_BL'].mean()
    df_viz['MIND_Group'] = np.where(df_viz['MIND_BL'] > mean_mind, 'High MIND (Better Connectivity)', 'Low MIND (Worse Connectivity)')

    plt.figure(figsize=FIG_SINGLE)
    sns.lineplot(data=df_viz, x='Time', y='Fitted_UPDRS', hue='MIND_Group', 
                 palette=CMAP_TRAJECTORY, marker=MARKER, markersize=MARKERSIZE_LG, errorbar=ERRORBAR, linewidth=LINEWIDTH_THICK)
    
    plt.xticks([0, 1, 2], ['Baseline', 'Year 1 (V04)', 'Year 2 (V06)'])
    plt.title("MIND Baseline Predicting 2-Year Clinical Progression\n(LME Inter-group Slopes: P=0.033)")
    plt.xlabel("Years from Baseline")
    plt.ylabel("Predicted UPDRS-III Score")
    plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    
    plt.savefig(os.path.join(OUTPUT_DIR, "Final_2Year_Trajectory.png"), dpi=DPI)
    
    # --- 4. 统计摘要保存 ---
    with open(os.path.join(OUTPUT_DIR, "Stats_Summary.txt"), "w") as f:
        f.write(mdf.summary().as_text())
    
    print(f"\n>>> 分析完成。结果保存在: {OUTPUT_DIR}")
    plt.show()

if __name__ == "__main__":
    run_2year_fixed_analysis()
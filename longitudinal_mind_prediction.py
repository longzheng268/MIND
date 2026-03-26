import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from scipy import stats
from config import *

apply_style()

# --- 1. 环境配置 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
OUTPUT_DIR = './final_aligned_results/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_aligned_analysis():
    print(">>> [1/4] 正在加载并强制对齐 Excel 记录...")
    df = pd.read_csv(DATA_FILE)
    
    # 清洗 EVENT_ID
    df['EVENT_ID_Clean'] = df['EVENT_ID'].str.extract(r'(BL|V\d+)', expand=False)
    
    # 建立时间映射
    time_map = TIME_MAP_FULL
    df['Time'] = df['EVENT_ID_Clean'].map(time_map)

    # 提取基线特征 (BL)
    # 重点：我们用 PATNO 或 Original_SUB_ID 匹配。如果匹配不上，说明该受试者没有基线MIND。
    df_bl = df[df['EVENT_ID_Clean'] == 'BL'][['Original_SUB_ID', 'MIND_Sig_Index', 'UPDRS3']].copy()
    df_bl.columns = ['Original_SUB_ID', 'MIND_BL', 'UPDRS3_BL']
    
    # 合并基线到纵向数据
    df_long = pd.merge(df, df_bl, on='Original_SUB_ID', how='inner')
    
    # --- 核心修正：解决 IndexError ---
    # 1. 剔除模型所需的关键变量中的空值
    cols_to_check = ['UPDRS3', 'Time', 'MIND_BL', 'UPDRS3_BL', 'Age_at_Visit', 'Education']
    df_long = df_long.dropna(subset=cols_to_check).copy()
    
    # 2. 【最重要】重置索引，确保 index 从 0 到 N-1 连续，防止 statsmodels 越界
    df_long = df_long.reset_index(drop=True)
    
    # 3. 确保 groups 变量是字符串或分类变量，且与重置后的索引同步
    df_long['Group_ID'] = df_long['Original_SUB_ID'].astype(str)

    print(f"    Excel 原始行数: 969")
    print(f"    当前进入模型行数: {len(df_long)} (剔除了量表缺失值)")
    print(f"    随访分布:\n{df_long['EVENT_ID_Clean'].value_counts()}")

    # --- 2. 混合效应模型 ---
    print("\n>>> [2/4] 正在运行 LME 预测模型...")
    model_formula = "UPDRS3 ~ Time * MIND_BL + UPDRS3_BL + Age_at_Visit + C(Sex) + Education"
    
    # 使用重置后的数据
    md = smf.mixedlm(model_formula, df_long, groups=df_long["Group_ID"])
    mdf = md.fit()
    print(mdf.summary())

    # --- 3. 优化绘图：解决轨迹交叉 ---
    print(">>> [3/4] 生成预测轨迹图...")
    # 只针对有随访轨迹的受试者绘图，效果最清晰
    id_counts = df_long.groupby('Group_ID')['Time'].transform('count')
    df_viz = df_long[id_counts >= 2].copy()
    
    # 计算拟合值以消除基线噪音
    df_viz['Fitted_UPDRS'] = mdf.predict(df_viz)
    
    # 按 MIND 高低中分组
    df_viz['MIND_Level'] = pd.qcut(df_viz['MIND_BL'], 3, labels=['Low MIND', 'Mid MIND', 'High MIND'])

    plt.figure(figsize=FIG_SINGLE)
    sns.lineplot(data=df_viz, x='Time', y='Fitted_UPDRS', hue='MIND_Level', 
                 palette=CMAP_TRAJECTORY, marker=MARKER, errorbar=ERRORBAR, linewidth=LINEWIDTH)
    
    # 坐标轴对齐
    plt.xticks([0, 1, 2, 3, 4], ['BL', 'Y1(V04)', 'Y2(V06)', 'Y3(V08)', 'Y4(V10)'])
    plt.title("2-Year Progressive Trajectory Grouped by Baseline MIND\n(LME Fitted Values)")
    plt.ylabel("Predicted UPDRS-III Score")
    plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    
    plt.savefig(os.path.join(OUTPUT_DIR, "Final_Progressive_Trajectory.png"), dpi=DPI)
    
    # --- 4. 统计结果导出 ---
    with open(os.path.join(OUTPUT_DIR, "LME_Full_Report.txt"), "w") as f:
        f.write(mdf.summary().as_text())

    print(f"\n>>> 分析报告已导出至: {OUTPUT_DIR}")
    plt.show()

if __name__ == "__main__":
    run_aligned_analysis()
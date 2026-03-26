import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from config import *

apply_style()

# 合并自：step3a_lme_full_timepoints.py（全时间点）
#         step3b_lme_2year_updrs.py（2年 BL/V04/V06）

# --- 路径配置 ---
DATA_FILE_FULL  = './MIND_Longitudinal_Clean_Data.csv'       # 全时间点数据
OUTPUT_DIR      = './lme_updrs_results/'
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# 模型 A：全时间点 LME（BL ~ V12）
# ─────────────────────────────────────────────
def run_full_timepoints():
    """
    使用 TIME_MAP_FULL（BL/V02/.../V12）拟合 LME。
    MIND 按三分位数分为高/中/低组，绘制轨迹图。
    """
    print("\n" + "═" * 60)
    print(">>> 模型 A：全时间点 LME（BL ~ V12）")
    print("═" * 60)

    df = pd.read_csv(DATA_FILE_FULL)
    df['EVENT_ID_Clean'] = df['EVENT_ID'].str.extract(r'(BL|V\d+)', expand=False)
    df['Time'] = df['EVENT_ID_Clean'].map(TIME_MAP_FULL)

    # 提取基线特征
    df_bl = (df[df['EVENT_ID_Clean'] == 'BL']
             [['Original_SUB_ID', 'MIND_Sig_Index', 'UPDRS3']]
             .copy())
    df_bl.columns = ['Original_SUB_ID', 'MIND_BL', 'UPDRS3_BL']

    df_long = pd.merge(df, df_bl, on='Original_SUB_ID', how='inner')
    cols = ['UPDRS3', 'Time', 'MIND_BL', 'UPDRS3_BL',
            'Age_at_Visit', 'Education']
    df_long = df_long.dropna(subset=cols).reset_index(drop=True)
    df_long['Group_ID'] = df_long['Original_SUB_ID'].astype(str)

    print(f"    进入模型记录数: {len(df_long)}"
          f"（{df_long['Group_ID'].nunique()} 位受试者）")
    print(f"    时间点分布:\n{df_long['EVENT_ID_Clean'].value_counts().to_string()}")

    # LME 拟合
    formula = "UPDRS3 ~ Time * MIND_BL + UPDRS3_BL + Age_at_Visit + C(Sex) + Education"
    mdf = smf.mixedlm(formula, df_long, groups=df_long["Group_ID"]).fit()
    print(mdf.summary())

    # 可视化：MIND 三分位轨迹
    id_counts = df_long.groupby('Group_ID')['Time'].transform('count')
    df_viz = df_long[id_counts >= 2].copy()
    df_viz['Fitted_UPDRS'] = mdf.predict(df_viz)
    df_viz['MIND_Level'] = pd.qcut(
        df_viz['MIND_BL'], 3,
        labels=['Low MIND', 'Mid MIND', 'High MIND']
    )

    plt.figure(figsize=FIG_SINGLE)
    sns.lineplot(data=df_viz, x='Time', y='Fitted_UPDRS',
                 hue='MIND_Level', palette=CMAP_TRAJECTORY,
                 marker=MARKER, errorbar=ERRORBAR, linewidth=LINEWIDTH)
    plt.xticks([0, 1, 2, 3, 4],
               ['BL', 'Y1(V04)', 'Y2(V06)', 'Y3(V08)', 'Y4(V10)'])
    plt.title("Progressive Trajectory by Baseline MIND"
              "\n(Full Timepoints, LME Fitted Values)")
    plt.ylabel("Predicted UPDRS-III Score")
    plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    plt.savefig(
        os.path.join(OUTPUT_DIR, "ModelA_Full_TP_Trajectory.png"), dpi=DPI
    )
    plt.close()

    # 保存统计报告
    with open(os.path.join(OUTPUT_DIR, "ModelA_Full_TP_LME_Report.txt"), "w") as f:
        f.write(mdf.summary().as_text())

    print(f"    [A] 结果已保存至: {OUTPUT_DIR}")
    return mdf


# ─────────────────────────────────────────────
# 模型 B：2年固定随访 LME（BL / V04 / V06）
# ─────────────────────────────────────────────
def run_2year_fixed():
    """
    仅保留 BL、V04、V06 三个时间点（TIME_MAP_3PT），
    MIND 按均值二分为高/低连接组，绘制 2 年轨迹图。
    """
    print("\n" + "═" * 60)
    print(">>> 模型 B：2年固定随访 LME（BL / V04 / V06）")
    print("═" * 60)

    df = pd.read_csv(DATA_FILE_FULL)
    df['EVENT_ID_Clean'] = df['EVENT_ID'].str.extract(r'(BL|V04|V06)', expand=False)
    df['Time'] = df['EVENT_ID_Clean'].map(TIME_MAP_3PT)

    df_bl = (df[df['EVENT_ID_Clean'] == 'BL']
             [['Original_SUB_ID', 'MIND_Sig_Index', 'UPDRS3']]
             .copy())
    df_bl.columns = ['Original_SUB_ID', 'MIND_BL', 'UPDRS3_BL']

    df_long = pd.merge(df, df_bl, on='Original_SUB_ID', how='inner')
    cols = ['Time', 'UPDRS3', 'MIND_BL', 'UPDRS3_BL',
            'Age_at_Visit', 'Sex', 'Education']
    df_long = df_long.dropna(subset=cols).reset_index(drop=True)

    print(f"    进入模型记录数: {len(df_long)}"
          f"（{df_long['Original_SUB_ID'].nunique()} 位受试者）")

    # LME 拟合
    formula = "UPDRS3 ~ Time * MIND_BL + UPDRS3_BL + Age_at_Visit + C(Sex) + Education"
    mdf = smf.mixedlm(formula, df_long,
                      groups=df_long["Original_SUB_ID"]).fit()
    print(mdf.summary())

    # 可视化：MIND 均值二分轨迹
    id_counts = df_long.groupby('Original_SUB_ID')['Time'].transform('count')
    df_viz = df_long[id_counts >= 2].copy()
    df_viz['Fitted_UPDRS'] = mdf.predict(df_viz)
    mean_mind = df_viz['MIND_BL'].mean()
    df_viz['MIND_Group'] = np.where(
        df_viz['MIND_BL'] > mean_mind,
        'High MIND (Better Connectivity)',
        'Low MIND (Worse Connectivity)'
    )

    plt.figure(figsize=FIG_SINGLE)
    sns.lineplot(data=df_viz, x='Time', y='Fitted_UPDRS',
                 hue='MIND_Group', palette=CMAP_TRAJECTORY,
                 marker=MARKER, markersize=MARKERSIZE_LG,
                 errorbar=ERRORBAR, linewidth=LINEWIDTH_THICK)
    plt.xticks([0, 1, 2],
               ['Baseline', 'Year 1 (V04)', 'Year 2 (V06)'])
    plt.title("MIND Baseline Predicting 2-Year Clinical Progression"
              "\n(LME, BL/V04/V06 Fixed Timepoints)")
    plt.xlabel("Years from Baseline")
    plt.ylabel("Predicted UPDRS-III Score")
    plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    plt.savefig(
        os.path.join(OUTPUT_DIR, "ModelB_2Year_Trajectory.png"), dpi=DPI
    )
    plt.close()

    # 保存统计报告
    with open(os.path.join(OUTPUT_DIR, "ModelB_2Year_LME_Report.txt"), "w") as f:
        f.write(mdf.summary().as_text())

    print(f"    [B] 结果已保存至: {OUTPUT_DIR}")
    return mdf


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    run_full_timepoints()   # 模型 A
    run_2year_fixed()       # 模型 B
    print("\n>>> 全部 UPDRS-III LME 分析完成。")

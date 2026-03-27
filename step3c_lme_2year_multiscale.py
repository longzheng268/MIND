import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from config import *

apply_style()

# --- 1. 配置与参数 ---
DATA_FILE = './scale/MIND_Longitudinal_Clean_Data_filled.csv'
BASE_OUTPUT_DIR = './MIND_Research_Results/'
SCALES = ['UPDRS3', 'MoCA', 'GDS15_all', 'RBDSQ_all', 'NP1APAT', 'NP1FATG']

def run_research_pipeline():
    if not os.path.exists(DATA_FILE):
        print(f"找不到文件: {DATA_FILE}")
        return

    df_raw = pd.read_csv(DATA_FILE)
    
    # 时间点清洗与映射 [BL=0, V04=1, V06=2]
    df_raw['EVENT_ID_Clean'] = df_raw['EVENT_ID'].str.extract(r'(BL|V04|V06)', expand=False)
    time_map = TIME_MAP_3PT
    df_raw['Time'] = df_raw['EVENT_ID_Clean'].map(time_map)
    
    # 提取基线 MIND 网络指标
    df_bl_mind = df_raw[df_raw['EVENT_ID_Clean'] == 'BL'][['Original_SUB_ID', 'MIND_Sig_Index']].copy()
    df_bl_mind.columns = ['Original_SUB_ID', 'MIND_BL']

    for scale in SCALES:
        print(f"\n>>> 正在处理量表: {scale} ...")
        df_raw[scale] = pd.to_numeric(df_raw[scale], errors='coerce')
        scale_dir = os.path.join(BASE_OUTPUT_DIR, scale)
        os.makedirs(scale_dir, exist_ok=True)
        
        # 准备模型数据
        df_bl_score = df_raw[df_raw['EVENT_ID_Clean'] == 'BL'][['Original_SUB_ID', scale]].copy()
        df_bl_score.columns = ['Original_SUB_ID', f'{scale}_BL']
        df_long = pd.merge(df_raw, df_bl_mind, on='Original_SUB_ID', how='inner')
        df_long = pd.merge(df_long, df_bl_score, on='Original_SUB_ID', how='inner')
        
        cols_needed = [scale, 'Time', 'MIND_BL', f'{scale}_BL', 'Age_at_Visit', 'Sex', 'Education', 'Group_MIND']
        df_clean = df_long.dropna(subset=cols_needed).reset_index(drop=True)

        if len(df_clean) < 30:
            print(f"量表 {scale} 有效数据太少，跳过。")
            continue

        # 定义公式（放在 try 块外面，防止出现 UnboundLocalError）
        # Model 1: 比较四组间的斜率差异 (ref='HC')
        formula1 = f"{scale} ~ Time * C(Group_MIND, Treatment('HC')) + Age_at_Visit + C(Sex) + Education"
        # Model 2: MIND 对恶化速率的独立预测作用
        formula2 = f"{scale} ~ Time * MIND_BL + {scale}_BL + C(Group_MIND) + Age_at_Visit + C(Sex) + Education"

        try:
            # 依次尝试 LME_METHODS 中的优化器，任一成功即停止（优化器列表来自 config.py）
            mdf1 = mdf2 = None
            for _m in LME_METHODS:
                try:
                    mdf1 = smf.mixedlm(formula1, df_clean, groups=df_clean["Original_SUB_ID"]).fit(method=_m, reml=False)
                    mdf2 = smf.mixedlm(formula2, df_clean, groups=df_clean["Original_SUB_ID"]).fit(method=_m, reml=False)
                    break
                except Exception:
                    continue
            if mdf1 is None:
                raise ValueError("所有优化器均失败，转 OLS 保底")

            # --- 绘图 1: 四组轨迹 (Group Progression) ---
            plt.figure(figsize=FIG_SINGLE)
            df_clean['Fitted_G'] = mdf1.predict(df_clean)
            sns.lineplot(data=df_clean, x='Time', y='Fitted_G', hue='Group_MIND',
                         hue_order=GROUP_ORDER, palette=GROUP_PALETTE,
                         marker=MARKER, markersize=MARKERSIZE, errorbar=ERRORBAR, linewidth=LINEWIDTH)
            plt.xticks(list(TIME_MAP_3PT.values()), TIME_LABELS_3)
            plt.title(f"Figure 1: {scale} Longitudinal Trajectory by Disease Groups", fontsize=FONT_TITLE)
            plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
            plt.savefig(os.path.join(scale_dir, f"Fig1_Group_Progression.png"), dpi=DPI)
            plt.close()

            # --- 绘图 2: MIND 预测效应 ---
            m_val, s_val = df_clean['MIND_BL'].mean(), df_clean['MIND_BL'].std()
            df_viz = df_clean.copy()
            df_viz['Fitted_M'] = mdf2.predict(df_viz)
            df_viz['MIND_Level'] = np.where(df_viz['MIND_BL'] > m_val + s_val, 'High MIND (Mean+1SD)',
                                   np.where(df_viz['MIND_BL'] < m_val - s_val, 'Low MIND (Mean-1SD)', 'Mid MIND (Mean)'))
            
            plt.figure(figsize=FIG_SINGLE)
            sns.lineplot(data=df_viz, x='Time', y='Fitted_M', hue='MIND_Level', 
                         hue_order=MIND_LEVEL_ORDER,
                         palette=CMAP_TRAJECTORY, marker='s', markersize=MARKERSIZE, errorbar=ERRORBAR, linewidth=LINEWIDTH_THICK)
            plt.xticks(list(TIME_MAP_3PT.values()), TIME_LABELS_3)
            plt.title(f"Figure 2: {scale} Progression Predicted by Baseline MIND", fontsize=FONT_TITLE)
            plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
            plt.savefig(os.path.join(scale_dir, f"Fig2_MIND_Prediction.png"), dpi=DPI)
            plt.close()

            # 保存报告
            with open(os.path.join(scale_dir, f"Statistical_Report.txt"), "w") as f:
                f.write(f"--- Model 1: Group Differences ---\n{mdf1.summary().as_text()}\n\n")
                f.write(f"--- Model 2: MIND Predictive Value ---\n{mdf2.summary().as_text()}")

        except Exception as e:
            print(f"量表 {scale} LME 拟合失败: {e}。正在尝试 OLS 保底...")
            mdf_ols = smf.ols(formula2, data=df_clean).fit()
            with open(os.path.join(scale_dir, f"OLS_Backup_Report.txt"), "w") as f:
                f.write(mdf_ols.summary().as_text())

    print(f"\n>>> 所有量表分析完成！结果存放至: {BASE_OUTPUT_DIR}")

if __name__ == "__main__":
    run_research_pipeline()
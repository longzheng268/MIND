import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from config import *

apply_style()

# 1. 加载数据
df = pd.read_csv('MIND_Final_Analysis_Table.csv')

# 2. 数据清洗：定义恶化程度 (Delta)
# Delta_UPDRS3 = 随访点 - 基线 (正值越大表示恶化越严重)
df['Delta_UPDRS3_V04'] = df['V04_UPDRS3'] - df['BL_UPDRS3']
df['Delta_UPDRS3_V06'] = df['V06_UPDRS3'] - df['BL_UPDRS3']

# --- Aim 1: 四组间 MIND 指标趋势分析 ---
print("\n=== Aim 1: 组间趋势检验 ===")
group_order = GROUP_ORDER
plt.figure(figsize=FIG_SINGLE)
sns.boxplot(x='Group', y='MIND_Sig_Index', data=df, order=group_order, palette=GROUP_PALETTE)
sns.stripplot(x='Group', y='MIND_Sig_Index', data=df, order=group_order, color=STRIP_COLOR, alpha=ALPHA_STRIP)
plt.title("Degeneration of MIND Network Index across Stages")
plt.savefig('Aim1_MIND_Trend.png', dpi=DPI)
print("已生成趋势图: Aim1_MIND_Trend.png")

# --- Aim 2: 预测 1 年后 (V04) 的症状恶化 ---
print("\n=== Aim 2: 基线 MIND 指标对 1 年后运动恶化的预测 (线性回归) ===")
# 排除掉随访数据缺失的行
analysis_df = df.dropna(subset=['Delta_UPDRS3_V04', 'MIND_Sig_Index', 'BL_Age']).copy()

if len(analysis_df) > 0:
    # 回归方程：Delta_UPDRS3 ~ MIND_Sig_Index + 基线年龄 + 基线得分 (控制变量)
    model = smf.ols('Delta_UPDRS3_V04 ~ MIND_Sig_Index + BL_Age + BL_UPDRS3', data=analysis_df).fit()
    print(model.summary())
    
    # 可视化相关性
    plt.figure(figsize=FIG_SMALL)
    sns.regplot(x='MIND_Sig_Index', y='Delta_UPDRS3_V04', data=analysis_df)
    plt.xlabel('Baseline MIND Sig Index')
    plt.ylabel('1-Year UPDRS-III Increase (V04 - BL)')
    plt.title('MIND Index Predicts Clinical Progression')
    plt.savefig('Aim2_MIND_Prediction.png', dpi=DPI)
else:
    print(" [!] 警告：缺乏有效的 V04 随访匹配数据，请检查量表表。")

# --- Aim 3: 增量价值 (MIND vs SAA) ---
print("\n=== Aim 3: MIND 对比 SAA 的预测增量价值 (似然比检验) ===")
# 只有 PD 和 Prodromal 参与恶化预测，排除 HC
prog_df = analysis_df[analysis_df['Group'] != 'HC'].copy()
if len(prog_df) > 0:
    # 模型 1: 仅 SAA 状态
    m1 = smf.ols('Delta_UPDRS3_V04 ~ SAA_Status + BL_Age + BL_UPDRS3', data=prog_df).fit()
    # 模型 2: SAA 状态 + MIND 指标
    m2 = smf.ols('Delta_UPDRS3_V04 ~ SAA_Status + MIND_Sig_Index + BL_Age + BL_UPDRS3', data=prog_df).fit()
    
    print(f"Model 1 (SAA only) R-squared: {m1.rsquared:.4f}")
    print(f"Model 2 (SAA + MIND) R-squared: {m2.rsquared:.4f}")
    print(f"MIND 带来的解释度提升: {(m2.rsquared - m1.rsquared)*100:.2f}%")

plt.show()
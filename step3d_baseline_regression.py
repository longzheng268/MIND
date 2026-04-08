import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from config import *

apply_style()

MIN_AIM3_NON_HC_N = 12
MIN_AIM3_RESID_DF = 5
PREVIEW_PLOTS = True


def _get_endpoint_map():
    return {endpoint['event']: endpoint for endpoint in STEP3D_REGRESSION_ENDPOINTS}


def _plot_group_delta_boxline(analysis_df, endpoint):
    event = endpoint['event']
    label = endpoint['label']
    suffix = endpoint['suffix']
    delta_col = f'Delta_UPDRS3_{event}'

    fig, ax = plt.subplots(figsize=FIG_SINGLE)
    sns.boxplot(
        x='Group',
        y=delta_col,
        data=analysis_df,
        order=GROUP_ORDER,
        palette=GROUP_PALETTE,
        hue='Group',
        dodge=False,
        legend=False,
        showfliers=False,
        ax=ax,
    )
    sns.stripplot(
        x='Group',
        y=delta_col,
        data=analysis_df,
        order=GROUP_ORDER,
        color=STRIP_COLOR,
        alpha=ALPHA_STRIP,
        size=STRIP_SIZE,
        ax=ax,
    )
    ax.axhline(0, color=COLOR_REF_LINE, linestyle='--', linewidth=LINEWIDTH_THIN)
    ax.set_xlabel('')
    ax.set_ylabel(f'UPDRS-III Change ({label})', fontsize=FONT_AXIS)
    ax.set_title(f'Figure 1: Clinical Progression by Group ({label})', fontsize=FONT_TITLE)
    ax.tick_params(axis='x', labelrotation=15)
    ax.grid(True, axis='y', linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    fig.savefig(f'Aim2_Group_Delta_Boxplot_{suffix}.png', dpi=DPI)
    print(f"已生成图一: Aim2_Group_Delta_Boxplot_{suffix}.png")
    return fig



def _plot_mind_regression_line(analysis_df, endpoint):
    event = endpoint['event']
    label = endpoint['label']
    suffix = endpoint['suffix']
    delta_col = f'Delta_UPDRS3_{event}'

    fig, ax = plt.subplots(figsize=FIG_SINGLE)
    sns.regplot(
        x='MIND_Sig_Index',
        y=delta_col,
        data=analysis_df,
        scatter_kws={'color': STRIP_COLOR, 'alpha': ALPHA_STRIP, 's': STRIP_SIZE * 14},
        line_kws={'color': GROUP_COLORS[2], 'linewidth': LINEWIDTH_THICK},
        ax=ax,
    )
    ax.axhline(0, color=COLOR_REF_LINE, linestyle='--', linewidth=LINEWIDTH_THIN)
    ax.set_xlabel('Baseline MIND Sig Index', fontsize=FONT_AXIS)
    ax.set_ylabel(f'UPDRS-III Change ({label})', fontsize=FONT_AXIS)
    ax.set_title(f'Figure 2: MIND Index Predicts Clinical Progression ({label})', fontsize=FONT_TITLE)
    ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    fig.savefig(f'Aim2_MIND_Prediction_{suffix}.png', dpi=DPI)
    print(f"已生成图二: Aim2_MIND_Prediction_{suffix}.png")
    return fig



def _fit_incremental_models(prog_df, delta_col, event):
    n_samples = len(prog_df)
    saa_nunique = prog_df['SAA_Status'].nunique(dropna=True)
    n_predictors_m2 = 4

    if n_samples < MIN_AIM3_NON_HC_N:
        print(f" [!] 跳过 Aim 3 [{event}]：非 HC 样本仅 {n_samples} 例，低于最小阈值 {MIN_AIM3_NON_HC_N}。")
        return None, None

    if saa_nunique < 2:
        print(f" [!] 跳过 Aim 3 [{event}]：`SAA_Status` 在非 HC 子样本中缺乏变异。")
        return None, None

    if n_samples - (n_predictors_m2 + 1) < MIN_AIM3_RESID_DF:
        print(
            f" [!] 跳过 Aim 3 [{event}]：非 HC 子样本剩余自由度不足，"
            f"n={n_samples}, 预测变量={n_predictors_m2}, resid_df<{MIN_AIM3_RESID_DF}。"
        )
        return None, None

    m1 = smf.ols(f'{delta_col} ~ SAA_Status + BL_Age + BL_UPDRS3', data=prog_df).fit()
    m2 = smf.ols(f'{delta_col} ~ SAA_Status + MIND_Sig_Index + BL_Age + BL_UPDRS3', data=prog_df).fit()

    if m1.df_resid <= 0 or m2.df_resid <= 0:
        print(f" [!] 跳过 Aim 3 [{event}]：模型残差自由度 <= 0，结果不可靠。")
        return None, None

    return m1, m2


# 1. 加载数据
df_long = pd.read_csv('./scale/MIND_baseline_with_followup_V04_V12.csv')
updrs_col = 'UPDRSIII' if 'UPDRSIII' in df_long.columns else 'UPDRS3'
endpoint_map = _get_endpoint_map()
preview_figs = []

# 2. 从长表整理基线宽表
base_cols = ['Original_SUB_ID', 'SAA_Status', 'Group_MIND', 'MIND_Sig_Index', 'Age_at_Visit', updrs_col]
df_bl = (df_long[df_long['EVENT_ID'] == BL_EVENT][base_cols]
         .copy()
         .rename(columns={
             'Group_MIND': 'Group',
             'Age_at_Visit': 'BL_Age',
             updrs_col: 'BL_UPDRS3'
         }))

df = df_bl.copy()
for endpoint in STEP3D_REGRESSION_ENDPOINTS:
    event = endpoint['event']
    df_fu = (df_long[df_long['EVENT_ID'] == event][['Original_SUB_ID', updrs_col]]
             .copy()
             .rename(columns={updrs_col: f'{event}_UPDRS3'}))
    df = df.merge(df_fu, on='Original_SUB_ID', how='left')
    df[f'Delta_UPDRS3_{event}'] = df[f'{event}_UPDRS3'] - df['BL_UPDRS3']

# --- Aim 1: 四组间 MIND 指标趋势分析 ---
print("\n=== Aim 1: 组间趋势检验 ===")
fig_aim1, ax_aim1 = plt.subplots(figsize=FIG_SINGLE)
sns.boxplot(
    x='Group',
    y='MIND_Sig_Index',
    data=df,
    order=GROUP_ORDER,
    palette=GROUP_PALETTE,
    hue='Group',
    dodge=False,
    legend=False,
    showfliers=False,
    ax=ax_aim1,
)
sns.stripplot(
    x='Group',
    y='MIND_Sig_Index',
    data=df,
    order=GROUP_ORDER,
    color=STRIP_COLOR,
    alpha=ALPHA_STRIP,
    size=STRIP_SIZE,
    ax=ax_aim1,
)
ax_aim1.set_xlabel('')
ax_aim1.set_ylabel('Baseline MIND Sig Index', fontsize=FONT_AXIS)
ax_aim1.set_title('Figure 0: Degeneration of MIND Network Index across Stages', fontsize=FONT_TITLE)
ax_aim1.tick_params(axis='x', labelrotation=15)
ax_aim1.grid(True, axis='y', linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
fig_aim1.savefig('Aim1_MIND_Trend.png', dpi=DPI)
print("已生成趋势图: Aim1_MIND_Trend.png")
preview_figs.append(fig_aim1)

# --- Aim 2 & Aim 3: 多终点回归预测 ---
for event in STEP3D_PRIMARY_ENDPOINTS:
    endpoint = endpoint_map[event]
    label = endpoint['label']
    delta_col = f'Delta_UPDRS3_{event}'

    print(f"\n=== {event} 组：{label} ===")
    analysis_df = df.dropna(subset=[delta_col, 'MIND_Sig_Index', 'BL_Age', 'BL_UPDRS3']).copy()
    print(f"匹配样本数 ({event}): {len(analysis_df)}")

    if len(analysis_df) == 0:
        print(f" [!] 警告：缺乏有效的 {event} 随访匹配数据，请检查量表表。")
        continue

    preview_figs.append(_plot_group_delta_boxline(analysis_df, endpoint))
    preview_figs.append(_plot_mind_regression_line(analysis_df, endpoint))

    print(f"\n=== Aim 2: 基线 MIND 指标对 {event} 症状恶化的预测 (线性回归) ===")
    model = smf.ols(f'{delta_col} ~ MIND_Sig_Index + BL_Age + BL_UPDRS3', data=analysis_df).fit()
    print(model.summary())

    print("\n=== Aim 3: MIND 对比 SAA 的预测增量价值 (似然比检验) ===")
    prog_df = analysis_df[analysis_df['Group'] != 'HC'].copy()
    if len(prog_df) == 0:
        print(f" [!] 警告：{event} 无足够 PD/Prodromal 样本用于增量价值分析。")
        continue

    m1, m2 = _fit_incremental_models(prog_df, delta_col, event)
    if m1 is None or m2 is None:
        continue

    print(f"Model 1 (SAA only) R-squared [{event}]: {m1.rsquared:.4f}")
    print(f"Model 2 (SAA + MIND) R-squared [{event}]: {m2.rsquared:.4f}")
    print(f"MIND 带来的解释度提升 [{event}]: {(m2.rsquared - m1.rsquared)*100:.2f}%")

if PREVIEW_PLOTS and preview_figs:
    plt.show(block=True)
else:
    for fig in preview_figs:
        plt.close(fig)

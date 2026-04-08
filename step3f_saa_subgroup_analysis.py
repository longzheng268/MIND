import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from config import *

apply_style()

# --- SAA 亚组敏感性分析 ---
# 分析 1：BL MIND SAA+ vs SAA- 组间差异（ANCOVA + 箱线图）
# 分析 2：SAA 状态对临床量表变化速率的调节（LME）
# 复用研究方案第五节"亚组敏感性"策略

DATA_FILE       = './scale/MIND_baseline_with_followup_V04_V12.csv'
BASE_OUTPUT_DIR = './MIND_Research_Results/'
PREVIEW_PLOTS   = True
TIMELINE_CONFIGS = [
    {
        'key': 'full',
        'time_map': TIME_MAP_FULL,
        'time_labels': TIME_LABELS_FULL,
        'window_title': TIME_WINDOW_FULL_TITLE,
        'window_label': TIME_WINDOW_FULL_LABEL,
        'suffix': 'FullTimeline',
    },
    {
        'key': '2year',
        'time_map': TIME_MAP_3PT,
        'time_labels': TIME_LABELS_3,
        'window_title': TIME_WINDOW_3PT_TITLE,
        'window_label': TIME_WINDOW_3PT_LABEL,
        'suffix': '2Year',
    },
]

# 7 网络 + 全局 MIND 指标
MIND_COLS = [
    'MIND_Sig_Index', 'MIND_Visual', 'MIND_Somatomotor',
    'MIND_Dorsal_Attention', 'MIND_Ventral_Attention',
    'MIND_Limbic', 'MIND_Frontoparietal', 'MIND_Default',
]

# 指标英文子图标题（避免中文字体缺失）
MIND_SHORT = {
    'MIND_Sig_Index':       'Global MIND',
    'MIND_Visual':          'Visual',
    'MIND_Somatomotor':     'Somatomotor',
    'MIND_Dorsal_Attention':'Dorsal Attention',
    'MIND_Ventral_Attention':'Ventral Attention',
    'MIND_Limbic':          'Limbic',
    'MIND_Frontoparietal':  'Frontoparietal',
    'MIND_Default':         'Default',
}

# LME 分析的量表
LME_SCALES = ['MoCA', 'UPDRS3']
SCALE_COLUMN_ALIASES = {
    'MoCA': ['MoCA'],
    'UPDRS3': ['UPDRS3', 'UPDRSIII', 'UPDRSIII.1'],
}


def _get_scale_col(df, scale):
    for col in SCALE_COLUMN_ALIASES.get(scale, [scale]):
        if col in df.columns:
            return col
    raise KeyError(f"未找到量表列: {scale}")


# BL 基线评分列名映射
BL_SCALE_MAP = {'MoCA': 'MoCA', 'UPDRS3': 'UPDRS3'}


def _fit_lme(formula, data, groups_col):
    """三级降级 LME 拟合（复用 step3c 框架，跳过 lbfgs 避免卡死）。"""
    for _re in [LME_RE_FORMULA, None]:
        for _m in ['powell', 'nm', 'bfgs']:
            try:
                _kw = {'re_formula': _re} if _re else {}
                return smf.mixedlm(
                    formula, data,
                    groups=data[groups_col], **_kw
                ).fit(method=_m, reml=False, maxiter=100)
            except Exception:
                continue
    raise ValueError("所有优化器均失败，转 OLS 保底")


def _get_plot_df(df_clean, timeline_cfg, scale):
    if timeline_cfg['key'] != 'full':
        return df_clean.copy(), timeline_cfg['time_map'], timeline_cfg['time_labels']

    visit_counts = df_clean['EVENT_ID_Clean'].value_counts()
    kept_events = [event for event in TIMEPOINTS_FULL if visit_counts.get(event, 0) >= STEP3_FULL_MIN_PLOT_N]
    if kept_events != TIMEPOINTS_FULL:
        dropped = [event for event in TIMEPOINTS_FULL if event not in kept_events]
        print(f"    [{scale}][{timeline_cfg['suffix']}] 可视化最小样本阈值={STEP3_FULL_MIN_PLOT_N}，不绘制: {dropped}")
    kept_map = {event: TIME_MAP_FULL[event] for event in kept_events}
    kept_labels = [TIME_LABELS_FULL[TIMEPOINTS_FULL.index(event)] for event in kept_events]
    return df_clean[df_clean['EVENT_ID_Clean'].isin(kept_events)].copy(), kept_map, kept_labels


def _plot_saa_trajectory(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels):
    fig, ax = plt.subplots(figsize=FIG_SINGLE)
    saa_palette = {'Negative': '#66c2a5', 'Positive': '#fc8d62'}
    sns.lineplot(data=df_plot, x='Time', y='Fitted_G',
                 hue='SAA_Status',
                 palette=saa_palette,
                 marker=MARKER, markersize=MARKERSIZE,
                 errorbar=ERRORBAR, linewidth=LINEWIDTH,
                 ax=ax)
    ticks, labels = get_time_ticks_and_labels(tick_map, tick_labels)
    ax.set_xticks(ticks, labels, rotation=30 if timeline_cfg['key'] == 'full' else 0)
    ax.set_title(
        f"SAA Subgroup: {scale} Longitudinal Trajectory\n"
        f"(SAA+ vs SAA-, {timeline_cfg['window_title']}, Model 1)",
        fontsize=FONT_TITLE,
    )
    ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    fig.savefig(os.path.join(scale_dir, f"Fig1_SAA_Trajectory_{timeline_cfg['suffix']}.png"), dpi=DPI)
    return fig


def _plot_mind_prediction(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels):
    m_val, s_val = df_plot['MIND_BL'].mean(), df_plot['MIND_BL'].std()
    df_viz = df_plot.copy()
    df_viz['MIND_Level'] = np.where(
        df_viz['MIND_BL'] > m_val + s_val, MIND_LEVEL_ORDER[0],
        np.where(df_viz['MIND_BL'] < m_val - s_val, MIND_LEVEL_ORDER[2],
                 MIND_LEVEL_ORDER[1])
    )

    fig, ax = plt.subplots(figsize=FIG_SINGLE)
    sns.lineplot(data=df_viz, x='Time', y='Fitted_M',
                 hue='MIND_Level', hue_order=MIND_LEVEL_ORDER,
                 palette=CMAP_TRAJECTORY,
                 marker='s', markersize=MARKERSIZE,
                 errorbar=ERRORBAR, linewidth=LINEWIDTH_THICK,
                 ax=ax)
    ticks, labels = get_time_ticks_and_labels(tick_map, tick_labels)
    ax.set_xticks(ticks, labels, rotation=30 if timeline_cfg['key'] == 'full' else 0)
    ax.set_title(
        f"SAA Subgroup: {scale} Progression Predicted by Baseline MIND\n"
        f"({timeline_cfg['window_title']}, Model 2)",
        fontsize=FONT_TITLE,
    )
    ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    fig.savefig(os.path.join(scale_dir, f"Fig2_MIND_Prediction_{timeline_cfg['suffix']}.png"), dpi=DPI)
    return fig


def run_analysis1_bl_ancova():
    """分析 1：BL 时间点，SAA+ vs SAA- 的 MIND 指标组间差异。"""
    print("\n" + "="*60)
    print("分析 1：BL MIND SAA+ vs SAA- 组间差异（ANCOVA）")
    print("="*60)

    if not os.path.exists(DATA_FILE):
        print(f"找不到文件: {DATA_FILE}")
        return

    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == 'BL'].copy()

    # 仅取 prodromal SAA+ 和 SAA-（不含 HC 和 PD）
    df_bl = df_bl[df_bl['SAA_Status'].isin(['Positive', 'Negative'])].copy()
    df_bl['SAA_Status'] = pd.Categorical(
        df_bl['SAA_Status'], categories=['Negative', 'Positive'], ordered=True
    )

    print(f"  SAA+ (Positive): {(df_bl['SAA_Status']=='Positive').sum()}")
    print(f"  SAA- (Negative): {(df_bl['SAA_Status']=='Negative').sum()}")

    out_dir = os.path.join(BASE_OUTPUT_DIR, 'SAA_subgroup_BL')
    os.makedirs(out_dir, exist_ok=True)

    # 转为长格式方便画图
    results = []
    plot_data = []

    for col in MIND_COLS:
        df_col = df_bl[['SAA_Status', col, 'Age_at_Visit', 'Sex', 'Education']].dropna()
        if len(df_col) < 20:
            print(f"  {col}: 数据不足({len(df_col)})，跳过")
            continue

        # ANCOVA
        model = ols(f"{col} ~ C(SAA_Status) + Age_at_Visit + C(Sex) + Education",
                    data=df_col).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)
        p_val = anova_table.loc['C(SAA_Status)', 'PR(>F)']
        f_val = anova_table.loc['C(SAA_Status)', 'F']

        # Welch t-test（稳健性检验）
        pos_vals = df_col[df_col['SAA_Status'] == 'Positive'][col]
        neg_vals = df_col[df_col['SAA_Status'] == 'Negative'][col]
        t_result = sm.stats.ttest_ind(pos_vals, neg_vals, usevar='unequal')
        t_stat, p_ttest = t_result[0], t_result[1]

        # Cohen's d
        pooled_std = np.sqrt(((len(pos_vals)-1)*pos_vals.std()**2 +
                              (len(neg_vals)-1)*neg_vals.std()**2) /
                             (len(pos_vals)+len(neg_vals)-2))
        cohens_d = (pos_vals.mean() - neg_vals.mean()) / pooled_std if pooled_std > 0 else 0

        results.append({
            'MIND指标': col,
            '英文名': MIND_SHORT.get(col, col),
            'SAA+均值': pos_vals.mean(),
            'SAA-均值': neg_vals.mean(),
            'ANCOVA_F': f_val,
            'ANCOVA_p': p_val,
            'Welch_t': t_stat,
            'Welch_p': p_ttest,
            'Cohens_d': cohens_d,
        })

        for _, row in df_col.iterrows():
            plot_data.append({'MIND指标': MIND_SHORT.get(col, col), 'SAA_Status': row['SAA_Status'],
                              col: row[col]})

    # FDR 校正
    res_df = pd.DataFrame(results)
    if len(res_df) > 0:
        res_df['ANCOVA_p_fdr'] = multipletests(res_df['ANCOVA_p'], method='fdr_bh')[1]
        res_df.to_csv(os.path.join(out_dir, 'SAA_BL_ANCOVA_Results.csv'), index=False)
        print(f"\n  ANCOVA 结果（已 FDR 校正）:")
        print(res_df[['英文名', 'SAA+均值', 'SAA-均值', 'ANCOVA_F', 'ANCOVA_p', 'ANCOVA_p_fdr', 'Cohens_d']].to_string(index=False))

    # 箱线图：8 个子图
    n_metrics = len(MIND_COLS)
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()

    for i, col in enumerate(MIND_COLS):
        ax = axes[i]
        df_col = df_bl[['SAA_Status', col]].dropna()
        if len(df_col) < 20:
            ax.set_visible(False)
            continue

        sns.boxplot(x='SAA_Status', y=col, data=df_col, ax=ax,
                    palette={'Negative': '#66c2a5', 'Positive': '#fc8d62'},
                    hue='SAA_Status', legend=False, order=['Negative', 'Positive'])
        sns.stripplot(x='SAA_Status', y=col, data=df_col, ax=ax,
                      color=STRIP_COLOR, alpha=ALPHA_STRIP, size=4,
                      order=['Negative', 'Positive'])

        ax.set_title(MIND_SHORT.get(col, col), fontsize=11)
        ax.set_xlabel('')
        ax.set_ylabel('MIND Strength')
        ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)

        # 标注 p 值
        p_row = res_df[res_df['MIND指标'] == col]
        if len(p_row) > 0:
            p_str = f"p={p_row['ANCOVA_p_fdr'].values[0]:.3f}"
            if p_row['ANCOVA_p_fdr'].values[0] < 0.05:
                p_str += ' *'
            ax.text(0.5, 0.95, p_str, transform=ax.transAxes,
                    ha='center', va='top', fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.suptitle('BL MIND Network Strength: SAA+ vs SAA-\n(prodromal subgroup, ANCOVA adjusted)',
                 fontsize=FONT_SUPTITLE)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'Fig1_SAA_BL_Boxplots.png'), dpi=DPI)
    plt.close()
    print(f"\n  箱线图已保存至: {out_dir}/Fig1_SAA_BL_Boxplots.png")


def _run_single_timeline(df_source, timeline_cfg, preview_figs):
    df_raw = add_time_from_event(df_source.copy(), timeline_cfg['time_map'])

    df_bl_mind = (df_raw[df_raw['EVENT_ID_Clean'] == BL_EVENT]
                  [['Original_SUB_ID', 'MIND_Sig_Index']].copy())
    df_bl_mind.columns = ['Original_SUB_ID', 'MIND_BL']

    df_sub = df_raw[df_raw['SAA_Status'].isin(['Positive', 'Negative'])].copy()
    df_sub['SAA_Status'] = pd.Categorical(
        df_sub['SAA_Status'], categories=['Negative', 'Positive'], ordered=True
    )

    for scale in LME_SCALES:
        print(f"\n  >>> 正在处理量表: {scale} [{timeline_cfg['window_title']}] ...")
        scale_col = _get_scale_col(df_sub, scale)
        df_sub[scale_col] = pd.to_numeric(df_sub[scale_col], errors='coerce')
        bl_col = _get_scale_col(df_raw, BL_SCALE_MAP[scale])

        df_bl_score = (df_raw[(df_raw['EVENT_ID_Clean'] == BL_EVENT) &
                              (df_raw['SAA_Status'].isin(['Positive', 'Negative']))]
                       [['Original_SUB_ID', bl_col]].copy())
        df_bl_score.columns = ['Original_SUB_ID', f'{scale}_BL']

        df_long = pd.merge(df_sub, df_bl_mind, on='Original_SUB_ID', how='inner')
        df_long = pd.merge(df_long, df_bl_score, on='Original_SUB_ID', how='inner')
        df_long[scale] = df_long[scale_col]

        cols_needed = [scale, 'Time', 'MIND_BL', f'{scale}_BL',
                       'Age_at_Visit', 'Sex', 'Education', 'SAA_Status']
        df_clean = df_long.dropna(subset=cols_needed).reset_index(drop=True)

        if len(df_clean) < 30:
            print(f"    有效数据不足({len(df_clean)})，跳过。")
            continue

        print(f"    有效样本: {len(df_clean)} 行, {df_clean['Original_SUB_ID'].nunique()} 人")
        print(f"    SAA+: {(df_clean['SAA_Status']=='Positive').sum()} 行")
        print(f"    SAA-: {(df_clean['SAA_Status']=='Negative').sum()} 行")

        scale_dir = os.path.join(BASE_OUTPUT_DIR, 'SAA_subgroup_lme', scale)
        os.makedirs(scale_dir, exist_ok=True)

        formula1 = (f"{scale} ~ Time * C(SAA_Status)"
                    f" + Age_at_Visit + C(Sex) + Education")
        formula2 = (f"{scale} ~ Time * C(SAA_Status)"
                    f" + Time * MIND_BL + {scale}_BL"
                    f" + Age_at_Visit + C(Sex) + Education")

        summary_path = os.path.join(scale_dir, f"Statistical_Summary_{timeline_cfg['suffix']}.txt")

        try:
            mdf1 = _fit_lme(formula1, df_clean, 'Original_SUB_ID')
            mdf2 = _fit_lme(formula2, df_clean, 'Original_SUB_ID')
            print(f"    [{timeline_cfg['suffix']}] LME 拟合完成，结果已保存。")

            df_clean['Fitted_G'] = mdf1.predict(df_clean)
            df_clean['Fitted_M'] = mdf2.predict(df_clean)
            df_plot, tick_map, tick_labels = _get_plot_df(df_clean, timeline_cfg, scale)
            if len(df_plot) > 0:
                preview_figs.append(_plot_saa_trajectory(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels))
                preview_figs.append(_plot_mind_prediction(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels))

            sk = 'Time:MIND_BL'
            slope_line = ""
            if sk in mdf2.params:
                beta = mdf2.params[sk]
                se = mdf2.bse[sk]
                pval = mdf2.pvalues[sk]
                ci_lo, ci_hi = beta - 1.96 * se, beta + 1.96 * se
                print(f"    [简单斜率] Time:MIND_BL  β={beta:.3f}  "
                      f"95%CI=[{ci_lo:.3f},{ci_hi:.3f}]  p={pval:.3f}")
                slope_line = (f"SIMPLE SLOPE (Time:MIND_BL):\n"
                              f"  β={beta:.4f}  SE={se:.4f}  "
                              f"95%CI=[{ci_lo:.4f},{ci_hi:.4f}]  p={pval:.4f}\n")

            sk_saa = 'Time:C(SAA_Status)[T.Positive]'
            saa_line = ""
            if sk_saa in mdf1.params:
                beta = mdf1.params[sk_saa]
                se = mdf1.bse[sk_saa]
                pval = mdf1.pvalues[sk_saa]
                ci_lo, ci_hi = beta - 1.96 * se, beta + 1.96 * se
                print(f"    [SAA 交互] Time:SAA_Status(Positive)  β={beta:.3f}  "
                      f"95%CI=[{ci_lo:.3f},{ci_hi:.3f}]  p={pval:.3f}")
                saa_line = (f"SAA INTERACTION (Time:SAA_Status Positive vs Negative):\n"
                            f"  β={beta:.4f}  SE={se:.4f}  "
                            f"95%CI=[{ci_lo:.4f},{ci_hi:.4f}]  p={pval:.4f}\n")

            with open(summary_path, 'w') as f:
                f.write(f"TIMELINE: {timeline_cfg['window_title']} ({timeline_cfg['window_label']})\n\n")
                f.write("MODEL 1: SAA SUBGROUP TRAJECTORY DIFFERENCES (ref=Negative)\n")
                f.write(mdf1.summary().as_text() + "\n\n")
                f.write(saa_line + "\n")
                f.write("MODEL 2: MIND INDEPENDENT PREDICTION (CONTROLLED FOR SAA)\n")
                f.write(mdf2.summary().as_text() + "\n\n")
                f.write(slope_line)

        except Exception as e:
            print(f"    LME 拟合失败，将自动切换 OLS 保底: {e}")
            mdf_ols = smf.ols(formula2, data=df_clean).fit()
            with open(os.path.join(scale_dir, f"OLS_Backup_Report_{timeline_cfg['suffix']}.txt"), 'w') as f:
                f.write(f"TIMELINE: {timeline_cfg['window_title']} ({timeline_cfg['window_label']})\n\n")
                f.write(mdf_ols.summary().as_text())

            df_clean['Fitted_G'] = mdf_ols.predict(df_clean)
            df_clean['Fitted_M'] = mdf_ols.predict(df_clean)
            df_plot, tick_map, tick_labels = _get_plot_df(df_clean, timeline_cfg, scale)
            if len(df_plot) > 0:
                preview_figs.append(_plot_saa_trajectory(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels))
                preview_figs.append(_plot_mind_prediction(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels))


def run_analysis2_saa_lme():
    """分析 2：SAA 状态对临床量表变化速率的调节（LME）。"""
    print("\n" + "="*60)
    print("分析 2：SAA 状态调节临床变化速率（LME）")
    print("="*60)

    if not os.path.exists(DATA_FILE):
        print(f"找不到文件: {DATA_FILE}")
        return

    df_source = pd.read_csv(DATA_FILE)
    preview_figs = []
    for timeline_cfg in TIMELINE_CONFIGS:
        _run_single_timeline(df_source, timeline_cfg, preview_figs)

    if PREVIEW_PLOTS and preview_figs:
        plt.show(block=True)
    else:
        for fig in preview_figs:
            plt.close(fig)

    print(f"\n>>> SAA 亚组分析完成！结果存放至: {BASE_OUTPUT_DIR}")


if __name__ == "__main__":
    run_analysis1_bl_ancova()
    run_analysis2_saa_lme()

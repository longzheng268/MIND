import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from config import *

apply_style()

# 分析框架来源：research_design_lme_mind.md
# 参数（优化器、随机效应公式、图幅、颜色等）全部来自 config.py

# --- 路径与量表列表 ---
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
# 所有量表统一循环处理（研究设计第六节）
SCALES = ['UPDRS3', 'MoCA', 'GDS15_all', 'RBDSQ_all', 'NP1APAT', 'NP1FATG']
SCALE_COLUMN_ALIASES = {
    'UPDRS3': ['UPDRS3', 'UPDRSIII', 'UPDRSIII.1'],
}


def _get_scale_col(df, scale):
    for col in SCALE_COLUMN_ALIASES.get(scale, [scale]):
        if col in df.columns:
            return col
    raise KeyError(f"未找到量表列: {scale}")


def _fit_lme(formula, data, groups_col):
    """
    三级降级 LME 拟合（参数来自 config.py）：
      ① LME_RE_FORMULA（随机截距+斜率）
      ② None（仅随机截距）
      ③ 均失败则抛出异常，由上层 except 接管 OLS 保底
    """
    for _re in [LME_RE_FORMULA, None]:
        for _m in LME_METHODS:
            try:
                _kw = {'re_formula': _re} if _re else {}
                return smf.mixedlm(
                    formula, data,
                    groups=data[groups_col], **_kw
                ).fit(method=_m, reml=False)
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


def _plot_group_progression(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels):
    fig, ax = plt.subplots(figsize=FIG_SINGLE)
    sns.lineplot(data=df_plot, x='Time', y='Fitted_G',
                 hue='Group_MIND', hue_order=GROUP_ORDER,
                 palette=GROUP_PALETTE,
                 marker=MARKER, markersize=MARKERSIZE,
                 errorbar=ERRORBAR, linewidth=LINEWIDTH,
                 ax=ax)
    ticks, labels = get_time_ticks_and_labels(tick_map, tick_labels)
    ax.set_xticks(ticks, labels, rotation=30 if timeline_cfg['key'] == 'full' else 0)
    ax.set_title(
        f"Figure 1: {scale} Longitudinal Trajectory by Disease Groups\n"
        f"({timeline_cfg['window_title']})",
        fontsize=FONT_TITLE,
    )
    ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    fig.savefig(os.path.join(scale_dir, f"Fig1_Group_Progression_{timeline_cfg['suffix']}.png"), dpi=DPI)
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
        f"Figure 2: {scale} Progression Predicted by Baseline MIND\n"
        f"({timeline_cfg['window_title']})",
        fontsize=FONT_TITLE,
    )
    ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    fig.savefig(os.path.join(scale_dir, f"Fig2_MIND_Prediction_{timeline_cfg['suffix']}.png"), dpi=DPI)
    return fig


def _run_single_timeline(df_source, scale, scale_dir, timeline_cfg, preview_figs):
    df_raw = add_time_from_event(df_source.copy(), timeline_cfg['time_map'])

    df_bl_mind = (df_raw[df_raw['EVENT_ID_Clean'] == BL_EVENT]
                  [['Original_SUB_ID', 'MIND_Sig_Index']]
                  .copy())
    df_bl_mind.columns = ['Original_SUB_ID', 'MIND_BL']

    scale_col = _get_scale_col(df_raw, scale)
    df_raw[scale_col] = pd.to_numeric(df_raw[scale_col], errors='coerce')

    df_bl_score = (df_raw[df_raw['EVENT_ID_Clean'] == BL_EVENT]
                   [['Original_SUB_ID', scale_col]]
                   .copy())
    df_bl_score.columns = ['Original_SUB_ID', f'{scale}_BL']
    df_long = pd.merge(df_raw, df_bl_mind, on='Original_SUB_ID', how='inner')
    df_long = pd.merge(df_long, df_bl_score, on='Original_SUB_ID', how='inner')
    df_long[scale] = df_long[scale_col]

    cols_needed = [scale, 'Time', 'MIND_BL', f'{scale}_BL',
                   'Age_at_Visit', 'Sex', 'Education', 'Group_MIND']
    df_clean = df_long.dropna(subset=cols_needed).reset_index(drop=True)
    df_clean['Group_MIND'] = pd.Categorical(
        df_clean['Group_MIND'], categories=GROUP_ORDER, ordered=True
    )

    if len(df_clean) < 30:
        print(f"  {scale} [{timeline_cfg['window_title']}] 有效数据不足({len(df_clean)})，跳过。")
        return

    print(f"  {scale} [{timeline_cfg['window_title']}]: {len(df_clean)} 行, {df_clean['Original_SUB_ID'].nunique()} 人")

    formula1 = (f"{scale} ~ Time * C(Group_MIND, Treatment('HC'))"
                f" + Age_at_Visit + C(Sex) + Education")
    formula2 = (f"{scale} ~ Time * C(Group_MIND, Treatment('HC'))"
                f" + Time * MIND_BL"
                f" + {scale}_BL + Age_at_Visit + C(Sex) + Education")

    summary_path = os.path.join(scale_dir, f"Statistical_Summary_{timeline_cfg['suffix']}.txt")

    try:
        mdf1 = _fit_lme(formula1, df_clean, 'Original_SUB_ID')
        mdf2 = _fit_lme(formula2, df_clean, 'Original_SUB_ID')
        print(f"    [{timeline_cfg['suffix']}] LME 拟合完成，结果已保存。")

        df_clean['Fitted_G'] = mdf1.predict(df_clean)
        df_clean['Fitted_M'] = mdf2.predict(df_clean)
        df_plot, tick_map, tick_labels = _get_plot_df(df_clean, timeline_cfg, scale)
        if len(df_plot) > 0:
            preview_figs.append(_plot_group_progression(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels))
            preview_figs.append(_plot_mind_prediction(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels))

        sk = 'Time:MIND_BL'
        slope_line = ""
        if sk in mdf2.params:
            beta = mdf2.params[sk]
            se = mdf2.bse[sk]
            pval = mdf2.pvalues[sk]
            ci_lo, ci_hi = beta - 1.96 * se, beta + 1.96 * se
            print(f"    [{timeline_cfg['suffix']}] [简单斜率] Time:MIND_BL  β={beta:.3f}  "
                  f"95%CI=[{ci_lo:.3f},{ci_hi:.3f}]  p={pval:.3f}")
            slope_line = (f"SIMPLE SLOPE (Time:MIND_BL):\n"
                          f"  β={beta:.4f}  SE={se:.4f}  "
                          f"95%CI=[{ci_lo:.4f},{ci_hi:.4f}]  p={pval:.4f}\n")

        with open(summary_path, 'w') as f:
            f.write(f"TIMELINE: {timeline_cfg['window_title']} ({timeline_cfg['window_label']})\n\n")
            f.write("MODEL 1: GROUP TRAJECTORY DIFFERENCES (REF=HC)\n")
            f.write(mdf1.summary().as_text() + "\n\n")
            f.write("MODEL 2: MIND INDEPENDENT PREDICTION (CONTROLLED FOR GROUP)\n")
            f.write(mdf2.summary().as_text() + "\n\n")
            f.write(slope_line)

    except Exception as e:
        print(f"  {scale} [{timeline_cfg['window_title']}] LME 拟合失败，将自动切换 OLS 保底: {e}")
        mdf_ols = smf.ols(formula2, data=df_clean).fit()
        with open(os.path.join(scale_dir, f"OLS_Backup_Report_{timeline_cfg['suffix']}.txt"), 'w') as f:
            f.write(f"TIMELINE: {timeline_cfg['window_title']} ({timeline_cfg['window_label']})\n\n")
            f.write(mdf_ols.summary().as_text())

        df_clean['Fitted_G'] = mdf_ols.predict(df_clean)
        df_clean['Fitted_M'] = mdf_ols.predict(df_clean)
        df_plot, tick_map, tick_labels = _get_plot_df(df_clean, timeline_cfg, scale)
        if len(df_plot) > 0:
            preview_figs.append(_plot_group_progression(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels))
            preview_figs.append(_plot_mind_prediction(df_plot, scale, scale_dir, timeline_cfg, tick_map, tick_labels))


def run_research_pipeline():
    if not os.path.exists(DATA_FILE):
        print(f"找不到文件: {DATA_FILE}")
        return

    df_source = pd.read_csv(DATA_FILE)
    preview_figs = []

    for scale in SCALES:
        print(f"\n>>> 正在处理量表: {scale} ...")
        scale_dir = os.path.join(BASE_OUTPUT_DIR, scale)
        os.makedirs(scale_dir, exist_ok=True)

        for timeline_cfg in TIMELINE_CONFIGS:
            _run_single_timeline(df_source, scale, scale_dir, timeline_cfg, preview_figs)

    if PREVIEW_PLOTS and preview_figs:
        plt.show(block=True)
    else:
        for fig in preview_figs:
            plt.close(fig)

    print(f"\n>>> 所有量表分析完成！结果存放至: {BASE_OUTPUT_DIR}")


if __name__ == "__main__":
    run_research_pipeline()

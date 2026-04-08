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


def run_research_pipeline():
    if not os.path.exists(DATA_FILE):
        print(f"找不到文件: {DATA_FILE}")
        return

    df_raw = add_time_from_event(pd.read_csv(DATA_FILE), TIME_MAP_3PT)

    # 提取基线 MIND 指标（独立预测因子）
    df_bl_mind = (df_raw[df_raw['EVENT_ID_Clean'] == BL_EVENT]
                  [['Original_SUB_ID', 'MIND_Sig_Index']]
                  .copy())
    df_bl_mind.columns = ['Original_SUB_ID', 'MIND_BL']

    for scale in SCALES:
        print(f"\n>>> 正在处理量表: {scale} ...")
        scale_col = _get_scale_col(df_raw, scale)
        df_raw[scale_col] = pd.to_numeric(df_raw[scale_col], errors='coerce')
        scale_dir = os.path.join(BASE_OUTPUT_DIR, scale)
        os.makedirs(scale_dir, exist_ok=True)

        # 准备长格式数据：合并基线评分作为协变量（控制基线起点差异）
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
            print(f"量表 {scale} 有效数据不足，跳过。")
            continue

        # ── 双模型公式（研究设计文档 §三） ──────────────────────────────────
        # 模型1：检验四组纵向轨迹差异（参照组 HC）
        formula1 = (f"{scale} ~ Time * C(Group_MIND, Treatment('HC'))"
                    f" + Age_at_Visit + C(Sex) + Education")
        # 模型2：控制分组后，MIND 对变化速率的独立预测（核心创新）
        formula2 = (f"{scale} ~ Time * C(Group_MIND, Treatment('HC'))"
                    f" + Time * MIND_BL"
                    f" + {scale}_BL + Age_at_Visit + C(Sex) + Education")

        try:
            mdf1 = _fit_lme(formula1, df_clean, 'Original_SUB_ID')
            mdf2 = _fit_lme(formula2, df_clean, 'Original_SUB_ID')

            # ── 图1：四组纵向轨迹（模型1预测值）────────────────────────────
            # GROUP_PALETTE / GROUP_ORDER / TIME_LABELS_3 均来自 config.py
            plt.figure(figsize=FIG_SINGLE)
            df_clean['Fitted_G'] = mdf1.predict(df_clean)
            sns.lineplot(data=df_clean, x='Time', y='Fitted_G',
                         hue='Group_MIND', hue_order=GROUP_ORDER,
                         palette=GROUP_PALETTE,
                         marker=MARKER, markersize=MARKERSIZE,
                         errorbar=ERRORBAR, linewidth=LINEWIDTH)
            ticks_3pt, labels_3pt = get_time_ticks_and_labels(TIME_MAP_3PT, TIME_LABELS_3)
            plt.xticks(ticks_3pt, labels_3pt)
            plt.title(f"Figure 1: {scale} Longitudinal Trajectory by Disease Groups",
                      fontsize=FONT_TITLE)
            plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
            plt.savefig(os.path.join(scale_dir, "Fig1_Group_Progression.png"), dpi=DPI)
            plt.close()

            # ── 图2：MIND 均值±1SD 三水平预测轨迹（模型2）────────────────────
            # MIND_LEVEL_ORDER / CMAP_TRAJECTORY / LINEWIDTH_THICK 均来自 config.py
            m_val, s_val = df_clean['MIND_BL'].mean(), df_clean['MIND_BL'].std()
            df_viz = df_clean.copy()
            df_viz['Fitted_M'] = mdf2.predict(df_viz)
            df_viz['MIND_Level'] = np.where(
                df_viz['MIND_BL'] > m_val + s_val, MIND_LEVEL_ORDER[0],
                np.where(df_viz['MIND_BL'] < m_val - s_val, MIND_LEVEL_ORDER[2],
                         MIND_LEVEL_ORDER[1])
            )
            plt.figure(figsize=FIG_SINGLE)
            sns.lineplot(data=df_viz, x='Time', y='Fitted_M',
                         hue='MIND_Level', hue_order=MIND_LEVEL_ORDER,
                         palette=CMAP_TRAJECTORY,
                         marker='s', markersize=MARKERSIZE,
                         errorbar=ERRORBAR, linewidth=LINEWIDTH_THICK)
            ticks_3pt, labels_3pt = get_time_ticks_and_labels(TIME_MAP_3PT, TIME_LABELS_3)
            plt.xticks(ticks_3pt, labels_3pt)
            plt.title(f"Figure 2: {scale} Progression Predicted by Baseline MIND",
                      fontsize=FONT_TITLE)
            plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
            plt.savefig(os.path.join(scale_dir, "Fig2_MIND_Prediction.png"), dpi=DPI)
            plt.close()

            # ── 简单斜率摘要（Time:MIND_BL 系数）────────────────────────────
            sk = 'Time:MIND_BL'
            slope_line = ""
            if sk in mdf2.params:
                beta  = mdf2.params[sk]
                se    = mdf2.bse[sk]
                pval  = mdf2.pvalues[sk]
                ci_lo, ci_hi = beta - 1.96 * se, beta + 1.96 * se
                print(f"    [简单斜率] Time:MIND_BL  β={beta:.3f}  "
                      f"95%CI=[{ci_lo:.3f},{ci_hi:.3f}]  p={pval:.3f}")
                slope_line = (f"SIMPLE SLOPE (Time:MIND_BL):\n"
                              f"  β={beta:.4f}  SE={se:.4f}  "
                              f"95%CI=[{ci_lo:.4f},{ci_hi:.4f}]  p={pval:.4f}\n")

            # ── 保存统计报告 ──────────────────────────────────────────────────
            with open(os.path.join(scale_dir, "Statistical_Summary.txt"), 'w') as f:
                f.write(f"MODEL 1: GROUP TRAJECTORY DIFFERENCES (REF=HC)\n")
                f.write(mdf1.summary().as_text() + "\n\n")
                f.write(f"MODEL 2: MIND INDEPENDENT PREDICTION (CONTROLLED FOR GROUP)\n")
                f.write(mdf2.summary().as_text() + "\n\n")
                f.write(slope_line)

        except Exception as e:
            print(f"量表 {scale} LME 拟合失败: {e}，执行 OLS 保底...")
            mdf_ols = smf.ols(formula2, data=df_clean).fit()
            with open(os.path.join(scale_dir, "OLS_Backup_Report.txt"), 'w') as f:
                f.write(mdf_ols.summary().as_text())

    print(f"\n>>> 所有量表分析完成！结果存放至: {BASE_OUTPUT_DIR}")


if __name__ == "__main__":
    run_research_pipeline()

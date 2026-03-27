import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from config import *

apply_style()

# 在 step3c_lme_2year_multiscale.py 框架基础上扩展，纳入 5 个新量表：
#   ESS_all（嗜睡）、SCOPA_AUT_all（自主神经障碍）、
#   S-AI（状态焦虑）、T-AI（特质焦虑）、UPSIT_PRCNTGE（嗅觉）
# 其中 S-AI / T-AI 含特殊字符（-），patsy 需用 Q() 包裹
# 临床意义：帕金森病非运动症状 & 精神症状评估

DATA_FILE       = './scale/MIND_Longitudinal_Clean_Data_filled.csv'
BASE_OUTPUT_DIR = './MIND_Research_Results/'
SCALES = ['ESS_all', 'SCOPA_AUT_all', 'S-AI', 'T-AI', 'UPSIT_PRCNTGE']

# 量表中文对照（报告用）
SCALE_NAMES = {
    'ESS_all':       '嗜睡量表 (Epworth Sleepiness Scale)',
    'SCOPA_AUT_all': '自主神经障碍问卷 (SCOPA-AUT)',
    'S-AI':          '状态焦虑 (State Anxiety Inventory)',
    'T-AI':          '特质焦虑 (Trait Anxiety Inventory)',
    'UPSIT_PRCNTGE': '嗅觉功能 (UPSIT 百分比)',
}


def _safe_col(name):
    """将列名转为 patsy 安全形式（含 - 等特殊字符时用 Q() 包裹）。"""
    if any(c in name for c in '- + ~ | * / % ^ ! @ # $ &'.split()):
        return f'Q("{name}")'
    return name


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


def run_extended_pipeline():
    if not os.path.exists(DATA_FILE):
        print(f"找不到文件: {DATA_FILE}")
        return

    df_raw = pd.read_csv(DATA_FILE)

    # 时间点清洗与映射（TIME_MAP_3PT 来自 config.py）
    df_raw['EVENT_ID_Clean'] = df_raw['EVENT_ID'].str.extract(r'(BL|V04|V06)', expand=False)
    df_raw['Time'] = df_raw['EVENT_ID_Clean'].map(TIME_MAP_3PT)

    # 提取基线 MIND 指标
    df_bl_mind = (df_raw[df_raw['EVENT_ID_Clean'] == 'BL']
                  [['Original_SUB_ID', 'MIND_Sig_Index']]
                  .copy())
    df_bl_mind.columns = ['Original_SUB_ID', 'MIND_BL']

    for scale in SCALES:
        cn_name = SCALE_NAMES.get(scale, scale)
        print(f"\n>>> 正在处理量表: {cn_name} ...")
        df_raw[scale] = pd.to_numeric(df_raw[scale], errors='coerce')
        scale_dir = os.path.join(BASE_OUTPUT_DIR, scale)
        os.makedirs(scale_dir, exist_ok=True)

        # 合并基线评分作为协变量（控制基线起点差异）
        df_bl_score = (df_raw[df_raw['EVENT_ID_Clean'] == 'BL']
                       [['Original_SUB_ID', scale]]
                       .copy())
        df_bl_score.columns = ['Original_SUB_ID', f'{scale}_BL']
        df_long = pd.merge(df_raw, df_bl_mind, on='Original_SUB_ID', how='inner')
        df_long = pd.merge(df_long, df_bl_score, on='Original_SUB_ID', how='inner')

        cols_needed = [scale, 'Time', 'MIND_BL', f'{scale}_BL',
                       'Age_at_Visit', 'Sex', 'Education', 'Group_MIND']
        df_clean = df_long.dropna(subset=cols_needed).reset_index(drop=True)
        df_clean['Group_MIND'] = pd.Categorical(
            df_clean['Group_MIND'], categories=GROUP_ORDER, ordered=True
        )

        if len(df_clean) < 30:
            print(f"  有效数据不足({len(df_clean)})，跳过。")
            continue

        # patsy 安全列名
        y   = _safe_col(scale)
        ybl = _safe_col(f'{scale}_BL')

        # 双模型公式（与 step3c 完全一致，仅列名加了安全转义）
        formula1 = (f"{y} ~ Time * C(Group_MIND, Treatment('HC'))"
                    f" + Age_at_Visit + C(Sex) + Education")
        formula2 = (f"{y} ~ Time * C(Group_MIND, Treatment('HC'))"
                    f" + Time * MIND_BL"
                    f" + {ybl} + Age_at_Visit + C(Sex) + Education")

        try:
            f1 = build_formula1(y, ybl)
            f2 = build_formula2(y, ybl)
            mdf1 = _fit_lme(f1, df_clean, 'Original_SUB_ID')
            mdf2 = _fit_lme(f2, df_clean, 'Original_SUB_ID')

            # 图1：四组纵向轨迹（模型1预测值）
            plt.figure(figsize=FIG_SINGLE)
            df_clean['Fitted_G'] = mdf1.predict(df_clean)
            sns.lineplot(data=df_clean, x='Time', y='Fitted_G',
                         hue='Group_MIND', hue_order=GROUP_ORDER,
                         palette=GROUP_PALETTE,
                         marker=MARKER, markersize=MARKERSIZE,
                         errorbar=ERRORBAR, linewidth=LINEWIDTH)
            plt.xticks(list(TIME_MAP_3PT.values()), TIME_LABELS_3)
            plt.title(f"Figure 1: {cn_name}\nLongitudinal Trajectory by Disease Groups",
                      fontsize=FONT_TITLE)
            plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
            plt.savefig(os.path.join(scale_dir, "Fig1_Group_Progression.png"), dpi=DPI)
            plt.close()

            # 图2：MIND 均值±1SD 三水平预测轨迹（模型2）
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
            plt.xticks(list(TIME_MAP_3PT.values()), TIME_LABELS_3)
            plt.title(f"Figure 2: {cn_name}\nProgression Predicted by Baseline MIND",
                      fontsize=FONT_TITLE)
            plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
            plt.savefig(os.path.join(scale_dir, "Fig2_MIND_Prediction.png"), dpi=DPI)
            plt.close()

            # 简单斜率摘要（Time:MIND_BL 系数）
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

            # 保存统计报告
            with open(os.path.join(scale_dir, "Statistical_Summary.txt"), 'w') as f:
                f.write(f"MODEL 1: GROUP TRAJECTORY DIFFERENCES (REF=HC)\n")
                f.write(mdf1.summary().as_text() + "\n\n")
                f.write(f"MODEL 2: MIND INDEPENDENT PREDICTION (CONTROLLED FOR GROUP)\n")
                f.write(mdf2.summary().as_text() + "\n\n")
                f.write(slope_line)

        except Exception as e:
            print(f"  LME 拟合失败: {e}，执行 OLS 保底...")
            mdf_ols = smf.ols(formula2, data=df_clean).fit()
            with open(os.path.join(scale_dir, "OLS_Backup_Report.txt"), 'w') as f:
                f.write(mdf_ols.summary().as_text())

    print(f"\n>>> 5个新量表分析完成！结果存放至: {BASE_OUTPUT_DIR}")


if __name__ == "__main__":
    run_extended_pipeline()

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
# 修订说明：
#   - 补充双模型结构（模型1组间轨迹 + 模型2 MIND 独立预测），符合常规 LME 分析范式
#   - 两个模型均加入 C(Group_MIND) 控制疾病阶段，避免 Time:MIND_BL 被组间差异混淆
#   - 随机效应采用三级降级：① 随机截距+斜率 → ② 仅随机截距 → ③ 报错
#   - 优化器列表与随机效应公式统一由 config.py 控制

# --- 路径配置 ---
DATA_FILE = './MIND_Longitudinal_Clean_Data.csv'
OUTPUT_DIR = './lme_updrs_results/'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _fit_lme(formula, data, groups_col):
    """
    三级降级拟合 LME：
      ① re_formula=LME_RE_FORMULA（随机截距+斜率）
      ② re_formula=None（仅随机截距）
      ③ 均失败时抛出异常
    优化器顺序来自 config.LME_METHODS。
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
    raise RuntimeError(f"所有优化器均失败，公式: {formula}")


# ─────────────────────────────────────────────
# 模型 A：全时间点 LME（BL ~ V12）
# ─────────────────────────────────────────────
def run_full_timepoints():
    """
    使用 TIME_MAP_FULL（BL/V02/.../V12）拟合双模型：
      模型1：检验四组间 UPDRS-III 纵向轨迹差异
      模型2：控制分组后，基线 MIND 对 UPDRS-III 变化速率的独立预测
    """
    print("\n" + "═" * 60)
    print(">>> 模型 A：全时间点 LME（BL ~ V12）")
    print("═" * 60)

    df = pd.read_csv(DATA_FILE)
    df['EVENT_ID_Clean'] = df['EVENT_ID'].str.extract(r'(BL|V\d+)', expand=False)
    df['Time'] = df['EVENT_ID_Clean'].map(TIME_MAP_FULL)

    df_bl = (df[df['EVENT_ID_Clean'] == 'BL']
             [['Original_SUB_ID', 'MIND_Sig_Index', 'UPDRS3']]
             .copy())
    df_bl.columns = ['Original_SUB_ID', 'MIND_BL', 'UPDRS3_BL']

    df_long = pd.merge(df, df_bl, on='Original_SUB_ID', how='inner')
    cols = ['UPDRS3', 'Time', 'MIND_BL', 'UPDRS3_BL',
            'Age_at_Visit', 'Education', 'Group_MIND']
    df_long = df_long.dropna(subset=cols).reset_index(drop=True)
    df_long['Group_MIND'] = pd.Categorical(
        df_long['Group_MIND'], categories=GROUP_ORDER, ordered=True
    )
    df_long['Group_ID'] = df_long['Original_SUB_ID'].astype(str)

    print(f"    进入模型记录数: {len(df_long)}"
          f"（{df_long['Group_ID'].nunique()} 位受试者）")

    # 模型1：四组轨迹差异（参照组 HC）
    f_m1 = ("UPDRS3 ~ Time * C(Group_MIND, Treatment('HC'))"
             " + UPDRS3_BL + Age_at_Visit + C(Sex) + Education")
    # 模型2：在控制分组的基础上，MIND 对恶化速率的独立预测
    f_m2 = ("UPDRS3 ~ Time * C(Group_MIND, Treatment('HC'))"
             " + Time * MIND_BL"
             " + UPDRS3_BL + Age_at_Visit + C(Sex) + Education")

    mdf1 = _fit_lme(f_m1, df_long, 'Group_ID')
    mdf2 = _fit_lme(f_m2, df_long, 'Group_ID')

    print("── 模型1（四组轨迹差异）──")
    print(mdf1.summary())
    print("── 模型2（MIND 独立预测）──")
    print(mdf2.summary())

    # 可视化：用模型2预测值，按 MIND 均值±1SD 分三组
    id_counts = df_long.groupby('Group_ID')['Time'].transform('count')
    df_viz = df_long[id_counts >= 2].copy()
    df_viz['Fitted_UPDRS'] = mdf2.predict(df_viz)
    m_val, s_val = df_viz['MIND_BL'].mean(), df_viz['MIND_BL'].std()
    df_viz['MIND_Level'] = pd.cut(
        df_viz['MIND_BL'],
        bins=[-np.inf, m_val - s_val, m_val + s_val, np.inf],
        labels=[MIND_LEVEL_ORDER[2], MIND_LEVEL_ORDER[1], MIND_LEVEL_ORDER[0]]
    )

    plt.figure(figsize=FIG_SINGLE)
    sns.lineplot(data=df_viz, x='Time', y='Fitted_UPDRS',
                 hue='MIND_Level', hue_order=MIND_LEVEL_ORDER,
                 palette=CMAP_TRAJECTORY,
                 marker=MARKER, errorbar=ERRORBAR, linewidth=LINEWIDTH)
    plt.xticks([0, 1, 2, 3, 4],
               ['BL', 'Y1(V04)', 'Y2(V06)', 'Y3(V08)', 'Y4(V10)'])
    plt.title("UPDRS-III Progressive Trajectory by Baseline MIND"
              "\n(Full Timepoints, LME Model 2 Fitted Values)")
    plt.ylabel("Predicted UPDRS-III Score (↑ = Worse Motor Function)")
    plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    plt.savefig(os.path.join(OUTPUT_DIR, "ModelA_Full_TP_Trajectory.png"), dpi=DPI)
    plt.close()

    # 保存双模型报告
    with open(os.path.join(OUTPUT_DIR, "ModelA_Full_TP_LME_Report.txt"), 'w') as f:
        f.write("MODEL 1: GROUP TRAJECTORY DIFFERENCES (REF=HC)\n")
        f.write(mdf1.summary().as_text() + "\n\n")
        f.write("MODEL 2: MIND INDEPENDENT PREDICTION (CONTROLLED FOR GROUP)\n")
        f.write(mdf2.summary().as_text())

    print(f"    [A] 结果已保存至: {OUTPUT_DIR}")
    return mdf1, mdf2


# ─────────────────────────────────────────────
# 模型 B：2年固定随访 LME（BL / V04 / V06）
# ─────────────────────────────────────────────
def run_2year_fixed():
    """
    仅保留 BL、V04、V06 三个时间点（TIME_MAP_3PT），
    同样拟合双模型结构，可视化采用 MIND 均值±1SD 三水平分组。
    """
    print("\n" + "═" * 60)
    print(">>> 模型 B：2年固定随访 LME（BL / V04 / V06）")
    print("═" * 60)

    df = pd.read_csv(DATA_FILE)
    df['EVENT_ID_Clean'] = df['EVENT_ID'].str.extract(r'(BL|V04|V06)', expand=False)
    df['Time'] = df['EVENT_ID_Clean'].map(TIME_MAP_3PT)

    df_bl = (df[df['EVENT_ID_Clean'] == 'BL']
             [['Original_SUB_ID', 'MIND_Sig_Index', 'UPDRS3']]
             .copy())
    df_bl.columns = ['Original_SUB_ID', 'MIND_BL', 'UPDRS3_BL']

    df_long = pd.merge(df, df_bl, on='Original_SUB_ID', how='inner')
    cols = ['Time', 'UPDRS3', 'MIND_BL', 'UPDRS3_BL',
            'Age_at_Visit', 'Sex', 'Education', 'Group_MIND']
    df_long = df_long.dropna(subset=cols).reset_index(drop=True)
    df_long['Group_MIND'] = pd.Categorical(
        df_long['Group_MIND'], categories=GROUP_ORDER, ordered=True
    )

    print(f"    进入模型记录数: {len(df_long)}"
          f"（{df_long['Original_SUB_ID'].nunique()} 位受试者）")

    f_m1 = ("UPDRS3 ~ Time * C(Group_MIND, Treatment('HC'))"
             " + UPDRS3_BL + Age_at_Visit + C(Sex) + Education")
    f_m2 = ("UPDRS3 ~ Time * C(Group_MIND, Treatment('HC'))"
             " + Time * MIND_BL"
             " + UPDRS3_BL + Age_at_Visit + C(Sex) + Education")

    mdf1 = _fit_lme(f_m1, df_long, 'Original_SUB_ID')
    mdf2 = _fit_lme(f_m2, df_long, 'Original_SUB_ID')

    print("── 模型1（四组轨迹差异）──")
    print(mdf1.summary())
    print("── 模型2（MIND 独立预测）──")
    print(mdf2.summary())

    # 简单斜率摘要（Time:MIND_BL）
    sk = 'Time:MIND_BL'
    if sk in mdf2.params:
        beta = mdf2.params[sk]
        se   = mdf2.bse[sk]
        pval = mdf2.pvalues[sk]
        ci_lo, ci_hi = beta - 1.96 * se, beta + 1.96 * se
        print(f"    [简单斜率] Time:MIND_BL  β={beta:.3f}  "
              f"95%CI=[{ci_lo:.3f},{ci_hi:.3f}]  p={pval:.3f}")

    # 可视化：MIND 均值±1SD 三水平
    id_counts = df_long.groupby('Original_SUB_ID')['Time'].transform('count')
    df_viz = df_long[id_counts >= 2].copy()
    df_viz['Fitted_UPDRS'] = mdf2.predict(df_viz)
    m_val, s_val = df_viz['MIND_BL'].mean(), df_viz['MIND_BL'].std()
    df_viz['MIND_Level'] = np.where(
        df_viz['MIND_BL'] > m_val + s_val, MIND_LEVEL_ORDER[0],
        np.where(df_viz['MIND_BL'] < m_val - s_val, MIND_LEVEL_ORDER[2],
                 MIND_LEVEL_ORDER[1])
    )

    plt.figure(figsize=FIG_SINGLE)
    sns.lineplot(data=df_viz, x='Time', y='Fitted_UPDRS',
                 hue='MIND_Level', hue_order=MIND_LEVEL_ORDER,
                 palette=CMAP_TRAJECTORY,
                 marker=MARKER, markersize=MARKERSIZE_LG,
                 errorbar=ERRORBAR, linewidth=LINEWIDTH_THICK)
    plt.xticks(list(TIME_MAP_3PT.values()), TIME_LABELS_3)
    plt.title("MIND Baseline Predicting 2-Year UPDRS-III Progression"
              "\n(LME Model 2, BL/V04/V06 Fixed Timepoints)")
    plt.xlabel("Years from Baseline")
    plt.ylabel("Predicted UPDRS-III Score (↑ = Worse Motor Function)")
    plt.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    plt.savefig(os.path.join(OUTPUT_DIR, "ModelB_2Year_Trajectory.png"), dpi=DPI)
    plt.close()

    with open(os.path.join(OUTPUT_DIR, "ModelB_2Year_LME_Report.txt"), 'w') as f:
        f.write("MODEL 1: GROUP TRAJECTORY DIFFERENCES (REF=HC)\n")
        f.write(mdf1.summary().as_text() + "\n\n")
        f.write("MODEL 2: MIND INDEPENDENT PREDICTION (CONTROLLED FOR GROUP)\n")
        f.write(mdf2.summary().as_text() + "\n\n")
        if sk in mdf2.params:
            f.write(f"SIMPLE SLOPE (Time:MIND_BL):\n"
                    f"  β={beta:.4f}  SE={se:.4f}  "
                    f"95%CI=[{ci_lo:.4f},{ci_hi:.4f}]  p={pval:.4f}\n")

    print(f"    [B] 结果已保存至: {OUTPUT_DIR}")
    return mdf1, mdf2


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    run_full_timepoints()
    run_2year_fixed()
    print("\n>>> 全部 UPDRS-III LME 分析完成。")

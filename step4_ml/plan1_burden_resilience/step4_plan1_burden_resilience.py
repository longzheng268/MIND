"""
Step 4 Plan 1: SAA+ burden-resilience + AHBA 机制注释
=====================================================

本脚本实现 Aim 3 的完整分析框架（对应论文 4.4.1–4.6 节），包含五大模块：

模块 1 — MIND burden score 构建（4.4.1）
    将分散的脑网络异常指标收束为单一负荷表型。
    优先使用 Step2 已有效应量加权的 HC 参照 z-score 复合分数，
    降级方案为 PCA 第一主成分。
    含 bootstrap 95% CI 评估 burden score 的稳定性。

模块 2 — 阶段表达分析（4.4.2）
    在 SAA+ 人群内部比较 prodromal/SAA+ 与 PD/SAA+，
    检验 MIND burden 是否与临床显化阶段相关。
    使用 logistic 回归，输出 odds ratio + forest plot。

模块 3 — 临床韧性构建（4.4.3）
    在给定 burden 和协变量（Age/Sex/Education/LEDD/NHY）条件下，
    取 studentized residuals 作为 resilience 表型。
    含 Spearman 单调性检验作为必要前提验证。

模块 4 — 纵向验证与高风险表型（4.4.4）
    使用 MixedLM 检验 Time×Burden 和 Time×Resilience 交互，
    验证 burden/resilience 对纵向进展的预测。
    基于 burden×resilience 中位数划分四象限高风险表型。
    含 four-quadrant scatter plot 和 spaghetti plot。

模块 5 — AHBA/PLS 机制注释（4.4.5）
    AHBA + Desikan-Killiany atlas 对齐 → PLS 回归 →
    半球保持置换 spatial null → 通路/细胞类型富集。
    含 LODO 敏感性分析、GO-BP dot plot、cnet plot。

探索性分析（4.5）
    PD/SAA- discordant biology 组的描述性分析。

质量控制（4.6）
    影像质控、稳健性分析、缺失处理、多重比较、空间统计。

输出目录：./MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/
运行环境：conda activate mind
"""

import json
import os
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径，确保可以导入 config 和 step4_ml 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import nibabel as nib
from scipy.stats import fisher_exact, pearsonr
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from nilearn import plotting
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

# abagen: Allen Human Brain Atlas 数据接口，用于获取区域基因表达数据
import abagen

from config import *
from step4_ml.step4_ml_shared import (
    CLINICAL_COVARS,       # 临床协变量列表: Age_at_Visit, Sex, Education, LEDD_Baseline, NHY
    DEMOGRAPHIC_COLS,      # 人口学变量: Age_at_Visit, Sex, Education
    SAA_BURDEN_COLS,       # 备选 burden 特征列（当 Step2 结果不可用时的降级方案）
    alias_scale_column,    # 量表列名别名映射（兼容 UPDRS3/UPDRSIII/UPDRSIII.1）
    coerce_numeric,        # 将指定列强制转换为数值类型
    encode_binary_columns, # 编码二值列（Sex, SAA_Status）
    ensure_dir,            # 确保目录存在
    get_saa_positive_table,# 获取 SAA+ 人群的基线数据表
    load_raw_dataframe,    # 加载原始 CSV 数据
    zscore_frame,          # 对指定列做 z-score 标准化
)


def _enforce_global_plot_style():
    """强制应用全局绘图样式（config.py 中定义的统一风格）"""
    apply_style()


_enforce_global_plot_style()

# ============================================================
# 全局配置常量
# ============================================================

DATA_FILE = './scale/MIND_baseline_with_followup_V04_V12.csv'  # 主数据文件路径
BASE_OUTPUT_DIR = './MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/'  # 输出根目录
RANDOM_STATE = 42  # 随机种子，确保结果可重复

# 主要分析的目标量表：运动（UPDRS3）和认知（MoCA）
TARGET_SCALES = ['UPDRS3', 'MoCA']

# 环境变量控制的开关
PREVIEW_PLOTS = os.getenv('STEP4_PLAN1_PREVIEW', '1') == '1'           # 是否预览图
PLAN1_UNIFIED_PREVIEW = os.getenv('STEP4_PLAN1_UNIFIED_PREVIEW', '1') == '1'  # 是否生成统一预览图
PLAN1_ALLEN_ENABLE = os.getenv('STEP4_PLAN1_ALLEN_ENABLE', '1') == '1'  # 是否启用 AHBA 机制注释

# AHBA 相关配置
PLAN1_ALLEN_GENE_GROUP = os.getenv('STEP4_PLAN1_ALLEN_GENE_GROUP', 'brain').strip() or 'brain'
PLAN1_ALLEN_DONORS_ENV = os.getenv('STEP4_AHBA_DONORS', 'all')  # 捐赠者选择：'all' 或逗号分隔 ID
PLAN1_AHBA_CACHE_DIR = os.getenv('STEP4_AHBA_CACHE_DIR', './data/external/allen/cache/abagen')  # AHBA 缓存目录
PLAN1_AHBA_LOCAL_EXPRESSION = os.getenv(
    'STEP4_AHBA_LOCAL_EXPRESSION',
    './data/external/allen/expression/AHBA_Brain_Expression.csv',
).strip()  # 本地表达矩阵备用路径

# PLS 分析参数
PLAN1_PLS_N_PERM = max(50, int(os.getenv('STEP4_PLAN1_PLS_N_PERM', '200')))    # 空间 null 置换次数
PLAN1_PLS_TOP_N = max(10, int(os.getenv('STEP4_PLAN1_PLS_TOP_N', '40')))       # 富集分析取 top N 基因
PLAN1_PLS_N_COMPONENTS = max(1, int(os.getenv('STEP4_PLAN1_PLS_N_COMPONENTS', '1')))  # PLS 成分数

# Allen 数据目录结构
ALLEN_ROOT_DIR = './data/external/allen/'
ALLEN_ATLAS_DIR = os.path.join(ALLEN_ROOT_DIR, 'atlas')
ALLEN_EXPRESSION_DIR = os.path.join(ALLEN_ROOT_DIR, 'expression')
ALLEN_DERIVED_DIR = os.path.join(ALLEN_ROOT_DIR, 'derived')

PLAN1_CELLTYPE_MARKERS = {
    'Excitatory neuron': {
        'SLC17A7', 'SLC17A6', 'CAMK2A', 'CAMK2B', 'GRIA1', 'GRIA2', 'GRIN1', 'GRIN2A', 'RBFOX1', 'RBFOX3',
    },
    'Inhibitory neuron': {
        'GAD1', 'GAD2', 'SLC6A1', 'SLC32A1', 'DLX1', 'DLX2', 'LHX6', 'PVALB', 'SST', 'VIP',
    },
    'Astrocyte': {
        'GFAP', 'AQP4', 'ALDH1L1', 'SLC1A2', 'SLC1A3', 'GLUL', 'SOX9', 'S100B',
    },
    'Microglia': {
        'P2RY12', 'CX3CR1', 'TREM2', 'TYROBP', 'AIF1', 'C1QA', 'C1QB', 'C1QC', 'CSF1R',
    },
    'Oligodendrocyte': {
        'MBP', 'MOG', 'PLP1', 'MAG', 'MOBP', 'CLDN11', 'OLIG1', 'OLIG2', 'SOX10',
    },
    'OPC': {
        'PDGFRA', 'CSPG4', 'VCAN', 'NG2', 'OLIG1', 'OLIG2', 'SOX10', 'NKX2-2',
    },
    'Endothelial': {
        'PECAM1', 'VWF', 'KDR', 'CLDN5', 'EMCN', 'RAMP2', 'FLT1', 'ESAM',
    },
}

PLAN1_PATHWAY_THEMES = {
    'Synaptic / Vesicle': {
        'SYN1', 'SYN2', 'SYP', 'SNAP25', 'STX1A', 'STXBP1', 'VAMP2', 'SYT1', 'DLG4', 'CAMK2A', 'CAMK2B',
    },
    'Mitochondrial OXPHOS': {
        'NDUFA1', 'NDUFA2', 'NDUFA3', 'NDUFA4', 'NDUFB5', 'SDHA', 'UQCRC1', 'UQCRC2', 'COX4I1', 'ATP5F1A',
    },
    'Proteostasis': {
        'HSPA8', 'HSP90AA1', 'HSPB1', 'BAG3', 'UBB', 'UBC', 'UBE2N', 'UBE3A', 'PSMA1', 'PSMB5',
    },
    'Neuroinflammation': {
        'HLA-DRA', 'HLA-DRB1', 'C1QA', 'C1QB', 'C1QC', 'TYROBP', 'TREM2', 'IL1B', 'TNF', 'NFKBIA',
    },
    'Vesicle Trafficking': {
        'RAB3A', 'RAB5A', 'RAB7A', 'DNM1', 'SNAP25', 'STXBP1', 'VAMP2', 'SYT1', 'AP2M1', 'CLTC',
    },
    'Myelination / Axon': {
        'MBP', 'PLP1', 'MOG', 'MAG', 'MOBP', 'CLDN11', 'SOX10', 'OLIG1', 'OLIG2', 'NEFL',
    },
}

PREVIOUS_STEP2_EVIDENCE_FILES = [
    './MIND_Research_Results/SAA_subgroup_BL/SAA_BL_ANCOVA_Results.csv',
    './analysis_results_professional/Stats_HC_vs_PD_SAA+.csv',
    './analysis_results_professional/Stats_HC_vs_prodromal_SAA+.csv',
    './analysis_results_professional/Stats_HC_vs_prodromal_SAA-.csv',
    './analysis_results_professional/Stats_prodromal_SAA+_vs_PD_SAA+.csv',
    './analysis_results_professional/Stats_prodromal_SAA-_vs_PD_SAA+.csv',
    './analysis_results_professional/Stats_prodromal_SAA-_vs_prodromal_SAA+.csv',
]


def _load_previous_mind_evidence():
    """
    加载 Step2 已有的 MIND 组间效应量结果，用于加权 burden score。

    遍历多个 Step2 输出文件（ANCOVA/Welch 检验结果），提取每个 MIND 指标的
    效应量（Cohen's d 或 adjusted group effect）和 p 值，
    按 p 值显著性分档加权（p≤0.01 → 1.5x, p≤0.05 → 1.0x, 其他 → 0.5x），
    最终汇总为每个 MIND 指标的平均加权效应量。

    返回：DataFrame，列包含 Feature, Mean_Abs_Effect, Mean_Weight, Evidence_Count, Min_P_Value
    """
    rows = []
    for path in PREVIOUS_STEP2_EVIDENCE_FILES:
        if not os.path.exists(path):
            continue

        try:
            evidence_df = pd.read_csv(path)
        except Exception:
            continue

        feature_col = None
        for candidate in ['MIND指标', 'Feature', 'MIND_Feature']:
            if candidate in evidence_df.columns:
                feature_col = candidate
                break
        if feature_col is None and len(evidence_df.columns) > 0:
            feature_col = evidence_df.columns[0]

        effect_col = None
        for candidate in ['Cohens_d', 'Cohen_d', 'EffectSize', 'Adjusted_Group_Effect']:
            if candidate in evidence_df.columns:
                effect_col = candidate
                break
        if effect_col is None:
            continue

        p_col = None
        for candidate in ['ANCOVA_p_fdr', 'P_FDR', 'p_fdr', 'Welch_p', 'ANCOVA_p']:
            if candidate in evidence_df.columns:
                p_col = candidate
                break

        for _, row in evidence_df.iterrows():
            feature = str(row.get(feature_col, '')).strip()
            if not feature.startswith('MIND_'):
                continue

            effect = pd.to_numeric(pd.Series([row.get(effect_col)]), errors='coerce').iloc[0]
            if pd.isna(effect):
                continue

            p_value = np.nan
            if p_col is not None:
                p_value = pd.to_numeric(pd.Series([row.get(p_col)]), errors='coerce').iloc[0]

            if pd.notna(p_value):
                if p_value <= 0.01:
                    sig_weight = 1.5
                elif p_value <= 0.05:
                    sig_weight = 1.0
                else:
                    sig_weight = 0.5
            else:
                sig_weight = 1.0

            rows.append({
                'Feature': feature,
                'Source_File': os.path.basename(path),
                'Effect_Size': float(effect),
                'Abs_Effect_Size': float(abs(effect)),
                'P_Value': float(p_value) if pd.notna(p_value) else np.nan,
                'Weight': float(abs(effect) * sig_weight),
            })

    if not rows:
        return pd.DataFrame()

    evidence = pd.DataFrame(rows)
    summary = evidence.groupby('Feature', as_index=False).agg(
        Mean_Abs_Effect=('Abs_Effect_Size', 'mean'),
        Mean_Weight=('Weight', 'mean'),
        Evidence_Count=('Source_File', 'nunique'),
        Min_P_Value=('P_Value', 'min'),
    )
    summary = summary.sort_values(['Mean_Weight', 'Mean_Abs_Effect'], ascending=False).reset_index(drop=True)
    return summary


def _hc_reference_stats(df_raw, cols):
    """
    计算 HC（健康对照）基线的均值和标准差，用于后续 z-score 标准化。

    这是 burden score 构建的关键步骤：以 HC 为参考群体，
    将 SAA+ 个体的 MIND 指标转化为偏离健康水平的 z-score。

    参数：
        df_raw: 原始长表数据（包含所有时间点和所有组别）
        cols: 需要计算 HC 参考统计量的 MIND 指标列名列表

    返回：dict，键为列名，值为 {'mean': float, 'std': float}
    """
    bl = df_raw[df_raw['EVENT_ID'] == 'BL'].copy()
    hc = bl[bl['Group_MIND'] == 'HC'].copy()
    if hc.empty:
        raise ValueError('HC baseline rows are required to build the burden score.')

    hc = coerce_numeric(hc, cols)
    stats = {}
    for col in cols:
        series = pd.to_numeric(hc[col], errors='coerce')
        mean = series.mean(skipna=True)
        std = series.std(skipna=True, ddof=0)
        if pd.isna(std) or std == 0:
            std = 1.0
        stats[col] = {'mean': float(mean), 'std': float(std)}
    return stats


def _build_burden_score(df_raw, df_saa):
    """
    构建 MIND burden score（模块 1：4.4.1）。

    构建策略（优先级从高到低）：
    1. 优先使用 Step2 已有的效应量结果加权：对每个 MIND 指标做 HC 参照 z-score，
       取绝对值后乘以 Step2 效应量权重，求加权平均。
    2. 降级方案：对 SAA_BURDEN_COLS 做 z-score 后取 PCA 第一主成分。
    3. 单特征兜底：只有一个特征时直接用其 z-score。

    参数：
        df_raw: 原始长表数据（用于提取 HC 参考统计量）
        df_saa: SAA+ 人群的基线数据表

    返回：
        df_out: 添加了 Burden_Score 列的 DataFrame
        method: 使用的构建方法描述
        explained: PCA 解释方差比（仅 PCA 方案有值）
        burden_cols: 实际使用的 burden 特征列表
        burden_evidence: Step2 效应量证据表
    """
    evidence = _load_previous_mind_evidence()
    if not evidence.empty:
        burden_cols = [col for col in evidence['Feature'].tolist() if col in df_raw.columns and col in df_saa.columns]
        if burden_cols:
            stats = _hc_reference_stats(df_raw, burden_cols)
            weight_map = evidence.set_index('Feature')['Mean_Weight'].to_dict()
            total_weight = float(sum(weight_map.get(col, 0.0) for col in burden_cols))
            if total_weight <= 0:
                total_weight = float(len(burden_cols))

            source = coerce_numeric(df_saa.copy(), burden_cols)
            weighted_terms = []
            for col in burden_cols:
                mean = stats[col]['mean']
                std = stats[col]['std']
                z = (pd.to_numeric(source[col], errors='coerce') - mean) / std
                weighted_terms.append(z.abs().fillna(0.0) * weight_map.get(col, 0.0))

            burden_score = pd.concat(weighted_terms, axis=1).sum(axis=1) / total_weight
            out = df_saa.copy()
            out['Burden_Score'] = burden_score.values
            out['Burden_Source'] = 'previous_step2_results'
            out['Burden_Weight_Mode'] = 'HC-referenced weighted absolute deviation'
            burden_evidence = evidence.copy()
            return out, 'HC-referenced burden score weighted by Step2 effect sizes', np.nan, burden_cols, burden_evidence

    burden_cols = [col for col in SAA_BURDEN_COLS if col in df_saa.columns]
    if not burden_cols:
        raise ValueError('No burden columns are available for Plan 1.')

    work = coerce_numeric(df_saa, burden_cols)
    zf = zscore_frame(work, burden_cols)
    zf = zf.fillna(0.0)

    if zf.shape[1] == 1:
        burden_score = zf.iloc[:, 0].copy()
        burden_method = 'single-feature z-score fallback'
        explained = 1.0
    else:
        scaler = StandardScaler()
        scaled = scaler.fit_transform(zf.values)
        pca = PCA(n_components=1, random_state=RANDOM_STATE)
        burden_score = pca.fit_transform(scaled).ravel()
        burden_method = 'PCA-PC1 on burden features fallback'
        explained = float(pca.explained_variance_ratio_[0])

    out = df_saa.copy()
    out['Burden_Score'] = burden_score
    out['Burden_Source'] = 'fallback_internal_pca'
    out['Burden_Weight_Mode'] = 'internal_pca'
    return out, burden_method, explained, burden_cols, pd.DataFrame()


def _bootstrap_burden_ci(df_raw, df_saa, n_bootstrap=1000, ci=0.95, random_state=42):
    """
    Bootstrap 95% 置信区间评估 burden score 的稳定性。

    对 burden score 的均值和标准差进行 bootstrap 重采样，
    获取置信区间以评估 burden score 构建的统计稳健性。

    参数：
        df_raw: 原始长表数据
        df_saa: SAA+ 基线数据
        n_bootstrap: bootstrap 重采样次数（默认 1000）
        ci: 置信水平（默认 0.95）
        random_state: 随机种子

    返回：(mean_lo, mean_hi, sd_lo, sd_hi) 四个浮点数
    """
    rng = np.random.default_rng(random_state)
    burden_df, _, _, _, _ = _build_burden_score(df_raw, df_saa)
    if 'Burden_Score' not in burden_df.columns:
        return np.nan, np.nan, np.nan, np.nan

    scores = burden_df['Burden_Score'].dropna().values
    if len(scores) < 5:
        return np.nan, np.nan, np.nan, np.nan

    boot_means = []
    boot_sds = []
    for _ in range(n_bootstrap):
        sample = rng.choice(scores, size=len(scores), replace=True)
        boot_means.append(np.mean(sample))
        boot_sds.append(np.std(sample, ddof=0))

    alpha = (1 - ci) / 2
    mean_lo = float(np.percentile(boot_means, alpha * 100))
    mean_hi = float(np.percentile(boot_means, (1 - alpha) * 100))
    sd_lo = float(np.percentile(boot_sds, alpha * 100))
    sd_hi = float(np.percentile(boot_sds, (1 - alpha) * 100))
    return mean_lo, mean_hi, sd_lo, sd_hi


def _save_gobp_dotplot(pathway_df, out_dir):
    """
    独立 GO-BP dot plot（Figure D 补充可视化）。

    按照论文要求，生成标准的 GO Biological Process 富集 dot plot：
    - 横轴：Gene Ratio（富集比）
    - 点大小：overlap gene count
    - 点颜色：-log10(FDR)
    - 正向基因集和负向基因集分开展示
    - 显著性星号标注（* p<0.05, ** p<0.01, *** p<0.001）

    参数：
        pathway_df: 通路富集结果 DataFrame
        out_dir: 输出目录

    返回：图片路径，若无数据则返回 None
    """
    if pathway_df is None or pathway_df.empty:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), constrained_layout=True)
    for j, gene_list in enumerate(['Positive PLS1', 'Negative PLS1']):
        ax = axes[j]
        sub = pathway_df[pathway_df['Gene_List'] == gene_list].sort_values('FDR').head(10)
        if sub.empty:
            ax.text(0.5, 0.5, f'No enrichment\n({gene_list})', ha='center', va='center', fontsize=11)
            ax.axis('off')
            continue

        y_pos = np.arange(len(sub))
        sizes = sub['Overlap'].clip(lower=1) * 45
        colors = -np.log10(sub['FDR'].clip(lower=1e-12))
        sc = ax.scatter(sub['Gene_Ratio'], y_pos, s=sizes, c=colors, cmap=CMAP_SEQUENTIAL,
                        edgecolors='black', linewidth=0.5)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(sub['Set_Name'], fontsize=9)
        ax.set_xlabel('Gene Ratio')
        ax.set_title(f'{"D1" if j == 0 else "D2"}. {gene_list} Pathway Enrichment')
        plt.colorbar(sc, ax=ax, fraction=0.04, pad=0.02, label='-log10(FDR)')

        # Add FDR annotation
        for i, row in enumerate(sub.itertuples()):
            fdr = row.FDR
            stars = '***' if fdr < 0.001 else '**' if fdr < 0.01 else '*' if fdr < 0.05 else ''
            if stars:
                ax.text(sub['Gene_Ratio'].iloc[i] + 0.005, i, stars, va='center', fontsize=8, color='red')

    fig.suptitle('GO-BP Pathway Enrichment Dot Plot', fontsize=13)
    path = os.path.join(out_dir, 'Plan1_GOBP_Dotplot.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return path


def _save_four_quadrant_scatter(fit_data_dict, out_dir):
    """
    四象限散点图（4.4.4 结果呈现要求）。

    横轴：Burden Score，纵轴：Resilience（Studentized Residual）
    中位数分割形成四个象限，用不同颜色标注：
    - 红色：High Burden + Low Resilience（高风险）
    - 蓝色：Low Burden + High Resilience（低风险）

    为每个目标量表（UPDRS3, MoCA）各生成一张图。

    参数：
        fit_data_dict: dict，键为量表名，值为含 Burden_Score 和 Residual 的 DataFrame
        out_dir: 输出目录

    返回：生成的图片路径列表
    """
    fig_paths = []
    for scale, fit_data in fit_data_dict.items():
        if fit_data is None or fit_data.empty or 'Residual' not in fit_data.columns:
            continue

        work = fit_data[['Original_SUB_ID', 'Group_MIND', 'Burden_Score', 'Residual']].copy()
        work = work.dropna(subset=['Burden_Score', 'Residual']).copy()
        if work.empty:
            continue

        burden_thr = work['Burden_Score'].median()
        resilience_thr = work['Residual'].median()

        fig, ax = plt.subplots(figsize=(8, 7))
        quadrant_labels = {
            ('High', 'High'): ('High Burden, High Resilience', GROUP_COLORS[2]),
            ('High', 'Low'): ('High Burden, Low Resilience', GROUP_COLORS[0]),
            ('Low', 'High'): ('Low Burden, High Resilience', GROUP_COLORS[3]),
            ('Low', 'Low'): ('Low Burden, Low Resilience', GROUP_COLORS[1]),
        }

        for _, row in work.iterrows():
            b_level = 'High' if row['Burden_Score'] >= burden_thr else 'Low'
            r_level = 'High' if row['Residual'] >= resilience_thr else 'Low'
            label, color = quadrant_labels[(b_level, r_level)]
            ax.scatter(row['Burden_Score'], row['Residual'], c=color, s=30, alpha=0.7)

        ax.axvline(burden_thr, color='gray', linestyle='--', linewidth=1, alpha=0.7)
        ax.axhline(resilience_thr, color='gray', linestyle='--', linewidth=1, alpha=0.7)
        ax.set_xlabel('Burden Score')
        ax.set_ylabel('Resilience (Studentized Residual)')
        ax.set_title(f'Four-Quadrant Risk Phenotype | {scale}')

        # Legend
        for (b_level, r_level), (label, color) in quadrant_labels.items():
            n = len(work[(work['Burden_Score'] >= burden_thr if b_level == 'High' else work['Burden_Score'] < burden_thr) &
                         (work['Residual'] >= resilience_thr if r_level == 'High' else work['Residual'] < resilience_thr)])
            ax.scatter([], [], c=color, s=50, label=f'{label} (n={n})')
        ax.legend(frameon=False, fontsize=8, loc='best')

        ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
        path = os.path.join(out_dir, f'Plan1_FourQuadrant_{scale}.png')
        fig.savefig(path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        fig_paths.append(path)
    return fig_paths


def _save_forest_plot_stage_expression(stage_summary_df, out_dir):
    """
    阶段表达 forest plot（4.4.2 结果呈现要求）。

    展示 logistic 回归中每个自变量的 odds ratio 和 95% CI。
    红色虚线标注 OR=1（无效应线），并标注 p 值显著性星号。

    参数：
        stage_summary_df: 阶段表达模型的系数汇总 DataFrame（含 OddsRatio, CI_Low, CI_High）
        out_dir: 输出目录

    返回：图片路径，若无数据则返回 None
    """
    if stage_summary_df is None or stage_summary_df.empty:
        return None

    plot_df = stage_summary_df[stage_summary_df['Term'] != 'Intercept'].copy()
    if 'OddsRatio' not in plot_df.columns:
        return None
    plot_df = plot_df.dropna(subset=['OddsRatio', 'CI_Low', 'CI_High']).copy()
    if plot_df.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, max(3, len(plot_df) * 0.6)))
    y_pos = np.arange(len(plot_df))

    ax.errorbar(
        plot_df['OddsRatio'], y_pos,
        xerr=[plot_df['OddsRatio'] - plot_df['CI_Low'], plot_df['CI_High'] - plot_df['OddsRatio']],
        fmt='o', color=GROUP_COLORS[0], ecolor='black', elinewidth=1.5, capsize=4, markersize=7,
    )
    ax.axvline(1.0, color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(plot_df['Term'])
    ax.set_xlabel('Odds Ratio (95% CI)')
    ax.set_title('Stage Expression: Odds Ratios')
    ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)

    # Annotate p-values
    for i, row in enumerate(plot_df.itertuples()):
        p = row.PValue
        stars = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
        ax.text(plot_df['CI_High'].iloc[i] + 0.05, i, f'p={p:.3f} {stars}', va='center', fontsize=8)

    path = os.path.join(out_dir, 'Plan1_Stage_Expression_Forest.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return path


def _run_pd_saa_exploratory(df_raw, burden_df):
    """
    探索性分析：PD/SAA- discordant biology 组（4.5 节）。

    将 PD/SAA- 作为探索性组别纳入，描述其 MIND burden 模式是否偏离 PD/SAA+，
    讨论可能的病理或诊断异质性。

    使用 Kruskal-Wallis 检验比较四组（prodromal_SAA-, prodromal_SAA+, PD_SAA+, PD/SAA-）
    的 burden score 分布差异。

    参数：
        df_raw: 原始长表数据
        burden_df: 含 Burden_Score 的 DataFrame

    返回：汇总 DataFrame（每组的 N, Mean, SD, Median）
    """
    all_groups = ['prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+', 'PD_SAA-']
    bl = df_raw[df_raw['EVENT_ID'] == 'BL'].copy()
    bl = bl[bl['Group_MIND'].isin(all_groups)].copy()
    bl = bl.drop_duplicates(subset='Original_SUB_ID', keep='first').reset_index(drop=True)
    bl = encode_binary_columns(bl)

    if bl.empty:
        return pd.DataFrame()

    burden_map = burden_df[['Original_SUB_ID', 'Burden_Score']].drop_duplicates(subset='Original_SUB_ID', keep='first')
    bl = pd.merge(bl, burden_map, on='Original_SUB_ID', how='inner')
    bl = bl.dropna(subset=['Burden_Score']).copy()

    if bl.empty:
        return pd.DataFrame()

    rows = []
    for group in all_groups:
        gdf = bl[bl['Group_MIND'] == group]
        if gdf.empty:
            continue
        rows.append({
            'Group': group,
            'N': int(len(gdf)),
            'Burden_Mean': float(gdf['Burden_Score'].mean()),
            'Burden_SD': float(gdf['Burden_Score'].std(ddof=0)),
            'Burden_Median': float(gdf['Burden_Score'].median()),
        })

    if not rows:
        return pd.DataFrame()

    summary = pd.DataFrame(rows)

    # ANOVA-like comparison across all 4 groups
    from scipy.stats import kruskal
    group_data = [bl[bl['Group_MIND'] == g]['Burden_Score'].dropna().values for g in all_groups]
    group_data = [g for g in group_data if len(g) >= 3]
    if len(group_data) >= 2:
        try:
            stat, p = kruskal(*group_data)
            summary.attrs['kruskal_stat'] = float(stat)
            summary.attrs['kruskal_p'] = float(p)
        except Exception:
            pass

    return summary


def _fit_resilience_model(df, scale_col, label):
    """
    构建临床韧性（resilience）模型（模块 3：4.4.3）。

    核心逻辑：以临床量表评分为因变量，以 burden score + 临床协变量为自变量，
    建立线性回归模型，取 studentized residuals 作为 resilience 表型。
    残差越高 → 在相似 burden 下临床表现越"耐受"。

    必要前提检验：Spearman 相关检验 burden 与临床评分之间的单调关系。

    协变量（CLINICAL_COVARS）：Age_at_Visit, Sex, Education, LEDD_Baseline, NHY

    参数：
        df: SAA+ 人群的基线数据（含 Burden_Score）
        scale_col: 临床量表列名（如 UPDRSIII, MoCA）
        label: 量表标签（如 'UPDRS3', 'MoCA'）

    返回：dict，包含 label, n, r2, coefficients, spearman_r, spearman_p,
          residual_mean, residual_sd, data（含 Residual, Studentized_Residual, Predicted）
          若样本不足则返回 None
    """
    covars = [col for col in CLINICAL_COVARS if col in df.columns]
    model_df = coerce_numeric(df, ['Burden_Score', scale_col] + [col for col in covars if col != 'Sex'])
    model_df = model_df.dropna(subset=['Burden_Score', scale_col]).copy()

    if len(model_df) < 8:
        return None

    # Monotonicity check: Spearman correlation between burden and clinical score
    from scipy.stats import spearmanr
    burden_vals = pd.to_numeric(model_df['Burden_Score'], errors='coerce')
    scale_vals = pd.to_numeric(model_df[scale_col], errors='coerce')
    valid_mask = burden_vals.notna() & scale_vals.notna()
    if valid_mask.sum() >= 10:
        spearman_r, spearman_p = spearmanr(burden_vals[valid_mask], scale_vals[valid_mask])
    else:
        spearman_r, spearman_p = np.nan, np.nan

    x_cols = ['Burden_Score'] + [col for col in covars if col in model_df.columns]
    x = model_df[x_cols].copy()
    if 'Sex' in x.columns:
        x['Sex'] = pd.to_numeric(x['Sex'], errors='coerce')
    x = x.fillna(x.median(numeric_only=True))
    y = pd.to_numeric(model_df[scale_col], errors='coerce')

    reg = LinearRegression()
    reg.fit(x, y)
    y_pred = reg.predict(x)
    residual = y - y_pred

    # Studentized residuals
    n = len(y)
    p = x.shape[1]
    if n > p + 1:
        mse = np.sum(residual ** 2) / (n - p - 1)
        hat_matrix = x.values @ np.linalg.pinv(x.values.T @ x.values) @ x.values.T
        leverage = np.diag(hat_matrix)
        studentized = residual / np.sqrt(mse * np.clip(1 - leverage, 0.01, None))
    else:
        studentized = residual / (residual.std(ddof=0) + 1e-12)

    return {
        'label': label,
        'n': int(len(model_df)),
        'r2': float(r2_score(y, y_pred)) if len(model_df) >= 2 else np.nan,
        'intercept': float(reg.intercept_),
        'coefficients': dict(zip(x_cols, reg.coef_)),
        'residual_mean': float(np.mean(residual)),
        'residual_sd': float(np.std(residual, ddof=0)),
        'spearman_r': float(spearman_r),
        'spearman_p': float(spearman_p),
        'data': model_df.assign(
            Residual=residual,
            Studentized_Residual=studentized,
            Predicted=y_pred,
        ),
    }


def _group_summary(df, scale_col):
    """
    按组别汇总 burden 和临床量表的描述性统计。

    参数：
        df: 含 Group_MIND, Burden_Score 和临床量表列的 DataFrame
        scale_col: 临床量表列名

    返回：DataFrame，每组的 N、Burden Mean/SD、量表 Mean/SD
    """
    rows = []
    for group_name, group_df in df.groupby('Group_MIND'):
        rows.append({
            'Group_MIND': group_name,
            'n': int(len(group_df)),
            'Burden_Mean': float(group_df['Burden_Score'].mean()),
            'Burden_SD': float(group_df['Burden_Score'].std(ddof=0)),
            f'{scale_col}_Mean': float(group_df[scale_col].mean()),
            f'{scale_col}_SD': float(group_df[scale_col].std(ddof=0)),
        })
    return pd.DataFrame(rows)


def _fit_mixedlm(formula, data, groups_col):
    """
    拟合混合效应线性模型（MixedLM），带多优化器降级策略。

    依次尝试 powell → nm → bfgs 优化器，以及 '1 + Time' → '1' 随机效应公式，
    直到有一个成功收敛。使用 REML=False（似然比检验需要 ML 估计）。

    参数：
        formula: statsmodels 公式字符串（如 'UPDRS3 ~ Time * Burden + ...'）
        data: 长表 DataFrame
        groups_col: 分组列名（如 'Original_SUB_ID'）

    返回：拟合结果对象
    """
    for re_formula in ['1 + Time', '1']:
        for method in ['powell', 'nm', 'bfgs']:
            try:
                return smf.mixedlm(
                    formula,
                    data,
                    groups=data[groups_col],
                    re_formula=re_formula,
                ).fit(method=method, reml=False, maxiter=120)
            except Exception:
                continue
    raise ValueError('All MixedLM optimizers failed.')


def _fit_stage_expression(df_saa, burden_source_col='Burden_Score'):
    """
    阶段表达分析（模块 2：4.4.2）。

    在 SAA+ 人群内部，检验 MIND burden 是否与临床阶段（prodromal vs PD）相关。
    使用 logistic 回归：Stage_PD ~ Burden_Score + Age + Sex + Education。

    若 burden 与 PD 阶段正相关，说明 MIND 不是简单重复 SAA 信息，
    而是在"病理存在"之上刻画了"病理表达的脑网络强度"。

    参数：
        df_saa: SAA+ 人群基线数据
        burden_source_col: burden score 列名

    返回：
        stage_df: 用于建模的 DataFrame（含 Stage_PD 列）
        model: 拟合的 logistic/OLS 模型对象
        summary_rows: 模型系数汇总（含 OR, CI）
        stage_path: 汇总 CSV 保存路径
    """
    stage_df = df_saa[df_saa['Group_MIND'].isin(['prodromal_SAA+', 'PD_SAA+'])].copy()
    stage_df = coerce_numeric(stage_df, [burden_source_col, 'Age_at_Visit', 'Education'])
    stage_df = stage_df.dropna(subset=[burden_source_col, 'Age_at_Visit', 'Education']).copy()

    if 'Sex' in stage_df.columns:
        stage_df['Sex'] = pd.to_numeric(stage_df['Sex'], errors='coerce')

    if stage_df.empty:
        return pd.DataFrame(), None, None, None

    stage_df['Stage_PD'] = (stage_df['Group_MIND'] == 'PD_SAA+').astype(int)

    if stage_df['Stage_PD'].nunique() < 2:
        return pd.DataFrame(), None, None, None

    logit_formula = f'Stage_PD ~ {burden_source_col} + Age_at_Visit + C(Sex) + Education'
    try:
        model = smf.logit(logit_formula, data=stage_df).fit(disp=False)
        summary_rows = pd.DataFrame({
            'Term': model.params.index,
            'Coefficient': model.params.values,
            'StdErr': model.bse.values,
            'PValue': model.pvalues.values,
            'OddsRatio': np.exp(model.params.values),
        })
        summary_rows['CI_Low'] = np.exp(model.conf_int().iloc[:, 0].values)
        summary_rows['CI_High'] = np.exp(model.conf_int().iloc[:, 1].values)
        stage_path = os.path.join(BASE_OUTPUT_DIR, 'Plan1_Stage_Expression_Logit.csv')
        summary_rows.to_csv(stage_path, index=False, encoding='utf-8-sig')
        return stage_df, model, summary_rows, stage_path
    except Exception:
        fallback = smf.ols(logit_formula, data=stage_df).fit()
        summary_rows = pd.DataFrame({
            'Term': fallback.params.index,
            'Coefficient': fallback.params.values,
            'StdErr': fallback.bse.values,
            'PValue': fallback.pvalues.values,
        })
        stage_path = os.path.join(BASE_OUTPUT_DIR, 'Plan1_Stage_Expression_OLS.csv')
        summary_rows.to_csv(stage_path, index=False, encoding='utf-8-sig')
        return stage_df, fallback, summary_rows, stage_path


def _build_high_risk_phenotypes(stage_df, burden_col='Burden_Score'):
    """
    高风险表型定义（模块 4 的一部分：4.4.4）。

    基于 burden score 和 resilience 的中位数，将 SAA+ 个体划分为四象限：
    - High_Burden__Low_Resilience: 高负荷 + 低韧性 → 理论最高风险
    - High_Burden__High_Resilience: 高负荷 + 高韧性
    - Low_Burden__Low_Resilience: 低负荷 + 低韧性
    - Low_Burden__High_Resilience: 低负荷 + 高韧性 → 理论最低风险

    参数：
        stage_df: 含 Burden_Score 和 Residual 的 DataFrame
        burden_col: burden score 列名

    返回：DataFrame，含 Risk_Phenotype 列
    """
    rows = []
    if stage_df.empty or burden_col not in stage_df.columns:
        return pd.DataFrame()

    for scale in TARGET_SCALES:
        scale_col = alias_scale_column(stage_df, scale)
        if scale_col not in stage_df.columns:
            continue
        work = stage_df[['Original_SUB_ID', 'Group_MIND', burden_col, scale_col, 'Residual']].copy()
        work = coerce_numeric(work, [burden_col, scale_col, 'Residual'])
        work = work.dropna(subset=[burden_col, 'Residual']).copy()
        if work.empty:
            continue

        burden_thr = float(work[burden_col].median())
        resilience_thr = float(work['Residual'].median())
        work['Burden_Level'] = np.where(work[burden_col] >= burden_thr, 'High_Burden', 'Low_Burden')
        work['Resilience_Level'] = np.where(work['Residual'] >= resilience_thr, 'High_Resilience', 'Low_Resilience')
        work['Risk_Phenotype'] = work['Burden_Level'] + '__' + work['Resilience_Level']
        work['Scale'] = scale
        rows.append(work)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _fit_longitudinal_validation(df_raw, burden_df, resilience_lookup=None):
    """
    纵向验证模型（模块 4：4.4.4）。

    在 SAA+ 子集内建立混合效应模型（MixedLM），验证 burden 和 resilience
    对纵向临床进展的预测作用。

    模型公式：
        Clinical ~ Time * Burden_Score + Time * Resilience_Score + Age + Sex + Education + LEDD + NHY
        + (1 + Time | Subject)

    核心关注项：
    - Time × Burden: burden 越高，未来恶化斜率是否越快？
    - Time × Resilience: resilience 越高，未来恶化斜率是否越缓？

    参数：
        df_raw: 原始长表数据（含所有时间点）
        burden_df: SAA+ 基线数据（含 Burden_Score）
        resilience_lookup: dict，键为量表名，值为含 Original_SUB_ID 和 Residual 的 DataFrame

    返回：
        summary_df: 每个量表的 LME 汇总（β, SE, p）
        lme_df: 拟合数据（含 Fitted 列，用于绘图）
    """
    if burden_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    time_map = {'BL': 0.0, 'V04': 1.0, 'V06': 2.0, 'V08': 3.0, 'V10': 4.0, 'V12': 5.0}
    df_long = df_raw[df_raw['EVENT_ID'].isin(time_map.keys())].copy()
    df_long['Time'] = df_long['EVENT_ID'].map(time_map)
    df_long = df_long[df_long['Group_MIND'].isin(['prodromal_SAA+', 'PD_SAA+'])].copy()

    burden_map = burden_df[['Original_SUB_ID', 'Burden_Score']].drop_duplicates(subset='Original_SUB_ID', keep='first')
    df_long = pd.merge(df_long, burden_map, on='Original_SUB_ID', how='inner')

    summary_rows = []
    lme_frames = []

    covar_cols = [c for c in CLINICAL_COVARS if c in df_long.columns]
    covar_numeric = [c for c in covar_cols if c != 'Sex']

    for scale in TARGET_SCALES:
        scale_col = alias_scale_column(df_long, scale)
        work = df_long.copy()
        work[scale_col] = pd.to_numeric(work[scale_col], errors='coerce')
        work = coerce_numeric(work, [scale_col, 'Burden_Score'] + covar_numeric)
        if 'Sex' in work.columns:
            work['Sex'] = pd.to_numeric(work['Sex'], errors='coerce')
        required = ['Time', scale_col, 'Burden_Score'] + [c for c in covar_cols if c in work.columns]
        work = work.dropna(subset=required).copy()
        if len(work) < 12 or work['Original_SUB_ID'].nunique() < 6:
            continue

        if resilience_lookup and scale in resilience_lookup:
            resilience_map = resilience_lookup[scale].drop_duplicates(subset='Original_SUB_ID', keep='first')
            resilience_map = resilience_map.rename(columns={'Residual': 'Resilience_Score'})
            work = pd.merge(work, resilience_map[['Original_SUB_ID', 'Resilience_Score']], on='Original_SUB_ID', how='inner')
            work = work.dropna(subset=['Resilience_Score']).copy()
        else:
            work['Resilience_Score'] = np.nan

        if 'Resilience_Score' not in work.columns or work['Resilience_Score'].isna().all():
            continue

        covar_formula_parts = []
        for c in covar_cols:
            if c in work.columns:
                if c == 'Sex':
                    covar_formula_parts.append('C(Sex)')
                else:
                    covar_formula_parts.append(c)
        covar_str = ' + '.join(covar_formula_parts) if covar_formula_parts else 'Age_at_Visit + Education'
        formula = f'{scale_col} ~ Time * Burden_Score + Time * Resilience_Score + {covar_str}'
        try:
            fit = _fit_mixedlm(formula, work, 'Original_SUB_ID')
            method = 'MixedLM'
        except Exception:
            fit = smf.ols(formula, data=work).fit()
            method = 'OLS'

        burden_term = 'Time:Burden_Score'
        resilience_term = 'Time:Resilience_Score'
        if burden_term in fit.params.index or resilience_term in fit.params.index:
            summary_rows.append({
                'Scale': scale,
                'Model': method,
                'N': int(len(work)),
                'Subjects': int(work['Original_SUB_ID'].nunique()),
                'Time_x_Burden_Beta': float(fit.params.get(burden_term, np.nan)),
                'Time_x_Burden_SE': float(fit.bse.get(burden_term, np.nan)),
                'Time_x_Burden_P': float(fit.pvalues.get(burden_term, np.nan)),
                'Time_x_Resilience_Beta': float(fit.params.get(resilience_term, np.nan)),
                'Time_x_Resilience_SE': float(fit.bse.get(resilience_term, np.nan)),
                'Time_x_Resilience_P': float(fit.pvalues.get(resilience_term, np.nan)),
            })

        work['Fitted'] = fit.predict(work)
        lme_frames.append(
            work[['Original_SUB_ID', 'Group_MIND', 'Time', scale_col, 'Burden_Score', 'Resilience_Score', 'Fitted']]
            .assign(Scale=scale)
        )

    return pd.DataFrame(summary_rows), pd.concat(lme_frames, ignore_index=True) if lme_frames else pd.DataFrame()


def _load_plan1_abnormality_map():
    """
    加载区域级异常图谱，用于 PLS 机制注释的 Y 变量。

    从 Step2 已有的多个组间比较结果文件中，提取每个 ROI 的 T 值和 p 值，
    按 |T| × p-weighting 公式计算加权异常分数，跨文件取均值汇总。

    加权公式：weight = |T| × (1 + max(-log10(p), 0))
    - p ≤ 0.01 → -log10(p) ≥ 2 → 权重乘以 ≥ 3
    - p ≤ 0.05 → -log10(p) ≥ 1.3 → 权重乘以 ≥ 2.3
    - p > 0.1  → 权重基本不变

    与 Desikan-Killiany atlas 对齐后返回 atlas 元信息、标签表、异常图谱和明细表。

    返回：
        atlas: abagen atlas dict（含 'image' 和 'info' 路径）
        atlas_labels: DataFrame，按 id 排序的 atlas 标签表（83 行）
        map_df: DataFrame，每个 ROI 的汇总异常分数（Abnormality_Score, Mean_Abs_T, Source_Count）
        detail_df: DataFrame，每条对比×ROI 的明细记录（用于溯源）
    """
    atlas = abagen.datasets.fetch_desikan_killiany(native=False, surface=False)
    atlas_labels = pd.read_csv(atlas['info']).sort_values('id').reset_index(drop=True)
    source_files = [
        './analysis_results_professional/Stats_HC_vs_PD_SAA+.csv',
        './analysis_results_professional/Stats_HC_vs_prodromal_SAA+.csv',
        './analysis_results_professional/Stats_HC_vs_prodromal_SAA-.csv',
        './analysis_results_professional/Stats_prodromal_SAA+_vs_PD_SAA+.csv',
        './analysis_results_professional/Stats_prodromal_SAA-_vs_PD_SAA+.csv',
        './analysis_results_professional/Stats_prodromal_SAA-_vs_prodromal_SAA+.csv',
        './nodal_statistical_results/Nodal_ANCOVA_Results.csv',
        './nodal_statistical_results/Nodal_ANOVA_Results.csv',
    ]

    detail_rows = []
    for path in source_files:
        if not os.path.exists(path):
            continue
        try:
            contrast_df = pd.read_csv(path)
        except Exception:
            continue

        # 自动检测 ROI 列名（不同 Step2 输出文件可能使用不同列名）
        roi_col = None
        for candidate in ['ROI', 'ROI_ID', 'Node', 'Region']:
            if candidate in contrast_df.columns:
                roi_col = candidate
                break
        if roi_col is None:
            continue

        t_col = None
        for candidate in ['T', 'Strength_T', 'Adjusted_Group_Effect', 't', 'Effect']:
            if candidate in contrast_df.columns:
                t_col = candidate
                break
        if t_col is None:
            continue

        p_col = None
        for candidate in ['P_FDR', 'P_raw', 'P', 'ANCOVA_p_fdr', 'ANCOVA_p']:
            if candidate in contrast_df.columns:
                p_col = candidate
                break

        for _, row in contrast_df.iterrows():
            roi = pd.to_numeric(pd.Series([row.get(roi_col)]), errors='coerce').iloc[0]
            score = pd.to_numeric(pd.Series([row.get(t_col)]), errors='coerce').iloc[0]
            if pd.isna(roi) or pd.isna(score):
                continue
            p_value = pd.to_numeric(pd.Series([row.get(p_col)]), errors='coerce').iloc[0] if p_col is not None else np.nan
            # 加权公式：|T| × (1 + max(-log10(p), 0))
            # p 越小，-log10(p) 越大，权重越高；p 缺失时仅用 |T|
            if pd.notna(p_value):
                weight = float(abs(score) * (1.0 + max(-np.log10(max(float(p_value), 1e-12)), 0.0)))
            else:
                weight = float(abs(score))
            detail_rows.append({
                'ROI': int(roi),
                'Source_File': os.path.basename(path),
                'Raw_T': float(score),
                'Abs_T': float(abs(score)),
                'P_Value': float(p_value) if pd.notna(p_value) else np.nan,
                'Weight': weight,
            })

    if not detail_rows:
        raise ValueError('No ROI-level prior results found for the mechanism map.')

    detail_df = pd.DataFrame(detail_rows)
    map_df = detail_df.groupby('ROI', as_index=False).agg(
        Abnormality_Score=('Weight', 'mean'),
        Mean_Abs_T=('Abs_T', 'mean'),
        Source_Count=('Source_File', 'nunique'),
    )
    map_df = atlas_labels.merge(map_df, left_on='id', right_on='ROI', how='left').drop(columns=['ROI'])
    map_df['Abnormality_Score'] = map_df['Abnormality_Score'].fillna(0.0)
    map_df['Mean_Abs_T'] = map_df['Mean_Abs_T'].fillna(0.0)
    map_df['Source_Count'] = map_df['Source_Count'].fillna(0).astype(int)
    return atlas, atlas_labels, map_df, detail_df


def _hemisphere_preserving_permutation(values, hemispheres, random_state=None):
    """
    半球保持置换检验（spatial null model）。

    在每个半球内部独立打乱数值顺序，保持左右半球各自的数值分布不变，
    从而生成保留空间自相关结构的零分布。这是 PLS 显著性检验的关键步骤：
    避免因脑区空间邻近性导致的假阳性。

    参数：
        values: 一维数组，每个脑区的数值（如异常分数或 Y 标准化值）
        hemispheres: 一维数组，每个脑区的半球标签（'L' 或 'R'）
        random_state: 随机种子

    返回：置换后的一维数组（半球内打乱，半球间保持原分布）
    """
    rng = np.random.default_rng(random_state)
    values = np.asarray(values, dtype=float)
    hemispheres = np.asarray(hemispheres)
    permuted = values.copy()
    for hemi in ['L', 'R']:
        idx = np.where(hemispheres == hemi)[0]
        if len(idx) > 1:
            permuted[idx] = rng.permutation(values[idx])
    return permuted


def _load_abagen_gene_symbol_map():
    """
    加载 abagen 内置的 Entrez ID → Gene Symbol 映射表。

    abagen 包内部维护了一份 reannotated.csv.gz 文件，包含探针到基因符号的
    重注释信息。本函数从中提取 entrez_id → gene_symbol 的映射字典，
    用于将 PLS 基因权重中的数值 ID 转换为可读的基因符号。

    返回：dict，键为 Entrez ID 字符串，值为大写基因符号
    """
    base_dir = os.path.dirname(abagen.__file__)
    candidates = [
        os.path.join(base_dir, 'data', 'reannotated.csv.gz'),
        os.path.join(base_dir, 'images', 'reannotated.csv.gz'),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            mapping_df = pd.read_csv(path, compression='gzip')
        except Exception:
            continue

        symbol_map = {}
        if 'allen_entrez_id' in mapping_df.columns and 'gene_symbol' in mapping_df.columns:
            for _, row in mapping_df[['allen_entrez_id', 'gene_symbol']].dropna().drop_duplicates().iterrows():
                key = str(int(float(row['allen_entrez_id'])))
                symbol_map[key] = str(row['gene_symbol']).strip().upper()
        if 'entrez_id' in mapping_df.columns and 'gene_symbol' in mapping_df.columns:
            for _, row in mapping_df[['entrez_id', 'gene_symbol']].dropna().drop_duplicates().iterrows():
                key = str(int(float(row['entrez_id'])))
                symbol_map.setdefault(key, str(row['gene_symbol']).strip().upper())
        if symbol_map:
            return symbol_map
    return {}


def _hypergeom_ora(query_genes, universe_genes, gene_sets, label_prefix):
    """
    超几何检验的过代表分析（Over-Representation Analysis, ORA）。

    对给定的候选基因集（如 PLS1 正/负向 top-N 基因），检验其在每个功能基因集
    （通路或细胞类型标记基因）中的富集程度。使用 Fisher 精确检验（单侧），
    并对多重比较进行 BH-FDR 校正。

    参数：
        query_genes: 候选基因列表（如 PLS1 top-N 正向基因）
        universe_genes: 基因全集（PLS 分析中所有纳入的基因）
        gene_sets: dict，键为基因集名称，值为基因列表（如 PLAN1_PATHWAY_THEMES）
        label_prefix: 结果标签前缀（如 'Positive PLS1'）

    返回：DataFrame，列含 Gene_List, Set_Name, Overlap, Gene_Ratio, Odds_Ratio, P_Value, FDR
    """
    universe = {str(g).upper() for g in universe_genes if pd.notna(g)}
    query = {str(g).upper() for g in query_genes if pd.notna(g)} & universe
    rows = []
    for set_name, set_genes in gene_sets.items():
        gene_set = {str(g).upper() for g in set_genes if pd.notna(g)} & universe
        if not gene_set:
            continue
        overlap = len(query & gene_set)
        query_only = len(query) - overlap
        set_only = len(gene_set) - overlap
        background_only = len(universe) - overlap - query_only - set_only
        if background_only < 0:
            background_only = 0
        odds_ratio, p_value = fisher_exact([[overlap, query_only], [set_only, background_only]], alternative='greater')
        rows.append({
            'Gene_List': label_prefix,
            'Set_Name': set_name,
            'Overlap': overlap,
            'Set_Size': len(gene_set),
            'Query_Size': len(query),
            'Gene_Ratio': overlap / max(len(query), 1),
            'Odds_Ratio': float(odds_ratio) if np.isfinite(odds_ratio) else np.nan,
            'P_Value': float(p_value),
        })

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out['FDR'] = multipletests(out['P_Value'].values, method='fdr_bh')[1]
    out = out.sort_values(['FDR', 'P_Value', 'Overlap'], ascending=[True, True, False]).reset_index(drop=True)
    return out


def _plan1_network_abnormality_summary(abnormality_map):
    """
    按 Yeo 7 网络汇总区域异常分数。

    将每个 ROI 的异常分数按其所属的功能网络（Visual, Somatomotor, Dorsal Attention,
    Ventral Attention, Limbic, Frontoparietal, Default）分组取均值，
    用于 Figure A2 的网络级异常条形图。

    参数：
        abnormality_map: DataFrame，含 id 和 Abnormality_Score 列

    返回：DataFrame，列含 Network, N_ROI, Mean_Abnormality, Mean_Abs_T
    """
    rows = []
    for net_name, roi_ids in YEO7_MAP.items():
        sub = abnormality_map[abnormality_map['id'].isin(roi_ids)].copy()
        rows.append({
            'Network': net_name,
            'N_ROI': int(len(sub)),
            'Mean_Abnormality': float(sub['Abnormality_Score'].mean()) if not sub.empty else np.nan,
            'Mean_Abs_T': float(sub['Mean_Abs_T'].mean()) if not sub.empty else np.nan,
        })
    return pd.DataFrame(rows).sort_values('Mean_Abnormality', ascending=False, na_position='last').reset_index(drop=True)


def _plan1_celltype_sensitivity(loadings_df, cell_sets, top_ns=(20, 30, 40)):
    """
    细胞类型富集敏感性分析（跨不同 top-N 基因选择阈值）。

    对 PLS1 基因权重分别取 top-20/30/40 正向和负向基因，
    在每个阈值下重复做超几何 ORA 检验，评估细胞类型富集结果是否
    对基因选择阈值稳健。结果用于 Figure E2 的热力图。

    参数：
        loadings_df: DataFrame，含 Gene 和 Weight 列（PLS1 基因权重排序表）
        cell_sets: dict，细胞类型标记基因集（PLAN1_CELLTYPE_MARKERS）
        top_ns: 基因选择阈值元组（默认 20, 30, 40）

    返回：DataFrame，含 TopN, Direction, Set_Name, FDR 等列
    """
    universe = loadings_df['Gene'].dropna().astype(str).str.upper().tolist()
    out_rows = []
    for n in top_ns:
        top_genes = loadings_df.sort_values('Weight', ascending=False).head(n)['Gene'].dropna().astype(str).str.upper().tolist()
        bottom_genes = loadings_df.sort_values('Weight', ascending=True).head(n)['Gene'].dropna().astype(str).str.upper().tolist()
        for direction, genes in [('Positive', top_genes), ('Negative', bottom_genes)]:
            ora = _hypergeom_ora(genes, universe, cell_sets, f'{direction}_Top{n}')
            if ora.empty:
                continue
            ora['TopN'] = int(n)
            ora['Direction'] = direction
            out_rows.append(ora)
    if not out_rows:
        return pd.DataFrame()
    return pd.concat(out_rows, ignore_index=True)


def _save_plan1_workflow_figure(path):
    """
    Supplementary Figure 1: AHBA 机制注释流程示意图。

    展示五个关键步骤的流程框：
    1. MIND 节点异常图谱 → 2. AHBA 表达矩阵与 atlas 对齐 →
    3. PLS + spatial null 检验 → 4. 基因排序（正/负向）→
    5. 通路 + 细胞类型富集

    参数：path: 输出 PNG 文件路径
    """
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.axis('off')
    steps = [
        'MIND nodal\nabnormality map',
        'AHBA expression\nparcellation alignment',
        'PLS + spatial\nnull testing',
        'Ranked genes\n(positive/negative)',
        'Pathway + cell-type\nenrichment',
    ]
    x = np.linspace(0.08, 0.92, len(steps))
    for i, (xi, label) in enumerate(zip(x, steps)):
        ax.text(xi, 0.5, label, ha='center', va='center', fontsize=11,
                bbox=dict(boxstyle='round,pad=0.45', facecolor='white', edgecolor='black', linewidth=1.0))
        if i < len(steps) - 1:
            ax.annotate('', xy=(x[i + 1] - 0.07, 0.5), xytext=(xi + 0.07, 0.5),
                        arrowprops=dict(arrowstyle='->', lw=1.2, color='black'))
    fig.suptitle('Supplementary Figure 1 | Aim3 Mechanism Workflow', fontsize=13)
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def _save_plan2_ahba_coverage_figure(atlas_labels, abnormality_map, region_scores, out_dir):
    """
    Supplementary Figure 2: AHBA 数据覆盖可视化。

    三个面板：
    - Panel 1: 皮层 parcel 覆盖率（绿=双覆盖，橙=单覆盖，红=无覆盖）
    - Panel 2: 半球分布（L/R parcel 数量）
    - Panel 3: 结构类型分布（cortex/subcortex）

    参数：
        atlas_labels: atlas 标签 DataFrame
        abnormality_map: 异常图谱 DataFrame
        region_scores: PLS1 regional scores 数组
        out_dir: 输出目录

    返回：图片路径
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), constrained_layout=True)

    # Panel 1: cortical parcel coverage
    has_abnorm = abnormality_map['Abnormality_Score'].notna().astype(int).values
    has_pls = pd.Series(region_scores).notna().astype(int).values
    coverage = has_abnorm + has_pls  # 0=none, 1=partial, 2=both
    colors_map = {0: '#d32f2f', 1: '#ffa726', 2: '#4caf50'}
    bar_colors = [colors_map.get(c, '#cccccc') for c in coverage]
    axes[0].bar(atlas_labels['id'].astype(str), np.ones(len(atlas_labels)), color=bar_colors, linewidth=0)
    axes[0].set_title('Parcel coverage (green=both, orange=partial)')
    axes[0].set_xlabel('ROI ID')
    axes[0].set_ylabel('')
    axes[0].tick_params(axis='x', labelrotation=90, labelsize=5)
    axes[0].set_yticks([])

    # Panel 2: hemisphere distribution
    hemi_counts = atlas_labels['hemisphere'].value_counts()
    axes[1].bar(hemi_counts.index, hemi_counts.values, color=[GROUP_COLORS[2], GROUP_COLORS[1]])
    axes[1].set_title(f'Hemisphere distribution (n={len(atlas_labels)})')
    axes[1].set_ylabel('Number of parcels')

    # Panel 3: structure type distribution
    if 'structure' in atlas_labels.columns:
        struct_counts = atlas_labels['structure'].value_counts()
        axes[2].bar(struct_counts.index, struct_counts.values, color=GROUP_COLORS[0])
        axes[2].set_title('Structure type distribution')
        axes[2].set_ylabel('Number of parcels')
    else:
        axes[2].text(0.5, 0.5, 'Structure info\nnot available', ha='center', va='center', fontsize=11)
        axes[2].axis('off')

    for ax in axes:
        ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)

    path = os.path.join(out_dir, 'Supplementary_Figure_2_AHBA_Coverage.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return path


def _save_plan3_spatial_null_robustness_figure(null_r2_arr, obs_cv_r2, null_r_arr, obs_cv_r, out_dir):
    """
    Supplementary Figure 3: 空间 null 分布稳健性图。

    两个面板：
    - Panel 1: CV R² 的 null 分布直方图 + 观测值竖线 + p 值标注
    - Panel 2: |R| 的 null 分布直方图 + 观测值竖线 + p 值

    参数：
        null_r2_arr: null 分布的 CV R² 数组
        obs_cv_r2: 观测到的 CV R²
        null_r_arr: null 分布的 R 数组
        obs_cv_r: 观测到的 R
        out_dir: 输出目录

    返回：图片路径
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)

    # Panel 1: CV R2 null distribution
    axes[0].hist(null_r2_arr, bins=30, color=GROUP_COLORS[0], alpha=0.8, edgecolor='white')
    axes[0].axvline(obs_cv_r2, color='black', linestyle='--', linewidth=2, label=f'Observed CV R² = {obs_cv_r2:.4f}')
    p_r2 = float((np.sum(null_r2_arr >= obs_cv_r2) + 1) / (len(null_r2_arr) + 1))
    axes[0].set_title(f'Spatial null: CV R² | p = {p_r2:.4f}')
    axes[0].set_xlabel('Cross-validated R²')
    axes[0].set_ylabel('Count')
    axes[0].legend(frameon=False, fontsize=9)

    # Panel 2: correlation null distribution
    valid_r = null_r_arr[np.isfinite(null_r_arr)]
    if len(valid_r) > 0:
        axes[1].hist(np.abs(valid_r), bins=30, color=GROUP_COLORS[2], alpha=0.8, edgecolor='white')
        axes[1].axvline(abs(obs_cv_r), color='black', linestyle='--', linewidth=2, label=f'|Observed R| = {abs(obs_cv_r):.4f}')
        p_r = float((np.sum(np.abs(valid_r) >= abs(obs_cv_r)) + 1) / (len(valid_r) + 1))
        axes[1].set_title(f'Spatial null: |R| | p = {p_r:.4f}')
        axes[1].set_xlabel('|Correlation|')
        axes[1].set_ylabel('Count')
        axes[1].legend(frameon=False, fontsize=9)
    else:
        axes[1].text(0.5, 0.5, 'Correlation null\nnot available', ha='center', va='center', fontsize=11)
        axes[1].axis('off')

    for ax in axes:
        ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)

    path = os.path.join(out_dir, 'Supplementary_Figure_3_Spatial_Null_Robustness.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return path


def _save_plan4_lodo_sensitivity_figure(atlas, atlas_labels, abnormality_map, expr_df,
                                         numeric_expr, X, Y, cv, PLAN1_PLS_N_COMPONENTS,
                                         gene_symbol_map, pathway_sets, cell_sets,
                                         top_n, out_dir, donors_used='all'):
    """
    Supplementary Figure 4: Leave-One-Donor-Out (LODO) 敏感性分析。

    逐一移除每个 AHBA 捐赠者后重新拟合 PLS，检验结果是否受单一捐赠者驱动。
    三个面板：
    - Panel 1: LODO CV R²（与全模型对比）
    - Panel 2: Top-N 基因重叠率（正/负向分别展示）
    - Panel 3: 热力图汇总（CV R² × 正/负向 overlap）

    参数：
        atlas: abagen atlas dict
        atlas_labels: atlas 标签 DataFrame
        abnormality_map: 异常图谱 DataFrame
        expr_df: 完整表达矩阵 DataFrame
        numeric_expr: 数值型表达矩阵（过滤后）
        X, Y: 标准化后的 PLS 输入矩阵
        cv: KFold 交叉验证对象
        PLAN1_PLS_N_COMPONENTS: PLS 成分数
        gene_symbol_map: Entrez ID → 基因符号映射
        pathway_sets, cell_sets: 通路/细胞类型基因集
        top_n: 取 top-N 基因做 overlap
        out_dir: 输出目录
        donors_used: 使用的捐赠者列表或 'all'

    返回：图片路径，失败返回 None
    """
    try:
        # Determine donor list
        if isinstance(donors_used, list) and len(donors_used) >= 2:
            all_donors_list = donors_used
        else:
            # Fetch donor list from abagen
            try:
                donor_info = abagen.fetchers.fetch_microarray(donor='all', data_dir=PLAN1_AHBA_CACHE_DIR)
                all_donors_list = [str(d) for d in donor_info.keys()] if isinstance(donor_info, dict) else []
            except Exception:
                all_donors_list = ['9861', '10021', '12876', '14380', '15496', '15697']

        if len(all_donors_list) < 2:
            print('  [Supp4] LODO skipped: fewer than 2 donors available')
            return None

        lodo_r2 = []
        lodo_top_pos_overlap = []
        lodo_top_neg_overlap = []
        donors_successful = []

        # Full model top genes for comparison
        full_pls = PLSRegression(n_components=min(PLAN1_PLS_N_COMPONENTS, X.shape[1], len(Y) - 1))
        full_pls.fit(X, Y)
        full_weights = full_pls.x_weights_[:, 0].copy()
        # 基因权重符号校正：仅用于富集分析（与主分析一致）
        if pearsonr(Y, full_pls.x_scores_[:, 0])[0] < 0:
            full_weights = -full_weights
        full_top_pos = set(gene_symbol_map.get(str(numeric_expr.columns[i]), str(numeric_expr.columns[i])).upper()
                           for i in np.argsort(full_weights)[-top_n:])
        full_top_neg = set(gene_symbol_map.get(str(numeric_expr.columns[i]), str(numeric_expr.columns[i])).upper()
                           for i in np.argsort(full_weights)[:top_n])

        for donor in all_donors_list:
            try:
                remaining = [d for d in all_donors_list if d != donor]
                lodo_expr = abagen.get_expression_data(
                    atlas['image'],
                    atlas_info=atlas['info'],
                    donors=remaining,
                    data_dir=PLAN1_AHBA_CACHE_DIR,
                    return_counts=False,
                    return_donors=False,
                    verbose=0,
                )
                lodo_df = lodo_expr.copy() if isinstance(lodo_expr, pd.DataFrame) else pd.DataFrame(lodo_expr)
                if lodo_df.shape[0] < lodo_df.shape[1]:
                    lodo_df = lodo_df.T
                if len(lodo_df) != len(atlas_labels):
                    lodo_df = lodo_df.iloc[:len(atlas_labels)]
                lodo_df.index = atlas_labels['id'].tolist()[:len(lodo_df)]
                lodo_df = lodo_df.loc[atlas_labels['id'].tolist()]

                lodo_num = lodo_df.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')
                lodo_num = lodo_num.fillna(lodo_num.mean(axis=0))
                var = lodo_num.var(axis=0, ddof=0)
                lodo_num = lodo_num.loc[:, var > 0]

                if lodo_num.shape[1] < 10:
                    continue

                lodo_X = StandardScaler().fit_transform(lodo_num.values)
                lodo_cv_pred = cross_val_predict(
                    PLSRegression(n_components=min(PLAN1_PLS_N_COMPONENTS, lodo_X.shape[1], len(Y) - 1)),
                    lodo_X, Y, cv=cv).ravel()
                lodo_r2.append(float(r2_score(Y, lodo_cv_pred)))

                lodo_pls = PLSRegression(n_components=min(PLAN1_PLS_N_COMPONENTS, lodo_X.shape[1], len(Y) - 1))
                lodo_pls.fit(lodo_X, Y)
                lodo_w = lodo_pls.x_weights_[:, 0].copy()
                # 基因权重符号校正：仅用于富集分析（与主分析一致）
                if pearsonr(Y, lodo_pls.x_scores_[:, 0])[0] < 0:
                    lodo_w = -lodo_w

                lodo_gene_map = {}
                for idx_c, col in enumerate(lodo_num.columns):
                    key = str(col)
                    try:
                        key = str(int(float(col)))
                    except Exception:
                        pass
                    lodo_gene_map[idx_c] = gene_symbol_map.get(key, key).upper()

                lodo_pos = set(lodo_gene_map.get(i, str(i)) for i in np.argsort(lodo_w)[-top_n:])
                lodo_neg = set(lodo_gene_map.get(i, str(i)) for i in np.argsort(lodo_w)[:top_n])

                lodo_top_pos_overlap.append(len(full_top_pos & lodo_pos) / max(len(full_top_pos), 1))
                lodo_top_neg_overlap.append(len(full_top_neg & lodo_neg) / max(len(full_top_neg), 1))
                donors_successful.append(donor)
            except Exception as e:
                print(f'  [Supp4] Donor {donor} failed: {e}')
                continue

        if len(donors_successful) < 2:
            print(f'  [Supp4] LODO skipped: only {len(donors_successful)} donors succeeded')
            return None

        fig, axes = plt.subplots(1, 3, figsize=(17, 5), constrained_layout=True)

        full_cv_r2 = float(r2_score(Y, cross_val_predict(
            PLSRegression(n_components=min(PLAN1_PLS_N_COMPONENTS, X.shape[1], len(Y) - 1)), X, Y, cv=cv).ravel()))

        x_labels = [f'w/o {d}' for d in donors_successful]
        axes[0].bar(x_labels, lodo_r2, color=GROUP_COLORS[0], alpha=0.85)
        axes[0].axhline(full_cv_r2, color='black', linestyle='--', linewidth=1.5, label=f'Full model ({full_cv_r2:.3f})')
        axes[0].set_title('LODO: CV R²')
        axes[0].set_ylabel('Cross-validated R²')
        axes[0].legend(frameon=False, fontsize=8)
        axes[0].tick_params(axis='x', rotation=30)

        axes[1].bar(x_labels, [o * 100 for o in lodo_top_pos_overlap], color=GROUP_COLORS[3], alpha=0.85, label='Positive')
        axes[1].bar(x_labels, [o * 100 for o in lodo_top_neg_overlap], color=GROUP_COLORS[2], alpha=0.55, label='Negative')
        axes[1].set_title(f'LODO: Top-{top_n} gene overlap (%)')
        axes[1].set_ylabel('Overlap with full model (%)')
        axes[1].legend(frameon=False, fontsize=8)
        axes[1].tick_params(axis='x', rotation=30)

        heatmap_data = np.array([lodo_r2, [o * 100 for o in lodo_top_pos_overlap], [o * 100 for o in lodo_top_neg_overlap]])
        im = axes[2].imshow(heatmap_data, aspect='auto', cmap=CMAP_SEQUENTIAL)
        axes[2].set_xticks(np.arange(len(donors_successful)))
        axes[2].set_xticklabels([f'w/o {d}' for d in donors_successful], rotation=30, fontsize=8)
        axes[2].set_yticks([0, 1, 2])
        axes[2].set_yticklabels(['CV R²', 'Pos overlap %', 'Neg overlap %'])
        axes[2].set_title('LODO sensitivity summary')
        plt.colorbar(im, ax=axes[2], fraction=0.05, pad=0.02)

        for ax in axes:
            ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)

        path = os.path.join(out_dir, 'Supplementary_Figure_4_LODO_Sensitivity.png')
        fig.savefig(path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        return path
    except Exception as e:
        print(f'  [Supp4] LODO analysis skipped: {e}')
        return None


def _save_plan5_enrichment_cnet_figure(pathway_df, cell_df, loadings_df, out_dir):
    """
    Supplementary Figure 5: 富集 cnet（connection network）图。

    左侧为通路/细胞类型节点，右侧为基因节点，连线表示关联关系。
    节点颜色按 -log10(FDR) 强度编码，用于直观展示哪些基因集与哪些基因关联。

    参数：
        pathway_df: 通路富集结果 DataFrame
        cell_df: 细胞类型富集结果 DataFrame
        loadings_df: PLS1 基因权重 DataFrame（含 Gene, Weight 列）
        out_dir: 输出目录

    返回：图片路径
    """
    fig, axes = plt.subplots(1, 2, figsize=(16, 8), constrained_layout=True)

    for ax_idx, (enrich_df, title_prefix) in enumerate([(pathway_df, 'Pathway'), (cell_df, 'Cell-type')]):
        ax = axes[ax_idx]
        if enrich_df.empty:
            ax.text(0.5, 0.5, f'{title_prefix} enrichment\nnot available', ha='center', va='center', fontsize=11)
            ax.axis('off')
            continue

        top_terms = enrich_df.sort_values('FDR').head(8)
        if top_terms.empty:
            ax.axis('off')
            continue

        # Build a simple network: terms on the left, genes on the right
        term_names = top_terms['Set_Name'].tolist()
        term_y = np.linspace(0.1, 0.9, len(term_names))

        # Get genes associated with each term
        top_genes_set = set()
        for _, row in top_terms.iterrows():
            gene_list_label = row['Gene_List']
            if 'Positive' in gene_list_label:
                genes = loadings_df.sort_values('Weight', ascending=False).head(20)['Gene'].tolist()
            else:
                genes = loadings_df.sort_values('Weight', ascending=True).head(20)['Gene'].tolist()
            # Take a subset for visualization
            top_genes_set.update(genes[:5])

        gene_names = sorted(top_genes_set)[:15]
        gene_y = np.linspace(0.1, 0.9, len(gene_names))

        # Draw term nodes
        for i, (name, y) in enumerate(zip(term_names, term_y)):
            fdr_val = top_terms.iloc[i]['FDR']
            color_intensity = min(-np.log10(max(fdr_val, 1e-12)) / 5, 1.0)
            ax.scatter(0.15, y, s=200, c=[plt.cm.YlOrRd(color_intensity)], edgecolors='black', linewidth=0.8, zorder=3)
            ax.text(0.02, y, name, ha='right', va='center', fontsize=7, clip_on=False)

        # Draw gene nodes
        for i, (name, y) in enumerate(zip(gene_names, gene_y)):
            ax.scatter(0.85, y, s=80, c=[GROUP_COLORS[2]], edgecolors='black', linewidth=0.5, zorder=3)
            ax.text(0.98, y, name, ha='left', va='center', fontsize=6, clip_on=False)

        # Draw connections (simplified: connect each term to all genes)
        for ti, trow in top_terms.iterrows():
            t_idx = term_names.index(trow['Set_Name'])
            for gi, gene in enumerate(gene_names):
                ax.plot([0.18, 0.82], [term_y[t_idx], gene_y[gi]],
                        color='gray', alpha=0.15, linewidth=0.5, zorder=1)

        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(0, 1)
        ax.set_title(f'{title_prefix}-gene cnet (top terms)')
        ax.axis('off')

    path = os.path.join(out_dir, 'Supplementary_Figure_5_Enrichment_Cnet.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return path


def _fit_plan1_pls_mechanism():
    """
    AHBA/PLS 机制注释（模块 5：4.4.5）。

    完整流程：
    1. 加载区域异常图谱（来自 Step2 的 nodal effect size）
    2. 获取 AHBA 基因表达数据（abagen + Desikan-Killiany atlas）
    3. PLS 回归：以区域异常值为 Y，全基因表达矩阵为 X
    4. 半球保持置换 spatial null 检验（避免空间自相关偏倚）
    5. 提取 PLS1 基因权重，排序得到正/负向基因集
    6. 通路富集（GO-BP/突触/线粒体/蛋白稳态/神经炎症等）
    7. 细胞类型注释（兴奋性/抑制性神经元、星形胶质细胞、小胶质细胞等）
    8. LODO 敏感性分析（leave-one-donor-out）
    9. 生成 Figures A-E + Supplementary 1-5 + GO-BP dot plot

    返回：dict，含 atlas, region_df, loadings_df, pathway_df, cell_df, gobp_path 等
    """
    atlas, atlas_labels, abnormality_map, detail_df = _load_plan1_abnormality_map()
    donors = _parse_ahba_donors(PLAN1_ALLEN_DONORS_ENV)
    gene_group = os.getenv('STEP4_PLAN1_PLS_GENE_GROUP', 'brain').strip() or 'brain'
    gene_symbol_map = _load_abagen_gene_symbol_map()

    expr = abagen.get_expression_data(
        atlas['image'],
        atlas_info=atlas['info'],
        donors=donors,
        data_dir=PLAN1_AHBA_CACHE_DIR,
        return_counts=False,
        return_donors=False,
        verbose=0,
    )
    expr_df = expr.copy() if isinstance(expr, pd.DataFrame) else pd.DataFrame(expr)
    # 修正转置逻辑：abagen 返回 (regions, genes) 或 (genes, regions)
    # 通过检查哪一维与 atlas 脑区数匹配来判断方向
    if expr_df.shape[0] == len(atlas_labels):
        pass  # 已经是 (regions, genes)，无需转置
    elif expr_df.shape[1] == len(atlas_labels):
        expr_df = expr_df.T  # 从 (genes, regions) 转为 (regions, genes)
    elif expr_df.shape[0] < expr_df.shape[1]:
        expr_df = expr_df.T  # 降级猜测：行数少的维度可能是脑区

    if len(expr_df) != len(atlas_labels):
        expr_df = expr_df.iloc[:len(atlas_labels)].copy()
    expr_df.index = atlas_labels['id'].tolist()[:len(expr_df)]
    expr_df = expr_df.loc[atlas_labels['id'].tolist()]

    y = abnormality_map.set_index('id')['Abnormality_Score'].reindex(atlas_labels['id']).astype(float).values
    hemispheres = atlas_labels['hemisphere'].values
    if np.isnan(y).any():
        y = pd.Series(y).fillna(np.nanmean(y)).values

    numeric_expr = expr_df.apply(pd.to_numeric, errors='coerce')
    numeric_expr = numeric_expr.dropna(axis=1, how='all')
    numeric_expr = numeric_expr.fillna(numeric_expr.mean(axis=0))
    variance = numeric_expr.var(axis=0, ddof=0)
    numeric_expr = numeric_expr.loc[:, variance > 0]

    x_scaler = StandardScaler()
    y_scaler = StandardScaler()
    X = x_scaler.fit_transform(numeric_expr.values)
    Y = y_scaler.fit_transform(y.reshape(-1, 1)).ravel()

    n_splits = min(5, max(2, len(Y)))
    cv = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    pls = PLSRegression(n_components=min(PLAN1_PLS_N_COMPONENTS, X.shape[1], len(Y) - 1))
    cv_pred = cross_val_predict(pls, X, Y, cv=cv).ravel()
    obs_cv_r2 = float(r2_score(Y, cv_pred))
    obs_cv_r = float(pearsonr(Y, cv_pred)[0])

    full_pls = PLSRegression(n_components=min(PLAN1_PLS_N_COMPONENTS, X.shape[1], len(Y) - 1))
    full_pls.fit(X, Y)
    gene_weights = full_pls.x_weights_[:, 0].copy()
    region_scores = full_pls.x_scores_[:, 0].copy()
    predicted = full_pls.predict(X).ravel()

    # 基因权重符号校正：仅翻转 gene_weights，不翻转 region_scores
    # region_scores 保持原始分布（零中心），脑图通过 percentile 裁剪实现红蓝均衡
    # gene_weights 需要与 Y 方向一致：正权重 = 与高异常相关的基因（用于富集分析）
    if pearsonr(Y, region_scores)[0] < 0:
        gene_weights = -gene_weights

    null_r2 = []
    null_r = []
    for seed in range(PLAN1_PLS_N_PERM):
        perm_y = _hemisphere_preserving_permutation(Y, hemispheres, random_state=seed)
        perm_pls = PLSRegression(n_components=min(PLAN1_PLS_N_COMPONENTS, X.shape[1], len(Y) - 1))
        perm_cv_pred = cross_val_predict(perm_pls, X, perm_y, cv=cv).ravel()
        null_r2.append(float(r2_score(perm_y, perm_cv_pred)))
        try:
            null_r.append(float(pearsonr(perm_y, perm_cv_pred)[0]))
        except Exception:
            null_r.append(np.nan)

    # 计算置换检验 p 值：(观测值在 null 中的排名 + 1) / (总置换数 + 1)
    # +1 是为了避免 p=0（保守估计）
    null_r2_arr = np.asarray(null_r2, dtype=float)
    null_r_arr = np.asarray([x for x in null_r if np.isfinite(x)], dtype=float)
    p_null_r2 = float((np.sum(null_r2_arr >= obs_cv_r2) + 1) / (len(null_r2_arr) + 1))
    p_null_r = float((np.sum(np.abs(null_r_arr) >= abs(obs_cv_r)) + 1) / (len(null_r_arr) + 1)) if len(null_r_arr) else np.nan

    burden_series = abnormality_map.set_index('id')['Abnormality_Score'].reindex(atlas_labels['id']).astype(float)
    burden_corr = float(pearsonr(burden_series.values, region_scores)[0])
    burden_corr_p = float(pearsonr(burden_series.values, region_scores)[1])

    # Entrez ID → Gene Symbol 映射：需要处理各种格式（'1234', '1234.0', 'ABCD'）
    filtered_gene_ids = [str(col) for col in numeric_expr.columns.tolist()]
    filtered_gene_symbols = []
    for raw_label in filtered_gene_ids:
        lookup_key = raw_label
        if raw_label.endswith('.0'):       # 处理 pandas 自动加的 '.0' 后缀
            lookup_key = raw_label[:-2]
        try:
            lookup_key = str(int(float(raw_label)))  # 尝试转为整数 ID
        except Exception:
            lookup_key = raw_label                    # 非数值标签保持原样
        filtered_gene_symbols.append(gene_symbol_map.get(lookup_key, raw_label).upper())

    loadings_df = pd.DataFrame({
        'Gene_ID': filtered_gene_ids,
        'Gene': filtered_gene_symbols,
        'Weight': gene_weights,
    })
    loadings_df['Abs_Weight'] = loadings_df['Weight'].abs()
    loadings_df = loadings_df.sort_values('Weight', ascending=False).reset_index(drop=True)
    loadings_df['Rank'] = np.arange(1, len(loadings_df) + 1)
    loadings_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_PLS_Gene_Loadings.csv'), index=False, encoding='utf-8-sig')

    region_df = atlas_labels.copy()
    region_df['Abnormality_Score'] = burden_series.values
    region_df['PLS1_Score'] = region_scores
    region_df['PLS1_Predicted'] = predicted
    region_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_PLS_Region_Scores.csv'), index=False, encoding='utf-8-sig')

    mechanism_overlay_dir = ensure_dir(os.path.join(BASE_OUTPUT_DIR, 'Mechanism'))
    mechanism_overlay_path = _save_ahba_overlay(
        mechanism_overlay_dir,
        region_df['PLS1_Score'],
        atlas['image'],
        atlas['info'],
        f'PLS1 | donors={donors} | gene group={gene_group}',
    )

    null_df = pd.DataFrame({'Permutation': np.arange(1, len(null_r2_arr) + 1), 'Null_CV_R2': null_r2_arr})
    null_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_PLS_Null_Distribution.csv'), index=False, encoding='utf-8-sig')

    pos_genes = loadings_df.sort_values('Weight', ascending=False).head(PLAN1_PLS_TOP_N)['Gene'].tolist()
    neg_genes = loadings_df.sort_values('Weight', ascending=True).head(PLAN1_PLS_TOP_N)['Gene'].tolist()

    pathway_sets = PLAN1_PATHWAY_THEMES
    cell_sets = PLAN1_CELLTYPE_MARKERS
    pathway_pos = _hypergeom_ora(pos_genes, loadings_df['Gene'].tolist(), pathway_sets, 'Positive PLS1')
    pathway_neg = _hypergeom_ora(neg_genes, loadings_df['Gene'].tolist(), pathway_sets, 'Negative PLS1')
    cell_pos = _hypergeom_ora(pos_genes, loadings_df['Gene'].tolist(), cell_sets, 'Positive PLS1')
    cell_neg = _hypergeom_ora(neg_genes, loadings_df['Gene'].tolist(), cell_sets, 'Negative PLS1')

    pathway_df = pd.concat([pathway_pos, pathway_neg], ignore_index=True) if not pathway_pos.empty or not pathway_neg.empty else pd.DataFrame()
    cell_df = pd.concat([cell_pos, cell_neg], ignore_index=True) if not cell_pos.empty or not cell_neg.empty else pd.DataFrame()

    if not pathway_df.empty:
        pathway_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Pathway_Enrichment.csv'), index=False, encoding='utf-8-sig')
    if not cell_df.empty:
        cell_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_CellType_Enrichment.csv'), index=False, encoding='utf-8-sig')

    figure_dir = ensure_dir(os.path.join(BASE_OUTPUT_DIR, 'Figure_Suite'))
    supp_dir = ensure_dir(os.path.join(BASE_OUTPUT_DIR, 'Supplementary'))

    network_df = _plan1_network_abnormality_summary(abnormality_map)
    network_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Network_Abnormality_Summary.csv'), index=False, encoding='utf-8-sig')

    rank_df = abnormality_map[['id', 'label', 'Abnormality_Score', 'Mean_Abs_T']].copy()
    rank_df['Abs_Abnormality'] = rank_df['Abnormality_Score'].abs()
    rank_df = rank_df.sort_values('Abs_Abnormality', ascending=False).reset_index(drop=True)
    rank_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Regionwise_Abnormality_Rank.csv'), index=False, encoding='utf-8-sig')

    comp_max = min(3, X.shape[1], len(Y) - 1)
    comp_rows = []
    if comp_max >= 1:
        for comp in range(1, comp_max + 1):
            cv_comp = cross_val_predict(PLSRegression(n_components=comp), X, Y, cv=cv).ravel()
            comp_rows.append({'Component': f'PLS{comp}', 'CV_R2': float(r2_score(Y, cv_comp))})
    else:
        comp_rows.append({'Component': 'PLS1', 'CV_R2': float(obs_cv_r2)})
    comp_df = pd.DataFrame(comp_rows)
    comp_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_PLS_Component_Explained.csv'), index=False, encoding='utf-8-sig')

    cell_sens_df = _plan1_celltype_sensitivity(loadings_df, PLAN1_CELLTYPE_MARKERS)
    if not cell_sens_df.empty:
        cell_sens_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_CellType_Enrichment_Sensitivity.csv'), index=False, encoding='utf-8-sig')

    # Figure A: abnormality map summary panels
    fig_a, axes_a = plt.subplots(1, 3, figsize=(20, 5), constrained_layout=True)
    try:
        a1_img = plt.imread(mechanism_overlay_path)
        axes_a[0].imshow(a1_img)
        axes_a[0].axis('off')
    except Exception:
        axes_a[0].axis('off')
    axes_a[0].set_title('A1. MIND Abnormality Surface Map')

    show_net = network_df.dropna(subset=['Mean_Abnormality']).copy()
    axes_a[1].barh(show_net['Network'], show_net['Mean_Abnormality'], color=GROUP_COLORS[0])
    axes_a[1].set_title('A2. Network-level Abnormality')
    axes_a[1].set_xlabel('Mean abnormality score')

    top_regions = rank_df.head(10).sort_values('Abs_Abnormality', ascending=True)
    axes_a[2].barh(top_regions['label'], top_regions['Abnormality_Score'], color=GROUP_COLORS[3])
    axes_a[2].axvline(0, color='black', linewidth=1)
    axes_a[2].set_title('A3. Top-10 Region-wise Ranking')
    axes_a[2].set_xlabel('Abnormality score')
    fig_a.savefig(os.path.join(figure_dir, 'Figure_A_MIND_Abnormality_Map.png'), dpi=300, bbox_inches='tight')
    plt.close(fig_a)

    # Figure B: PLS core results
    fig_b, axes_b = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    axes_b[0, 0].bar(comp_df['Component'], comp_df['CV_R2'], color=GROUP_COLORS[2])
    axes_b[0, 0].set_title('B1. PLS Component Explained Variance (CV R2)')
    axes_b[0, 0].set_ylabel('Cross-validated R2')

    axes_b[0, 1].hist(null_r2_arr, bins=28, color=GROUP_COLORS[0], alpha=0.8)
    axes_b[0, 1].axvline(obs_cv_r2, color='black', linestyle='--', linewidth=2)
    axes_b[0, 1].set_title(f'B2. Spatial Null Distribution | p={p_null_r2:.3f}')
    axes_b[0, 1].set_xlabel('Null CV R2')

    axes_b[1, 0].scatter(region_df['Abnormality_Score'], region_df['PLS1_Score'], s=30, alpha=0.8, color=GROUP_COLORS[2])
    axes_b[1, 0].set_title(f'B3. Region-wise association | r={burden_corr:.3f}, p={burden_corr_p:.3g}')
    axes_b[1, 0].set_xlabel('MIND abnormality')
    axes_b[1, 0].set_ylabel('PLS1 regional score')

    try:
        b4_img = plt.imread(mechanism_overlay_path)
        axes_b[1, 1].imshow(b4_img)
        axes_b[1, 1].axis('off')
    except Exception:
        axes_b[1, 1].axis('off')
    axes_b[1, 1].set_title('B4. PLS1 Surface Projection')
    fig_b.savefig(os.path.join(figure_dir, 'Figure_B_PLS_Spatial_Null.png'), dpi=300, bbox_inches='tight')
    plt.close(fig_b)

    # Figure C: gene-level results
    fig_c, axes_c = plt.subplots(1, 3, figsize=(20, 6), constrained_layout=True)
    top_pos = loadings_df.sort_values('Weight', ascending=False).head(10)
    top_neg = loadings_df.sort_values('Weight', ascending=True).head(10)
    c1 = pd.concat([top_neg, top_pos], ignore_index=True)
    c1_colors = [GROUP_COLORS[1]] * len(top_neg) + [GROUP_COLORS[3]] * len(top_pos)
    axes_c[0].barh(c1['Gene'], c1['Weight'], color=c1_colors)
    axes_c[0].axvline(0, color='black', linewidth=1)
    axes_c[0].set_title('C1. PLS1 Gene Weight Ranking')

    heat_ids = list(dict.fromkeys(top_pos['Gene_ID'].tolist() + top_neg['Gene_ID'].tolist()))
    col_lookup = {}
    for col in numeric_expr.columns:
        col_lookup[str(col)] = col
        try:
            col_lookup[str(int(float(col)))] = col
        except Exception:
            pass
    heat_cols_real = [col_lookup[c] for c in heat_ids if c in col_lookup]
    heat_expr = numeric_expr[heat_cols_real].copy() if heat_cols_real else pd.DataFrame(index=numeric_expr.index)
    if not heat_expr.empty and heat_expr.shape[1] > 0:
        net_blocks = []
        net_names = []
        for net_name, roi_ids in YEO7_MAP.items():
            sub = heat_expr.loc[heat_expr.index.intersection(roi_ids)]
            if sub.empty:
                continue
            net_blocks.append(sub.mean(axis=0).values)
            net_names.append(net_name)
        if net_blocks:
            heat_arr = np.vstack(net_blocks)
            z_arr = (heat_arr - heat_arr.mean()) / (heat_arr.std() + 1e-8)
            im = axes_c[1].imshow(z_arr, aspect='auto', cmap=CMAP_DIVERGING)
            axes_c[1].set_yticks(np.arange(len(net_names)))
            axes_c[1].set_yticklabels(net_names)
            axes_c[1].set_xticks(np.arange(heat_arr.shape[1]))
            axes_c[1].set_xticklabels([str(x) for x in heat_cols_real[:heat_arr.shape[1]]], rotation=90, fontsize=6)
            axes_c[1].set_title('C2. Top-gene expression by network')
            plt.colorbar(im, ax=axes_c[1], fraction=0.05, pad=0.02, label='z-scored expression')
        else:
            axes_c[1].text(0.5, 0.5, 'No network-level\nexpression data', ha='center', va='center', fontsize=10)
            axes_c[1].axis('off')
    else:
        axes_c[1].text(0.5, 0.5, 'No matching gene\ncolumns found', ha='center', va='center', fontsize=10)
        axes_c[1].axis('off')

    # C3: formatted gene summary table
    c3_genes = loadings_df[['Gene', 'Weight', 'Abs_Weight']].copy().head(10)
    c3_genes = c3_genes.sort_values('Weight', ascending=False)
    axes_c[2].axis('off')
    axes_c[2].set_title('C3. Top gene summary')
    if not c3_genes.empty:
        cell_text = [[r.Gene, f'{r.Weight:+.4f}', f'{r.Abs_Weight:.4f}'] for r in c3_genes.itertuples()]
        tbl = axes_c[2].table(
            cellText=cell_text,
            colLabels=['Gene', 'PLS1 Weight', '|Weight|'],
            cellLoc='center',
            loc='center',
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1.0, 1.3)
        for (row, col), cell in tbl.get_celld().items():
            if row == 0:
                cell.set_facecolor('#e0e0e0')
                cell.set_text_props(weight='bold')
            elif row <= 3:
                cell.set_facecolor('#fff3e0')
    fig_c.savefig(os.path.join(figure_dir, 'Figure_C_Gene_Level_Results.png'), dpi=300, bbox_inches='tight')
    plt.close(fig_c)

    # Figure D: pathway enrichment (positive / negative)
    fig_d, axes_d = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    if not pathway_df.empty:
        for j, gene_list in enumerate(['Positive PLS1', 'Negative PLS1']):
            sub = pathway_df[pathway_df['Gene_List'] == gene_list].sort_values('FDR').head(10)
            if sub.empty:
                axes_d[j].axis('off')
                continue
            sc = axes_d[j].scatter(sub['Gene_Ratio'], sub['Set_Name'], s=sub['Overlap'].clip(lower=1) * 35,
                                   c=-np.log10(sub['FDR'].clip(lower=1e-12)), cmap=CMAP_SEQUENTIAL)
            axes_d[j].set_title(f'D{j+1}. {gene_list} pathway enrichment')
            axes_d[j].set_xlabel('Gene ratio')
            axes_d[j].set_ylabel('Pathway')
            plt.colorbar(sc, ax=axes_d[j], fraction=0.05, pad=0.02, label='-log10(FDR)')
    else:
        axes_d[0].axis('off')
        axes_d[1].axis('off')
    fig_d.savefig(os.path.join(figure_dir, 'Figure_D_Pathway_Enrichment.png'), dpi=300, bbox_inches='tight')
    plt.close(fig_d)

    # Standalone GO-BP dot plot
    gobp_path = _save_gobp_dotplot(pathway_df, figure_dir)

    # Figure E: cell-type enrichment and sensitivity heatmap
    fig_e, axes_e = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)
    if not cell_df.empty:
        show_cell = cell_df.sort_values('FDR').head(14)
        sc = axes_e[0].scatter(show_cell['Odds_Ratio'].clip(lower=0), show_cell['Set_Name'],
                               s=show_cell['Overlap'].clip(lower=1) * 35,
                               c=-np.log10(show_cell['FDR'].clip(lower=1e-12)), cmap=CMAP_SEQUENTIAL)
        axes_e[0].set_title('E1. Cell-type enrichment bubble plot')
        axes_e[0].set_xlabel('Odds ratio')
        axes_e[0].set_ylabel('Cell type')
        plt.colorbar(sc, ax=axes_e[0], fraction=0.05, pad=0.02, label='-log10(FDR)')
    else:
        axes_e[0].axis('off')

    if not cell_sens_df.empty:
        # Cross-dataset style heatmap: cell types × gene selection strategies
        sens = cell_sens_df.groupby(['Set_Name', 'Direction', 'TopN'])['FDR'].min().reset_index()
        sens['Condition'] = sens['Direction'] + '_Top' + sens['TopN'].astype(str)
        pivot = sens.pivot_table(index='Set_Name', columns='Condition', values='FDR', aggfunc='min')
        pivot = pivot.reindex(index=sorted(pivot.index))
        # Sort columns logically
        col_order = sorted(pivot.columns, key=lambda x: (x.split('_')[0], int(x.split('Top')[1])))
        pivot = pivot[col_order]
        # Convert to -log10(FDR) for visualization
        plot_arr = -np.log10(pivot.clip(lower=1e-12).fillna(1.0).values)
        im = axes_e[1].imshow(plot_arr, aspect='auto', cmap=CMAP_SEQUENTIAL)
        axes_e[1].set_yticks(np.arange(len(pivot.index)))
        axes_e[1].set_yticklabels(pivot.index)
        axes_e[1].set_xticks(np.arange(len(pivot.columns)))
        axes_e[1].set_xticklabels(pivot.columns, rotation=45, ha='right', fontsize=7)
        axes_e[1].set_title('E2. Cell-type enrichment robustness\n(across gene selection strategies)')
        plt.colorbar(im, ax=axes_e[1], fraction=0.05, pad=0.02, label='-log10(FDR)')
        # Mark significant cells
        for i in range(plot_arr.shape[0]):
            for j in range(plot_arr.shape[1]):
                if plot_arr[i, j] > -np.log10(0.05):
                    axes_e[1].text(j, i, '*', ha='center', va='center', fontsize=8, color='white')
    else:
        axes_e[1].axis('off')
    fig_e.savefig(os.path.join(figure_dir, 'Figure_E_CellType_Enrichment.png'), dpi=300, bbox_inches='tight')
    plt.close(fig_e)

    # Supplementary figures
    _save_plan1_workflow_figure(os.path.join(supp_dir, 'Supplementary_Figure_1_Workflow.png'))

    # Supp 2: AHBA coverage figure
    supp2_path = _save_plan2_ahba_coverage_figure(atlas_labels, abnormality_map, region_scores, supp_dir)
    supp2_df = atlas_labels.copy()
    supp2_df['Has_Abnormality'] = abnormality_map['Abnormality_Score'].notna().astype(int)
    supp2_df['Has_PLS1'] = pd.Series(region_scores).notna().astype(int)
    supp2_df.to_csv(os.path.join(supp_dir, 'Supplementary_Figure_2_AHBA_Coverage.csv'), index=False, encoding='utf-8-sig')

    # Supp 3: spatial null robustness figure
    supp3_path = _save_plan3_spatial_null_robustness_figure(null_r2_arr, obs_cv_r2, null_r_arr, obs_cv_r, supp_dir)
    supp3 = pd.DataFrame({'Null_CV_R2': null_r2_arr})
    supp3['Observed_CV_R2'] = obs_cv_r2
    supp3.to_csv(os.path.join(supp_dir, 'Supplementary_Figure_3_Spatial_Null.csv'), index=False, encoding='utf-8-sig')

    # Supp 4: leave-one-donor-out sensitivity
    supp4_path = _save_plan4_lodo_sensitivity_figure(
        atlas, atlas_labels, abnormality_map, expr_df, numeric_expr, X, Y, cv,
        PLAN1_PLS_N_COMPONENTS, gene_symbol_map, PLAN1_PATHWAY_THEMES, PLAN1_CELLTYPE_MARKERS,
        PLAN1_PLS_TOP_N, supp_dir, donors_used=donors)
    if not cell_sens_df.empty:
        donor_like = cell_sens_df.groupby(['Direction', 'TopN', 'Set_Name'])['FDR'].min().reset_index()
        donor_like.to_csv(os.path.join(supp_dir, 'Supplementary_Figure_4_Sensitivity_Heatmap.csv'), index=False, encoding='utf-8-sig')

    # Supp 5: enrichment cnet figure
    supp5_path = _save_plan5_enrichment_cnet_figure(pathway_df, cell_df, loadings_df, supp_dir)

    stats_rows = [
        {'Figure': 'A1', 'Statistic': 'Map_Type', 'Value': 'Nodal abnormality score (weighted T with p-weighting)'},
        {'Figure': 'A1', 'Statistic': 'Parcellation', 'Value': 'Desikan-Killiany'},
        {'Figure': 'A1', 'Statistic': 'Views', 'Value': 'L/R lateral + medial (2x2 grid)'},
        {'Figure': 'B1', 'Statistic': 'PLS1_CV_R2', 'Value': obs_cv_r2},
        {'Figure': 'B2', 'Statistic': 'Spatial_Null_p', 'Value': p_null_r2},
        {'Figure': 'B3', 'Statistic': 'Regionwise_r', 'Value': burden_corr},
        {'Figure': 'B3', 'Statistic': 'Regionwise_p', 'Value': burden_corr_p},
        {'Figure': 'C2', 'Statistic': 'Heatmap_Type', 'Value': 'Gene × Network z-scored expression'},
        {'Figure': 'C3', 'Statistic': 'Table_Type', 'Value': 'Top-10 gene PLS1 weights formatted table'},
        {'Figure': 'D', 'Statistic': 'Multiple_Correction', 'Value': 'BH-FDR'},
        {'Figure': 'D', 'Statistic': 'Gene_Universe_Size', 'Value': int(loadings_df['Gene'].nunique())},
        {'Figure': 'E', 'Statistic': 'Celltype_Marker_Sets', 'Value': int(len(PLAN1_CELLTYPE_MARKERS))},
        {'Figure': 'E', 'Statistic': 'Multiple_Correction', 'Value': 'BH-FDR'},
        {'Figure': 'E2', 'Statistic': 'Robustness_Type', 'Value': 'Cell-type × gene selection strategy heatmap'},
        {'Figure': 'Supp2', 'Statistic': 'Coverage_Type', 'Value': 'AHBA parcel + hemisphere + structure coverage'},
        {'Figure': 'Supp3', 'Statistic': 'Null_Type', 'Value': 'Spatial null CV R² and |R| distributions'},
        {'Figure': 'Supp4', 'Statistic': 'LODO_Type', 'Value': 'Leave-one-donor-out PLS sensitivity'},
        {'Figure': 'Supp5', 'Statistic': 'Cnet_Type', 'Value': 'Pathway-gene and cell-type-gene connection plot'},
        {'Figure': 'GOBP', 'Statistic': 'DotPlot_Type', 'Value': 'Standalone GO-BP pathway enrichment dot plot'},
    ]
    pd.DataFrame(stats_rows).to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Figure_Statistics_Annotations.csv'), index=False, encoding='utf-8-sig')

    top_pos = loadings_df.sort_values('Weight', ascending=False).head(12)
    top_neg = loadings_df.sort_values('Weight', ascending=True).head(12)

    fig, axes = plt.subplots(2, 3, figsize=(20, 11), constrained_layout=True)
    ax = axes[0, 0]
    # 使用全局配置颜色，使半球配色与项目主题一致（左/右分别对应蓝/橙风格）
    colors = [GROUP_COLORS[2] if hemi == 'L' else GROUP_COLORS[1] for hemi in region_df['hemisphere']]
    ax.bar(region_df['id'].astype(str), region_df['Abnormality_Score'], color=colors, linewidth=0)
    ax.set_title('MIND Abnormality Map')
    ax.set_xlabel('ROI')
    ax.set_ylabel('Composite score')
    ax.tick_params(axis='x', labelrotation=90, labelsize=6)

    ax = axes[0, 1]
    ax.hist(null_r2_arr, bins=24, color=GROUP_COLORS[0], alpha=0.75)
    ax.axvline(obs_cv_r2, color='black', linestyle='--', linewidth=2, label=f'obs R2={obs_cv_r2:.3f}')
    ax.set_title(f'PLS Spatial Null | p={p_null_r2:.3f}')
    ax.set_xlabel('Cross-validated R2')
    ax.set_ylabel('Count')
    ax.legend(frameon=False, fontsize=8)

    ax = axes[0, 2]
    ax.scatter(region_df['Abnormality_Score'], region_scores, s=34, alpha=0.8, color=GROUP_COLORS[2])
    ax.set_title(f'PLS1 Spatial Association | r={burden_corr:.3f}, p={burden_corr_p:.3g}')
    ax.set_xlabel('MIND abnormality')
    ax.set_ylabel('PLS1 regional score')

    ax = axes[1, 0]
    if not top_pos.empty or not top_neg.empty:
        plot_weights = pd.concat([
            top_neg[['Gene', 'Weight']],
            top_pos[['Gene', 'Weight']],
        ], ignore_index=True)
        plot_colors = [GROUP_COLORS[1]] * len(top_neg) + [GROUP_COLORS[3]] * len(top_pos)
        ax.barh(plot_weights['Gene'], plot_weights['Weight'], color=plot_colors)
        ax.axvline(0, color='black', linewidth=1)
        ax.set_title('Top PLS1 Gene Weights')
        ax.set_xlabel('Weight')
    else:
        ax.axis('off')

    ax = axes[1, 1]
    if not pathway_df.empty:
        show = pathway_df.sort_values('FDR').head(10)
        ax.scatter(show['Gene_Ratio'], show['Set_Name'], s=show['Overlap'].clip(lower=1) * 35, c=-np.log10(show['FDR'].clip(lower=1e-12)), cmap='viridis')
        ax.set_title('Pathway Enrichment')
        ax.set_xlabel('Gene ratio')
        ax.set_ylabel('Theme')
    else:
        ax.axis('off')

    ax = axes[1, 2]
    if not cell_df.empty:
        show = cell_df.sort_values('FDR').head(10)
        ax.scatter(show['Gene_Ratio'], show['Set_Name'], s=show['Overlap'].clip(lower=1) * 35, c=-np.log10(show['FDR'].clip(lower=1e-12)), cmap='magma')
        ax.set_title('Cell-type Enrichment')
        ax.set_xlabel('Gene ratio')
        ax.set_ylabel('Cell type')
    else:
        ax.axis('off')

    fig.savefig(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Mechanism_Annotation.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)

    mechanism_summary = pd.DataFrame([{
        'Metric': 'PLS1_CV_R2',
        'Value': obs_cv_r2,
    }, {
        'Metric': 'PLS1_CV_R',
        'Value': obs_cv_r,
    }, {
        'Metric': 'PLS1_null_p_R2',
        'Value': p_null_r2,
    }, {
        'Metric': 'PLS1_null_p_R',
        'Value': p_null_r,
    }, {
        'Metric': 'Burden_PLS1_r',
        'Value': burden_corr,
    }, {
        'Metric': 'Burden_PLS1_p',
        'Value': burden_corr_p,
    }])
    mechanism_summary.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Mechanism_Summary.csv'), index=False, encoding='utf-8-sig')

    mechanism_notes = os.path.join(BASE_OUTPUT_DIR, 'Plan1_Mechanism_Notes.txt')
    with open(mechanism_notes, 'w', encoding='utf-8') as f:
        f.write('PLAN 1: MIND mechanism annotation\n')
        f.write(f'Atlas: Desikan-Killiany | Donors={donors} | Gene group={gene_group}\n')
        f.write(f'PLS1 cross-validated R2={obs_cv_r2:.4f}, R={obs_cv_r:.4f}, null_p_R2={p_null_r2:.4f}\n')
        f.write(f'Burden-PLS1 correlation: r={burden_corr:.4f}, p={burden_corr_p:.4f}\n')
        if not pathway_df.empty:
            top_pathway = pathway_df.sort_values('FDR').iloc[0]
            f.write(f'Top pathway theme: {top_pathway["Set_Name"]} ({top_pathway["Gene_List"]}), FDR={top_pathway["FDR"]:.4f}\n')
        if not cell_df.empty:
            top_cell = cell_df.sort_values('FDR').iloc[0]
            f.write(f'Top cell-type theme: {top_cell["Set_Name"]} ({top_cell["Gene_List"]}), FDR={top_cell["FDR"]:.4f}\n')
        f.write(f'\nSupplementary figures:\n')
        f.write(f'  Supp 1 (workflow): {os.path.join(supp_dir, "Supplementary_Figure_1_Workflow.png")}\n')
        f.write(f'  Supp 2 (coverage): {supp2_path}\n')
        f.write(f'  Supp 3 (null robustness): {supp3_path}\n')
        f.write(f'  Supp 4 (LODO sensitivity): {supp4_path}\n')
        f.write(f'  Supp 5 (cnet enrichment): {supp5_path}\n')
        if gobp_path:
            f.write(f'  GO-BP dot plot: {gobp_path}\n')

    return {
        'atlas': atlas,
        'atlas_labels': atlas_labels,
        'abnormality_map': abnormality_map,
        'region_df': region_df,
        'loadings_df': loadings_df,
        'pathway_df': pathway_df,
        'cell_df': cell_df,
        'gobp_path': gobp_path,
        'mechanism_preview_path': os.path.join(BASE_OUTPUT_DIR, 'Plan1_Mechanism_Annotation.png'),
        'mechanism_overlay_path': mechanism_overlay_path,
        'mechanism_notes': mechanism_notes,
        'pls_plots': os.path.join(BASE_OUTPUT_DIR, 'Plan1_PLS_Region_Scores.csv'),
    }


def _create_plan1_unified_preview(stage_df, burden_stage_df, lme_df, preview_path, ahba_path=None):
    """
    Plan 1 统一预览图（2×3 网格）。

    第一行：
    - (0,0) Burden vs Residual 散点图（按组着色）
    - (0,1) Stage Expression 箱线图（prodromal vs PD）
    - (0,2) High-risk Phenotype 计数条形图

    第二行：
    - (1,0) UPDRS3 纵向散点图
    - (1,1) MoCA 纵向散点图
    - (1,2) Allen/AHBA 机制注释 overlay（若可用）

    参数：
        stage_df: 阶段表达数据
        burden_stage_df: burden-resilience 数据（含 Risk_Phenotype）
        lme_df: 纵向拟合数据
        preview_path: 输出 PNG 路径
        ahba_path: AHBA overlay 图片路径（可选）

    返回：matplotlib Figure 对象
    """
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), constrained_layout=True)
    fig.patch.set_facecolor('white')
    residual_df = burden_stage_df if burden_stage_df is not None and not burden_stage_df.empty else pd.DataFrame()

    if stage_df is not None and not stage_df.empty:
        ax = axes[0, 0]
        palette = {
            'prodromal_SAA+': GROUP_PALETTE.get('prodromal_SAA+', '#4c78a8'),
            'PD_SAA+': GROUP_PALETTE.get('PD_SAA+', '#f58518'),
        }
        scatter_df = residual_df if not residual_df.empty else stage_df
        if 'Residual' in scatter_df.columns:
            for name, group_df in scatter_df.groupby('Group_MIND'):
                ax.scatter(group_df['Burden_Score'], group_df['Residual'], s=26, alpha=0.75, label=name, color=palette.get(name))
            ax.axhline(0, color='black', linewidth=1, alpha=0.6)
            ax.set_ylabel('Residual')
            ax.legend(frameon=False, fontsize=8)
        else:
            for name, group_df in stage_df.groupby('Group_MIND'):
                ax.scatter(group_df['Burden_Score'], np.arange(len(group_df)), s=26, alpha=0.75, label=name, color=palette.get(name))
            ax.set_ylabel('Index')
            ax.legend(frameon=False, fontsize=8)
        ax.set_title('Burden vs Residual')
        ax.set_xlabel('Burden Score')

        ax = axes[0, 1]
        sns_df = stage_df[['Group_MIND', 'Burden_Score']].copy()
        try:
            import seaborn as sns
            sns.boxplot(
                data=sns_df,
                x='Group_MIND',
                y='Burden_Score',
                hue='Group_MIND',
                palette=palette,
                ax=ax,
                showfliers=False,
                dodge=False,
                legend=False,
            )
            sns.stripplot(data=sns_df, x='Group_MIND', y='Burden_Score', color='black', jitter=True, size=3, alpha=0.6, ax=ax)
        except Exception:
            for name, group_df in stage_df.groupby('Group_MIND'):
                ax.boxplot(group_df['Burden_Score'], positions=[0 if name == 'prodromal_SAA+' else 1], widths=0.5)
        ax.set_title('Stage Expression')
        ax.set_xlabel('Group')
        ax.set_ylabel('Burden Score')

        ax = axes[0, 2]
        if not residual_df.empty and 'Risk_Phenotype' in residual_df.columns:
            counts = residual_df['Risk_Phenotype'].value_counts().reindex([
                'High_Burden__Low_Resilience',
                'High_Burden__High_Resilience',
                'Low_Burden__Low_Resilience',
                'Low_Burden__High_Resilience',
            ]).fillna(0)
            ax.bar(counts.index, counts.values, color=GROUP_COLORS[1])
            ax.set_xticklabels(counts.index, rotation=45, ha='right')
            ax.set_title('High-risk Phenotypes')
            ax.set_ylabel('Count')
        else:
            ax.axis('off')
    else:
        for ax in axes[0, :]:
            ax.axis('off')

    if not lme_df.empty:
        for idx, scale in enumerate(TARGET_SCALES):
            ax = axes[1, idx]
            sub = lme_df[lme_df['Scale'] == scale].copy()
            if sub.empty:
                ax.axis('off')
                continue
            scale_col = alias_scale_column(sub, scale)
            for name, group_df in sub.groupby('Group_MIND'):
                ax.scatter(group_df['Burden_Score'], group_df[scale_col], s=20, alpha=0.5, label=name)
            ax.set_title(f'Longitudinal | {scale}')
            ax.set_xlabel('Burden Score')
            ax.set_ylabel(scale)
            if idx == 0:
                ax.legend(frameon=False, fontsize=8)
    else:
        axes[1, 0].axis('off')
        axes[1, 1].axis('off')

    if ahba_path and os.path.exists(ahba_path):
        try:
            ahba_img = plt.imread(ahba_path)
            ax = axes[1, 2]
            ax.imshow(ahba_img)
            ax.set_title('Allen / AHBA Overlay')
            ax.axis('off')
        except Exception:
            axes[1, 2].axis('off')
    else:
        axes[1, 2].axis('off')

    for ax in axes.flat:
        ax.set_facecolor('white')
        ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)

    fig.savefig(preview_path, dpi=300, bbox_inches='tight')
    return fig


def _save_group_plot(df, out_dir, scale_col):
    """
    保存 burden-resilience 双面板散点图。

    左图：临床量表评分 vs Burden Score（按组着色）
    右图：Residual（Resilience）vs Burden Score（按组着色）

    参数：
        df: 含 Burden_Score, Residual, Group_MIND 的 DataFrame
        out_dir: 输出目录
        scale_col: 临床量表列名

    返回：图片路径
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)

    for group_name, group_df in df.groupby('Group_MIND'):
        axes[0].scatter(group_df['Burden_Score'], group_df[scale_col], s=38, alpha=0.85, label=group_name)
    axes[0].set_xlabel('Burden Score')
    axes[0].set_ylabel(scale_col)
    axes[0].set_title(f'{scale_col} vs Burden Score')
    axes[0].legend(frameon=False)

    for group_name, group_df in df.groupby('Group_MIND'):
        axes[1].scatter(group_df['Burden_Score'], group_df['Residual'], s=38, alpha=0.85, label=group_name)
    axes[1].axhline(0, color='black', linewidth=1, alpha=0.7)
    axes[1].set_xlabel('Burden Score')
    axes[1].set_ylabel('Residual')
    axes[1].set_title(f'{scale_col} Residual (Resilience)')
    axes[1].legend(frameon=False)

    fig.suptitle(f'Plan 1 Burden-Resilience | {scale_col}')
    fig_path = os.path.join(out_dir, f'Plan1_Burden_Resilience_{scale_col}.png')
    fig.savefig(fig_path, dpi=300, bbox_inches='tight')
    if PREVIEW_PLOTS:
        plt.show(block=True)
    plt.close(fig)
    return fig_path


def _parse_ahba_donors(raw_value):
    """
    解析 AHBA 捐赠者配置（环境变量 STEP4_AHBA_DONORS）。

    'all' → 使用所有可用捐赠者；逗号分隔 ID → 使用指定捐赠者列表。

    参数：raw_value: 环境变量原始值

    返回：'all' 或捐赠者 ID 列表
    """
    text = str(raw_value).strip()
    if not text or text.lower() == 'all':
        return 'all'
    parts = [x.strip() for x in text.split(',') if x.strip()]
    return parts if parts else 'all'


def _ensure_allen_dirs():
    """确保 Allen 数据目录结构存在（atlas, expression, derived, cache）。"""
    ensure_dir(ALLEN_ROOT_DIR)
    ensure_dir(ALLEN_ATLAS_DIR)
    ensure_dir(ALLEN_EXPRESSION_DIR)
    ensure_dir(ALLEN_DERIVED_DIR)
    ensure_dir(os.path.join(ALLEN_ROOT_DIR, 'cache'))


def _load_local_expression_scores(local_file, atlas_info):
    """
    加载本地表达矩阵备用文件（当 AHBA 在线抓取失败时的降级方案）。

    支持两种格式：
    - 含 'Regional_Score' 列的 CSV → 直接使用
    - 多列数值 CSV → 取数值列均值作为区域分数

    参数：
        local_file: 本地 CSV 文件路径
        atlas_info: atlas 标签文件路径（用于长度对齐）

    返回：pd.Series（区域分数），失败返回 None
    """
    path = str(local_file).strip()
    if not path or not os.path.exists(path):
        return None

    df = pd.read_csv(path)
    if df.empty:
        return None

    if 'Regional_Score' in df.columns:
        score = pd.to_numeric(df['Regional_Score'], errors='coerce')
    else:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not numeric_cols:
            coerced = df.apply(pd.to_numeric, errors='coerce')
            numeric_cols = [c for c in coerced.columns if coerced[c].notna().any()]
            df = coerced
        if not numeric_cols:
            return None
        score = df[numeric_cols].mean(axis=1)

    score = pd.Series(score).reset_index(drop=True)
    atlas_labels = pd.read_csv(atlas_info).sort_values('id').reset_index(drop=True)
    if len(score) < len(atlas_labels):
        score = score.reindex(range(len(atlas_labels))).fillna(score.mean())
    return score


def _save_ahba_overlay(out_dir, regional_score, atlas_img, atlas_info, title_suffix):
    """
    保存 AHBA/PLS 区域分数的脑表面渲染图。

    优先使用 surface-based 渲染（fsaverage + nilearn plot_surf_stat_map），
    展示 L/R 半球的 lateral 和 medial 四个视角。
    若 surface 渲染失败，降级为 volumetric 渲染（plot_stat_map）。

    色图：CMAP_DIVERGING（RdBu_r），负值=红色（高异常），正值=蓝色（低异常）。
    使用 P5/P95 percentile 裁剪色图范围，避免离群值拉宽色图。

    参数：
        out_dir: 输出目录
        regional_score: 区域分数数组（如 PLS1_Score 或 Abnormality_Score）
        atlas_img: atlas NIfTI 图像路径
        atlas_info: atlas 标签 CSV 路径
        title_suffix: 图标题后缀

    返回：图片路径，失败返回 None
    """
    try:
        from nilearn import datasets, plotting
        surf_atlas = abagen.datasets.fetch_desikan_killiany(surface=True)
        left_gii, right_gii = surf_atlas['image']
        atlas_labels_surf = pd.read_csv(surf_atlas['info'])
        
        left_data = nib.load(left_gii).darrays[0].data
        right_data = nib.load(right_gii).darrays[0].data
        left_stat = np.zeros_like(left_data, dtype=float)
        right_stat = np.zeros_like(right_data, dtype=float)

        score_values = pd.Series(regional_score).reset_index(drop=True)
        if len(score_values) < len(atlas_labels_surf):
            score_values = score_values.reindex(range(len(atlas_labels_surf))).fillna(score_values.mean())

        for idx, row in atlas_labels_surf.iterrows():
            if row['hemisphere'] == 'L' and row['structure'] == 'cortex':
                left_stat[left_data == row['id']] = float(score_values.iloc[idx])
            elif row['hemisphere'] == 'R' and row['structure'] == 'cortex':
                right_stat[right_data == row['id']] = float(score_values.iloc[idx])

        # percentile 裁剪色图范围，避免离群值拉宽色图导致大部分区域颜色压缩
        # PLS1 score 有少数极端正值离群值（>94），会把色图拉宽使大部分区域变蓝
        # 使用 P5/P95 裁剪后，57 个负值区域（红）和 26 个正值区域（蓝）分布均衡
        finite_vals = score_values.dropna()
        finite_vals = finite_vals[np.isfinite(finite_vals)]
        if len(finite_vals) > 10:
            vmin = float(np.percentile(finite_vals, 5))
            vmax = float(np.percentile(finite_vals, 95))
            # 确保色图对称（发散型色图需要 vmin = -vmax）
            abs_max = max(abs(vmin), abs(vmax))
            vmin, vmax = -abs_max, abs_max
        else:
            vmin, vmax = None, None

        fsaverage = datasets.fetch_surf_fsaverage()
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), subplot_kw={'projection': '3d'})
        # symmetric_cbar=False 必须显式设置，否则 nilearn 会覆盖 vmin/vmax
        plot_args = dict(colorbar=True, cmap=CMAP_DIVERGING, threshold=None,
                         vmin=vmin, vmax=vmax, symmetric_cbar=False)
        plotting.plot_surf_stat_map(
            fsaverage.infl_left, left_stat, hemi='left', view='lateral',
            bg_map=fsaverage.sulc_left, axes=axes[0, 0], **plot_args)
        plotting.plot_surf_stat_map(
            fsaverage.infl_left, left_stat, hemi='left', view='medial',
            bg_map=fsaverage.sulc_left, axes=axes[1, 0], **plot_args)
        plotting.plot_surf_stat_map(
            fsaverage.infl_right, right_stat, hemi='right', view='lateral',
            bg_map=fsaverage.sulc_right, axes=axes[0, 1], **plot_args)
        plotting.plot_surf_stat_map(
            fsaverage.infl_right, right_stat, hemi='right', view='medial',
            bg_map=fsaverage.sulc_right, axes=axes[1, 1], **plot_args)
        for ax, label in zip(axes[:, 0], ['L lateral', 'L medial']):
            ax.set_title(label, fontsize=10)
        for ax, label in zip(axes[:, 1], ['R lateral', 'R medial']):
            ax.set_title(label, fontsize=10)
        fig.suptitle(f'Allen/AHBA mechanism surface | {title_suffix}', fontsize=12)
        fig_path = os.path.join(out_dir, 'AHBA_Mechanism_Overlay.png')
        fig.savefig(fig_path, dpi=300, bbox_inches='tight')
        plt.close('all')
        return fig_path
    except Exception as e:
        print(f"Warning: Failed to save surface map, using volumetric fallback: {e}")
        from nilearn import datasets, plotting
        atlas_labels = pd.read_csv(atlas_info).sort_values('id').reset_index(drop=True)
        atlas_img_obj = nib.load(atlas_img)
        atlas_data = atlas_img_obj.get_fdata().astype(int)
        overlay_data = np.zeros_like(atlas_data, dtype=float)

        score_values = pd.Series(regional_score).reset_index(drop=True)
        if len(score_values) < len(atlas_labels):
            score_values = score_values.reindex(range(len(atlas_labels))).fillna(score_values.mean())

        for idx, label_id in enumerate(atlas_labels['id'].tolist()):
            overlay_data[atlas_data == int(label_id)] = float(score_values.iloc[idx])

        score_img = nib.Nifti1Image(overlay_data, affine=atlas_img_obj.affine, header=atlas_img_obj.header)
        # percentile 裁剪色图范围（与 surface 渲染一致，P5/P95）
        finite_vals = score_values.dropna()
        finite_vals = finite_vals[np.isfinite(finite_vals)]
        if len(finite_vals) > 10:
            vmin = float(np.percentile(finite_vals, 5))
            vmax = float(np.percentile(finite_vals, 95))
            abs_max = max(abs(vmin), abs(vmax))
            vmin, vmax = -abs_max, abs_max
        else:
            vmin, vmax = None, None

        fig = plotting.plot_stat_map(
            score_img,
            title=f'Allen/AHBA overlay | {title_suffix}',
            display_mode='ortho',
            colorbar=True,
            cmap=CMAP_DIVERGING,
            cut_coords=None,
            vmin=vmin,
            vmax=vmax,
            symmetric_cbar=False,
        )
        fig_path = os.path.join(out_dir, 'AHBA_Mechanism_Overlay.png')
        fig.savefig(fig_path, dpi=300, bbox_inches='tight')
        plt.close('all')
        return fig_path


def _run_plan1_allen_overlay(base_out_dir, gene_group_name='brain'):
    """
    生成 Allen/AHBA 基因表达脑表面 overlay 图。

    流程：
    1. 获取指定基因组的 AHBA 表达数据（abagen）
    2. 对齐到 Desikan-Killiany atlas
    3. 计算区域级平均表达分数
    4. 渲染脑表面图（_save_ahba_overlay）
    5. 保存表达矩阵和汇总 CSV

    若 AHBA 在线抓取失败，降级使用本地表达矩阵文件。

    参数：
        base_out_dir: 输出根目录
        gene_group_name: 基因组名称（默认 'brain'，即脑特异性基因）

    返回：脑表面图路径，失败返回 None
    """
    _ensure_allen_dirs()
    ahba_dir = ensure_dir(os.path.join(base_out_dir, 'AHBA'))
    atlas = abagen.datasets.fetch_desikan_killiany(native=False, surface=False)
    donors = _parse_ahba_donors(PLAN1_ALLEN_DONORS_ENV)

    try:
        genes = abagen.datasets.fetch_gene_group(gene_group_name)
        gene_set = {g.upper() for g in genes}
        expr = abagen.get_expression_data(
            atlas['image'],
            atlas_info=atlas['info'],
            donors=donors,
            data_dir=PLAN1_AHBA_CACHE_DIR,
            return_counts=False,
            return_donors=False,
            verbose=0,
        )

        expr_df = expr.copy() if isinstance(expr, pd.DataFrame) else pd.DataFrame(expr)
        # 修正转置逻辑：abagen 通常返回 (regions, genes)
        # 通过检查哪一维与 atlas 脑区数匹配来判断
        atlas_info_path = atlas['info']
        n_atlas_regions = len(pd.read_csv(atlas_info_path))
        if expr_df.shape[0] == n_atlas_regions:
            pass  # 已是 (regions, genes)
        elif expr_df.shape[1] == n_atlas_regions:
            expr_df = expr_df.T
        elif expr_df.shape[0] < expr_df.shape[1]:
            expr_df = expr_df.T

        selected = [col for col in expr_df.columns if str(col).upper() in gene_set]
        if not selected:
            selected = expr_df.columns.tolist()
        regional_score = expr_df[selected].mean(axis=1).fillna(expr_df.mean(axis=1))

        expr_df.to_csv(os.path.join(ahba_dir, 'AHBA_Brain_Expression.csv'), index=False, encoding='utf-8-sig')
        expr_df.to_csv(os.path.join(ALLEN_EXPRESSION_DIR, 'AHBA_Brain_Expression.csv'), index=False, encoding='utf-8-sig')

        summary_df = pd.DataFrame({
            'Gene_Group': [gene_group_name],
            'Gene_Count': [len(genes)],
            'Donors_Used': [','.join(donors) if isinstance(donors, list) else str(donors)],
            'Regional_Mean': [float(regional_score.mean())],
        })
        summary_df.to_csv(os.path.join(ahba_dir, 'AHBA_Brain_Summary.csv'), index=False, encoding='utf-8-sig')
        summary_df.to_csv(os.path.join(ALLEN_EXPRESSION_DIR, 'AHBA_Brain_Summary.csv'), index=False, encoding='utf-8-sig')

        fig1 = _save_ahba_overlay(ahba_dir, regional_score, atlas['image'], atlas['info'], f'{gene_group_name} gene group')
        _save_ahba_overlay(ALLEN_DERIVED_DIR, regional_score, atlas['image'], atlas['info'], f'{gene_group_name} gene group')
        return fig1
    except Exception as exc:
        local_scores = _load_local_expression_scores(PLAN1_AHBA_LOCAL_EXPRESSION, atlas['info'])
        if local_scores is not None:
            fig1 = _save_ahba_overlay(
                ahba_dir,
                local_scores,
                atlas['image'],
                atlas['info'],
                f'{gene_group_name} local expression fallback',
            )
            _save_ahba_overlay(
                ALLEN_DERIVED_DIR,
                local_scores,
                atlas['image'],
                atlas['info'],
                f'{gene_group_name} local expression fallback',
            )
            with open(os.path.join(ahba_dir, 'AHBA_Local_Fallback_Notes.txt'), 'w', encoding='utf-8') as f:
                f.write(f'Local expression fallback used: {PLAN1_AHBA_LOCAL_EXPRESSION}\n')
            return fig1

        with open(os.path.join(ahba_dir, 'AHBA_Fallback_Notes.txt'), 'w', encoding='utf-8') as f:
            f.write('AHBA overlay could not be generated for Plan1.\n')
            f.write(f'Error: {exc}\n')
        return None


def run_plan1_burden_resilience():
    """
    Plan 1 主入口函数：执行完整的 Aim 3 burden-resilience 分析流程。

    执行顺序：
    1. 加载数据，获取 SAA+ 人群基线表
    2. 构建 MIND burden score（含 bootstrap CI）
    3. 对 UPDRS3 和 MoCA 分别拟合 resilience 模型（含 Spearman 检验）
    4. 生成四象限散点图
    5. PD/SAA- 探索性分析
    6. 阶段表达分析（logistic 回归 + forest plot）
    7. 构建高风险表型
    8. 纵向验证（MixedLM Time×Burden + Time×Resilience）
    9. AHBA/PLS 机制注释（Figures A-E + Supplementary 1-5）
    10. 保存所有结果和汇总
    """
    print('\n' + '=' * 60)
    print('Step 4 Plan 1: SAA+ burden-resilience')
    print('=' * 60)

    df_raw = load_raw_dataframe(DATA_FILE)
    df = get_saa_positive_table(df_raw)
    if df.empty:
        print('No SAA+ subjects available for Plan 1.')
        return

    ensure_dir(BASE_OUTPUT_DIR)
    df, burden_method, explained, burden_cols, burden_evidence = _build_burden_score(df_raw, df)

    # Bootstrap CI for burden score
    boot_mean_lo, boot_mean_hi, boot_sd_lo, boot_sd_hi = _bootstrap_burden_ci(df_raw, df)

    if not burden_evidence.empty:
        burden_evidence.to_csv(
            os.path.join(BASE_OUTPUT_DIR, 'Plan1_Burden_Previous_Result_Evidence.csv'),
            index=False,
            encoding='utf-8-sig',
        )

    summary_rows = []
    coef_rows = []
    model_rows = []
    fit_data_map = {}

    for scale in TARGET_SCALES:
        scale_col = alias_scale_column(df, scale)
        scale_df = df.copy()
        scale_df[scale_col] = pd.to_numeric(scale_df[scale_col], errors='coerce')
        scale_df = scale_df.dropna(subset=['Burden_Score', scale_col]).copy()
        scale_df = scale_df[scale_df['Group_MIND'].isin(['prodromal_SAA+', 'PD_SAA+'])].copy()

        fit = _fit_resilience_model(scale_df, scale_col, scale)
        if fit is None:
            print(f'  [{scale}] skipped: too few complete SAA+ subjects.')
            continue

        out_dir = ensure_dir(os.path.join(BASE_OUTPUT_DIR, scale))
        fit_data = fit['data'].copy()
        fit_data_map[scale] = fit_data
        plot_path = _save_group_plot(fit_data, out_dir, scale_col)

        summary_rows.append({
            'Outcome': scale,
            'Scale_Column': scale_col,
            'N': fit['n'],
            'Burden_Method': burden_method,
            'Burden_Explained_Variance': explained,
            'Burden_Source': df['Burden_Source'].iloc[0] if 'Burden_Source' in df.columns and len(df) else 'unknown',
            'Burden_Weight_Mode': df['Burden_Weight_Mode'].iloc[0] if 'Burden_Weight_Mode' in df.columns and len(df) else 'unknown',
            'Burden_Feature_Count': len(burden_cols),
            'Model_R2': fit['r2'],
            'Spearman_r': fit['spearman_r'],
            'Spearman_p': fit['spearman_p'],
            'Plot_Path': plot_path,
        })

        for feature, coef in fit['coefficients'].items():
            coef_rows.append({
                'Outcome': scale,
                'Feature': feature,
                'Coefficient': float(coef),
            })

        group_summary = _group_summary(fit_data, scale_col)
        group_summary.to_csv(os.path.join(out_dir, 'Group_Summary.csv'), index=False, encoding='utf-8-sig')
        out_cols = ['Original_SUB_ID', 'Group_MIND', 'Burden_Score', scale_col, 'Predicted', 'Residual']
        if 'Studentized_Residual' in fit_data.columns:
            out_cols.append('Studentized_Residual')
        fit_data[out_cols].to_csv(
            os.path.join(out_dir, 'Burden_Resilience_Data.csv'), index=False, encoding='utf-8-sig'
        )

        model_rows.append({
            'Outcome': scale,
            'Intercept': fit['intercept'],
            'Residual_Mean': fit['residual_mean'],
            'Residual_SD': fit['residual_sd'],
        })

    # Four-quadrant scatter plot
    four_quad_paths = _save_four_quadrant_scatter(fit_data_map, BASE_OUTPUT_DIR)

    # PD/SAA- exploratory analysis (section 4.5)
    pd_saa_exploratory = _run_pd_saa_exploratory(df_raw, df)
    if not pd_saa_exploratory.empty:
        pd_saa_exploratory.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_PDSAAMinus_Exploratory.csv'), index=False, encoding='utf-8-sig')

    stage_df, stage_model, stage_summary_df, stage_path = _fit_stage_expression(df)
    if stage_summary_df is not None and not stage_summary_df.empty:
        stage_summary_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Stage_Expression_Summary.csv'), index=False, encoding='utf-8-sig')
        forest_path = _save_forest_plot_stage_expression(stage_summary_df, BASE_OUTPUT_DIR)
    else:
        forest_path = None

    burden_stage_df = pd.DataFrame()
    if not fit_data_map:
        fit_data_map = {}
    if 'UPDRS3' in fit_data_map and 'MoCA' in fit_data_map:
        burden_stage_df = pd.concat([
            fit_data_map['UPDRS3'].assign(Scale='UPDRS3'),
            fit_data_map['MoCA'].assign(Scale='MoCA'),
        ], ignore_index=True)

    resilience_lookup = {
        scale: fit_data[['Original_SUB_ID', 'Residual']].copy()
        for scale, fit_data in fit_data_map.items()
    }

    high_risk_df = _build_high_risk_phenotypes(pd.concat(list(fit_data_map.values()), ignore_index=True) if fit_data_map else pd.DataFrame())
    if not high_risk_df.empty:
        high_risk_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_High_Risk_Phenotypes.csv'), index=False, encoding='utf-8-sig')

    lme_summary_df, lme_df = _fit_longitudinal_validation(df_raw, df, resilience_lookup=resilience_lookup)
    if not lme_summary_df.empty:
        lme_summary_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Longitudinal_Validation.csv'), index=False, encoding='utf-8-sig')
    if not lme_df.empty:
        lme_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Longitudinal_Fitted_Data.csv'), index=False, encoding='utf-8-sig')

    mechanism_result = None
    mechanism_preview_path = None
    mechanism_overlay_path = None
    gobp_path = None
    if PLAN1_ALLEN_ENABLE:
        print(f'[Plan1] Mechanism annotation stage started (gene group: {PLAN1_ALLEN_GENE_GROUP})', flush=True)
        try:
            mechanism_result = _fit_plan1_pls_mechanism()
            mechanism_preview_path = mechanism_result['mechanism_preview_path']
            mechanism_overlay_path = mechanism_result['mechanism_overlay_path']
            gobp_path = mechanism_result.get('gobp_path')
            print(f'[Plan1] Mechanism annotation complete: {mechanism_preview_path}', flush=True)
        except Exception as exc:
            print(f'[Plan1] Mechanism annotation failed: {exc}', flush=True)
    else:
        print('[Plan1] Mechanism annotation stage skipped (STEP4_PLAN1_ALLEN_ENABLE=0)', flush=True)

    summary_df = pd.DataFrame(summary_rows)
    coef_df = pd.DataFrame(coef_rows)
    model_df = pd.DataFrame(model_rows)

    summary_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Burden_Resilience_Summary.csv'), index=False, encoding='utf-8-sig')
    if not coef_df.empty:
        coef_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Burden_Resilience_Coefficients.csv'), index=False, encoding='utf-8-sig')
    if not model_df.empty:
        model_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Burden_Resilience_Residuals.csv'), index=False, encoding='utf-8-sig')

    preview_rows = []
    if not summary_df.empty:
        preview_rows.extend(summary_df.to_dict('records'))
    if stage_summary_df is not None and not stage_summary_df.empty:
        preview_rows.append({
            'Outcome': 'Stage_Expression',
            'Scale_Column': 'Stage_PD',
            'N': int(len(stage_df)) if stage_df is not None else 0,
            'Burden_Method': 'Stage expression model',
            'Burden_Explained_Variance': np.nan,
            'Burden_Source': df['Burden_Source'].iloc[0] if 'Burden_Source' in df.columns and len(df) else 'unknown',
            'Burden_Weight_Mode': df['Burden_Weight_Mode'].iloc[0] if 'Burden_Weight_Mode' in df.columns and len(df) else 'unknown',
            'Burden_Feature_Count': len(burden_cols),
            'Model_R2': np.nan,
            'Plot_Path': stage_path,
        })
    if not lme_summary_df.empty:
        for _, row in lme_summary_df.iterrows():
            preview_rows.append({
                'Outcome': f"Longitudinal_{row['Scale']}",
                'Scale_Column': 'Time × Burden',
                'N': int(row['N']),
                'Burden_Method': row['Model'],
                'Burden_Explained_Variance': np.nan,
                'Burden_Source': df['Burden_Source'].iloc[0] if 'Burden_Source' in df.columns and len(df) else 'unknown',
                'Burden_Weight_Mode': df['Burden_Weight_Mode'].iloc[0] if 'Burden_Weight_Mode' in df.columns and len(df) else 'unknown',
                'Burden_Feature_Count': len(burden_cols),
                'Model_R2': np.nan,
                'Plot_Path': os.path.join(BASE_OUTPUT_DIR, f"Plan1_Longitudinal_{row['Scale']}.csv"),
            })

    if preview_rows:
        pd.DataFrame(preview_rows).to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Overview.csv'), index=False, encoding='utf-8-sig')

    with open(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Burden_Resilience_Notes.txt'), 'w', encoding='utf-8') as f:
        f.write('PLAN 1: SAA+ BURDEN-RESILIENCE\n')
        f.write('Scope: prodromal_SAA+ vs PD_SAA+ only.\n')
        f.write(f'Burden score method: {burden_method}\n')
        f.write(f'Burden source: {df["Burden_Source"].iloc[0] if "Burden_Source" in df.columns and len(df) else "unknown"}\n')
        f.write(f'Burden feature count: {len(burden_cols)}\n')
        f.write(f'Burden score bootstrap 95% CI (mean): [{boot_mean_lo:.4f}, {boot_mean_hi:.4f}]\n')
        f.write(f'Burden score bootstrap 95% CI (SD): [{boot_sd_lo:.4f}, {boot_sd_hi:.4f}]\n')
        f.write('Residual resilience: studentized residuals from outcome ~ Burden_Score + Age/Sex/Education/LEDD/NHY.\n')
        f.write('Monotonicity check: Spearman correlation between burden and clinical score reported per scale.\n')
        if 'Burden_Source' in df.columns and len(df) and df['Burden_Source'].iloc[0] == 'previous_step2_results':
            f.write('Burden score is directly weighted by previous Step2 group-effect results and HC-referenced z-scores.\n')
        if stage_path:
            f.write(f'Stage expression summary: {stage_path}\n')
        if forest_path:
            f.write(f'Stage expression forest plot: {forest_path}\n')
        if not lme_summary_df.empty:
            f.write('Longitudinal validation: Plan1_Longitudinal_Validation.csv\n')
        if not high_risk_df.empty:
            f.write('High-risk phenotype table: Plan1_High_Risk_Phenotypes.csv\n')
        if four_quad_paths:
            f.write(f'Four-quadrant scatter plots: {", ".join(four_quad_paths)}\n')
        if not pd_saa_exploratory.empty:
            f.write(f'PD/SAA- exploratory analysis: Plan1_PDSAAMinus_Exploratory.csv\n')
        if mechanism_result is not None:
            f.write(f'Mechanism annotation summary: {os.path.join(BASE_OUTPUT_DIR, "Plan1_Mechanism_Summary.csv")}\n')
            f.write(f'Mechanism overlay: {mechanism_overlay_path or "not generated"}\n')
            f.write(f'Mechanism preview: {mechanism_preview_path or "not generated"}\n')

    if PLAN1_UNIFIED_PREVIEW:
        preview_path = os.path.join(BASE_OUTPUT_DIR, 'Plan1_Unified_Preview.png')
        preview_fig = _create_plan1_unified_preview(
            stage_df=stage_df,
            burden_stage_df=burden_stage_df,
            lme_df=lme_df,
            preview_path=preview_path,
            ahba_path=mechanism_overlay_path if mechanism_overlay_path and os.path.exists(mechanism_overlay_path) else None,
        )
        if PREVIEW_PLOTS:
            plt.show(block=True)
        plt.close(preview_fig)

    print(f'Plan 1 complete. Results saved to: {BASE_OUTPUT_DIR}')


if __name__ == '__main__':
    run_plan1_burden_resilience()

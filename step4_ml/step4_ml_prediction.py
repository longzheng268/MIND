import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.svm import SVR, SVC
from sklearn.linear_model import ElasticNet, LogisticRegression
from sklearn.model_selection import cross_val_score, RepeatedKFold, StratifiedKFold
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from config import *

apply_style()

# --- Step 4：机器学习预测模型 ---
# 回归：用基线 MIND 网络特征预测 2 年内临床量表变化量（Δ = V06 - BL）
# 分类：用基线 MIND 网络特征预测 SAA+ vs SAA-
# 输入特征：8 维 MIND 网络指标 + 3 维人口学变量 = 11 维
# 仅 SAA+ 和 SAA-（prodromal 亚组）

DATA_FILE       = './scale/MIND_baseline_with_followup_V04_V12.csv'
BASE_OUTPUT_DIR = './MIND_Research_Results/ML_Prediction/'

# 网络级别特征列
MIND_COLS = [
    'MIND_Sig_Index', 'MIND_Visual', 'MIND_Somatomotor',
    'MIND_Dorsal_Attention', 'MIND_Ventral_Attention',
    'MIND_Limbic', 'MIND_Frontoparietal', 'MIND_Default',
]
DEMO_COLS = ['Age_at_Visit', 'Sex', 'Education']
FEATURE_COLS = MIND_COLS + DEMO_COLS

# 特征英文名（图表用）
FEAT_SHORT = {
    'MIND_Sig_Index': 'Global MIND',
    'MIND_Visual': 'Visual',
    'MIND_Somatomotor': 'Somatomotor',
    'MIND_Dorsal_Attention': 'Dorsal Att',
    'MIND_Ventral_Attention': 'Ventral Att',
    'MIND_Limbic': 'Limbic',
    'MIND_Frontoparietal': 'Frontoparietal',
    'MIND_Default': 'Default',
    'Age_at_Visit': 'Age',
    'Sex': 'Sex',
    'Education': 'Education',
}

# 交叉验证参数
N_SPLITS = 5
N_REPEATS = 3
RANDOM_STATE = 42
SCALE_COLUMN_ALIASES = {
    'MoCA': ['MoCA'],
    'UPDRS3': ['UPDRS3', 'UPDRSIII', 'UPDRSIII.1'],
}


def _get_scale_col(df, scale):
    for col in SCALE_COLUMN_ALIASES.get(scale, [scale]):
        if col in df.columns:
            return col
    raise KeyError(f"未找到量表列: {scale}")


def _load_bl_features():
    """加载 BL 时间点的特征数据（仅 SAA+ 和 SAA-）。"""
    df = pd.read_csv(DATA_FILE)
    df_bl = df[df['EVENT_ID'] == BL_EVENT].copy()
    df_bl = df_bl[df_bl['SAA_Status'].isin(['Positive', 'Negative'])].copy()
    df_bl['SAA_Status'] = pd.Categorical(
        df_bl['SAA_Status'], categories=['Negative', 'Positive'], ordered=True
    )
    return df_bl


def _get_delta(df, scale, subjects):
    """计算受试者从 BL 到 V06 的评分变化量（Δ = V06 - BL）。"""
    scale_col = _get_scale_col(df, scale)
    df[scale_col] = pd.to_numeric(df[scale_col], errors='coerce')
    df_clean = df[df['Original_SUB_ID'].isin(subjects)].copy()

    bl = df_clean[df_clean['EVENT_ID'] == BL_EVENT][['Original_SUB_ID', scale_col]].copy()
    bl.columns = ['Original_SUB_ID', 'BL_score']
    bl = bl.drop_duplicates(subset='Original_SUB_ID', keep='first')

    v06 = df_clean[df_clean['EVENT_ID'] == FOLLOWUP_EVENT_2Y][['Original_SUB_ID', scale_col]].copy()
    v06.columns = ['Original_SUB_ID', 'V06_score']
    v06 = v06.drop_duplicates(subset='Original_SUB_ID', keep='first')

    delta = pd.merge(bl, v06, on='Original_SUB_ID', how='inner')
    delta['Delta'] = delta['V06_score'] - delta['BL_score']
    delta = delta.dropna(subset=['Delta']).drop_duplicates(subset='Original_SUB_ID', keep='first')
    return delta[['Original_SUB_ID', 'Delta']]


def run_regression():
    """回归任务：预测 Δ 临床量表（MoCA、UPDRS3）。"""
    print("\n" + "="*60)
    print("Step 4a：回归预测 Δ 临床量表（SAA 亚组）")
    print("="*60)

    if not os.path.exists(DATA_FILE):
        print(f"找不到文件: {DATA_FILE}")
        return

    df_raw = pd.read_csv(DATA_FILE)
    df_bl = _load_bl_features()

    for scale in ['MoCA', 'UPDRS3']:
        print(f"\n  >>> 正在处理量表: {scale} ...")

        # 获取 Δ
        delta = _get_delta(df_raw, scale, df_bl['Original_SUB_ID'].unique())
        if len(delta) < 30:
            print(f"    有 V06 数据的受试者不足({len(delta)})，跳过。")
            continue

        # 合并特征 + Δ
        df_merge = pd.merge(df_bl, delta, on='Original_SUB_ID', how='inner')
        X = df_merge[FEATURE_COLS].dropna()
        y = df_merge.loc[X.index, 'Delta']

        print(f"    有效样本: {len(X)} 人")

        out_dir = os.path.join(BASE_OUTPUT_DIR, f'Regression_{scale}')
        os.makedirs(out_dir, exist_ok=True)

        # 标准化 + 模型
        models = {
            'RandomForest': Pipeline([
                ('scaler', StandardScaler()),
                ('model', RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE))
            ]),
            'SVR': Pipeline([
                ('scaler', StandardScaler()),
                ('model', SVR(kernel='rbf', C=1.0))
            ]),
            'ElasticNet': Pipeline([
                ('scaler', StandardScaler()),
                ('model', ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=RANDOM_STATE, max_iter=5000))
            ]),
        }

        cv = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
        results = []

        for name, pipe in models.items():
            r2_scores = cross_val_score(pipe, X, y, cv=cv, scoring='r2')
            neg_mae = cross_val_score(pipe, X, y, cv=cv, scoring='neg_mean_absolute_error')
            neg_rmse = cross_val_score(pipe, X, y, cv=cv, scoring='neg_root_mean_squared_error')

            results.append({
                'Model': name,
                'R2_mean': r2_scores.mean(),
                'R2_std': r2_scores.std(),
                'MAE_mean': -neg_mae.mean(),
                'MAE_std': -neg_mae.std(),
                'RMSE_mean': -neg_rmse.mean(),
                'RMSE_std': -neg_rmse.std(),
            })
            print(f"    {name}: R²={r2_scores.mean():.3f}±{r2_scores.std():.3f}, "
                  f"MAE={-neg_mae.mean():.3f}")

        # 保存 CV 结果
        res_df = pd.DataFrame(results)
        res_df.to_csv(os.path.join(out_dir, 'CV_Results.csv'), index=False)

        # 特征重要性（用最佳模型）
        best_name = res_df.loc[res_df['R2_mean'].idxmax(), 'Model']
        print(f"    最佳模型: {best_name}")
        best_pipe = models[best_name]
        best_pipe.fit(X, y)

        # permutation importance
        perm_imp = permutation_importance(best_pipe, X, y, n_repeats=10, random_state=RANDOM_STATE)
        imp_df = pd.DataFrame({
            'Feature': [FEAT_SHORT.get(c, c) for c in FEATURE_COLS],
            'Importance_mean': perm_imp.importances_mean,
            'Importance_std': perm_imp.importances_std,
        }).sort_values('Importance_mean', ascending=True)

        # 特征重要性图
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(imp_df['Feature'], imp_df['Importance_mean'], xerr=imp_df['Importance_std'],
                color='#66c2a5', edgecolor='white', linewidth=0.5)
        ax.set_xlabel('Permutation Importance (R² decrease)', fontsize=FONT_AXIS)
        ax.set_title(f'Regression: {scale} Δ Prediction\nFeature Importance ({best_name}, 5-fold CV)',
                     fontsize=FONT_TITLE)
        ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, 'Feature_Importance.png'), dpi=DPI)
        plt.close()

        # 保存摘要
        with open(os.path.join(out_dir, 'Prediction_Summary.txt'), 'w') as f:
            f.write(f"REGRESSION: Predicting Δ {scale} (V06 - BL)\n")
            f.write(f"Sample size: {len(X)}\n")
            f.write(f"CV: {N_SPLITS}-fold, {N_REPEATS} repeats\n\n")
            for _, row in res_df.iterrows():
                f.write(f"{row['Model']}: R²={row['R2_mean']:.3f}±{row['R2_std']:.3f}, "
                        f"MAE={row['MAE_mean']:.3f}, RMSE={row['RMSE_mean']:.3f}\n")
            f.write(f"\nBest model: {best_name}\n")
            f.write(f"\nPermutation Importance:\n")
            for _, row in imp_df.iterrows():
                f.write(f"  {row['Feature']}: {row['Importance_mean']:.4f}±{row['Importance_std']:.4f}\n")

    print(f"\n>>> 回归预测完成！结果存放至: {BASE_OUTPUT_DIR}")


def run_classification():
    """分类任务：预测 SAA+ vs SAA-。"""
    print("\n" + "="*60)
    print("Step 4b：分类预测 SAA+ vs SAA-")
    print("="*60)

    if not os.path.exists(DATA_FILE):
        print(f"找不到文件: {DATA_FILE}")
        return

    df_bl = _load_bl_features()
    X = df_bl[FEATURE_COLS].dropna()
    y = df_bl.loc[X.index, 'SAA_Status'].map({'Negative': 0, 'Positive': 1})

    print(f"  有效样本: {len(X)} 人 (SAA-: {(y==0).sum()}, SAA+: {(y==1).sum()})")

    out_dir = os.path.join(BASE_OUTPUT_DIR, 'Classification_SAA')
    os.makedirs(out_dir, exist_ok=True)

    models = {
        'RandomForest': Pipeline([
            ('scaler', StandardScaler()),
            ('model', RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE))
        ]),
        'SVC': Pipeline([
            ('scaler', StandardScaler()),
            ('model', SVC(kernel='rbf', C=1.0, probability=True))
        ]),
        'LogisticRegression': Pipeline([
            ('scaler', StandardScaler()),
            ('model', LogisticRegression(C=1.0, random_state=RANDOM_STATE, max_iter=2000))
        ]),
    }

    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    results = []

    for name, pipe in models.items():
        acc = cross_val_score(pipe, X, y, cv=cv, scoring='accuracy')
        f1 = cross_val_score(pipe, X, y, cv=cv, scoring='f1')
        auc = cross_val_score(pipe, X, y, cv=cv, scoring='roc_auc')

        results.append({
            'Model': name,
            'Accuracy_mean': acc.mean(),
            'Accuracy_std': acc.std(),
            'F1_mean': f1.mean(),
            'F1_std': f1.std(),
            'AUC_mean': auc.mean(),
            'AUC_std': auc.std(),
        })
        print(f"    {name}: Acc={acc.mean():.3f}±{acc.std():.3f}, "
              f"F1={f1.mean():.3f}, AUC={auc.mean():.3f}")

    res_df = pd.DataFrame(results)
    res_df.to_csv(os.path.join(out_dir, 'CV_Results.csv'), index=False)

    # 特征重要性（用最佳模型）
    best_name = res_df.loc[res_df['AUC_mean'].idxmax(), 'Model']
    print(f"    最佳模型: {best_name}")
    best_pipe = models[best_name]
    best_pipe.fit(X, y)

    perm_imp = permutation_importance(best_pipe, X, y, n_repeats=10, random_state=RANDOM_STATE)
    imp_df = pd.DataFrame({
        'Feature': [FEAT_SHORT.get(c, c) for c in FEATURE_COLS],
        'Importance_mean': perm_imp.importances_mean,
        'Importance_std': perm_imp.importances_std,
    }).sort_values('Importance_mean', ascending=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(imp_df['Feature'], imp_df['Importance_mean'], xerr=imp_df['Importance_std'],
            color='#fc8d62', edgecolor='white', linewidth=0.5)
    ax.set_xlabel('Permutation Importance (AUC decrease)', fontsize=FONT_AXIS)
    ax.set_title(f'Classification: SAA+ vs SAA-\nFeature Importance ({best_name}, 5-fold CV)',
                 fontsize=FONT_TITLE)
    ax.grid(True, linestyle=GRID_LINESTYLE, alpha=ALPHA_GRID)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'Feature_Importance.png'), dpi=DPI)
    plt.close()

    with open(os.path.join(out_dir, 'Prediction_Summary.txt'), 'w') as f:
        f.write(f"CLASSIFICATION: Predicting SAA+ vs SAA-\n")
        f.write(f"Sample size: {len(X)} (SAA-: {(y==0).sum()}, SAA+: {(y==1).sum()})\n")
        f.write(f"CV: {N_SPLITS}-fold, stratified\n\n")
        for _, row in res_df.iterrows():
            f.write(f"{row['Model']}: Acc={row['Accuracy_mean']:.3f}±{row['Accuracy_std']:.3f}, "
                    f"F1={row['F1_mean']:.3f}, AUC={row['AUC_mean']:.3f}\n")
        f.write(f"\nBest model: {best_name}\n")
        f.write(f"\nPermutation Importance:\n")
        for _, row in imp_df.iterrows():
            f.write(f"  {row['Feature']}: {row['Importance_mean']:.4f}±{row['Importance_std']:.4f}\n")

    print(f"\n>>> 分类预测完成！结果存放至: {BASE_OUTPUT_DIR}")


if __name__ == "__main__":
    run_regression()
    run_classification()

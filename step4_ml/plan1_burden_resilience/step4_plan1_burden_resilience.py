import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from config import *
from step4_ml.step4_ml_shared import (
    DEMOGRAPHIC_COLS,
    SAA_BURDEN_COLS,
    alias_scale_column,
    coerce_numeric,
    ensure_dir,
    get_saa_positive_table,
    load_raw_dataframe,
    zscore_frame,
)


def _enforce_global_plot_style():
    apply_style()


_enforce_global_plot_style()

DATA_FILE = './scale/MIND_baseline_with_followup_V04_V12.csv'
BASE_OUTPUT_DIR = './MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/'
RANDOM_STATE = 42

TARGET_SCALES = ['UPDRS3', 'MoCA']


def _build_burden_score(df):
    burden_cols = [col for col in SAA_BURDEN_COLS if col in df.columns]
    if not burden_cols:
        raise ValueError('No burden columns are available for Plan 1.')

    work = coerce_numeric(df, burden_cols)
    zf = zscore_frame(work, burden_cols)
    zf = zf.fillna(0.0)

    if zf.shape[1] == 1:
        burden_score = zf.iloc[:, 0].copy()
        burden_method = 'single-feature z-score'
        explained = 1.0
    else:
        scaler = StandardScaler()
        scaled = scaler.fit_transform(zf.values)
        pca = PCA(n_components=1, random_state=RANDOM_STATE)
        burden_score = pca.fit_transform(scaled).ravel()
        burden_method = 'PCA-PC1 on burden features'
        explained = float(pca.explained_variance_ratio_[0])

    out = df.copy()
    out['Burden_Score'] = burden_score
    return out, burden_method, explained, burden_cols


def _fit_resilience_model(df, scale_col, label):
    covars = [col for col in DEMOGRAPHIC_COLS if col in df.columns]
    model_cols = ['Burden_Score'] + covars
    model_df = coerce_numeric(df, ['Burden_Score', scale_col] + [col for col in covars if col != 'Sex'])
    model_df = model_df.dropna(subset=['Burden_Score', scale_col]).copy()

    if len(model_df) < 8:
        return None

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

    return {
        'label': label,
        'n': int(len(model_df)),
        'r2': float(r2_score(y, y_pred)) if len(model_df) >= 2 else np.nan,
        'intercept': float(reg.intercept_),
        'coefficients': dict(zip(x_cols, reg.coef_)),
        'residual_mean': float(np.mean(residual)),
        'residual_sd': float(np.std(residual, ddof=0)),
        'data': model_df.assign(Residual=residual, Predicted=y_pred),
    }


def _group_summary(df, scale_col):
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


def _save_group_plot(df, out_dir, scale_col):
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
    plt.show(block=True)
    plt.close(fig)
    return fig_path


def run_plan1_burden_resilience():
    print('\n' + '=' * 60)
    print('Step 4 Plan 1: SAA+ burden-resilience')
    print('=' * 60)

    df_raw = load_raw_dataframe(DATA_FILE)
    df = get_saa_positive_table(df_raw)
    if df.empty:
        print('No SAA+ subjects available for Plan 1.')
        return

    df, burden_method, explained, burden_cols = _build_burden_score(df)
    ensure_dir(BASE_OUTPUT_DIR)

    summary_rows = []
    coef_rows = []
    model_rows = []

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
        plot_path = _save_group_plot(fit_data, out_dir, scale_col)

        summary_rows.append({
            'Outcome': scale,
            'Scale_Column': scale_col,
            'N': fit['n'],
            'Burden_Method': burden_method,
            'Burden_Explained_Variance': explained,
            'Model_R2': fit['r2'],
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
        fit_data[['Original_SUB_ID', 'Group_MIND', 'Burden_Score', scale_col, 'Predicted', 'Residual']].to_csv(
            os.path.join(out_dir, 'Burden_Resilience_Data.csv'), index=False, encoding='utf-8-sig'
        )

        model_rows.append({
            'Outcome': scale,
            'Intercept': fit['intercept'],
            'Residual_Mean': fit['residual_mean'],
            'Residual_SD': fit['residual_sd'],
        })

    summary_df = pd.DataFrame(summary_rows)
    coef_df = pd.DataFrame(coef_rows)
    model_df = pd.DataFrame(model_rows)

    summary_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Burden_Resilience_Summary.csv'), index=False, encoding='utf-8-sig')
    if not coef_df.empty:
        coef_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Burden_Resilience_Coefficients.csv'), index=False, encoding='utf-8-sig')
    if not model_df.empty:
        model_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Burden_Resilience_Residuals.csv'), index=False, encoding='utf-8-sig')

    with open(os.path.join(BASE_OUTPUT_DIR, 'Plan1_Burden_Resilience_Notes.txt'), 'w', encoding='utf-8') as f:
        f.write('PLAN 1: SAA+ BURDEN-RESILIENCE\n')
        f.write('Scope: prodromal_SAA+ vs PD_SAA+ only.\n')
        f.write(f'Burden score method: {burden_method}\n')
        f.write(f'Burden feature count: {len(burden_cols)}\n')
        f.write('Residual resilience is computed as outcome residual after Burden Score + Age/Sex/Education adjustment.\n')

    print(f'Plan 1 complete. Results saved to: {BASE_OUTPUT_DIR}')


if __name__ == '__main__':
    run_plan1_burden_resilience()

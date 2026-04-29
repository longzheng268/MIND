import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, roc_auc_score, roc_curve
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import *
from step4_ml.step4_ml_shared import (
    BL_EVENT,
    DEMOGRAPHIC_COLS,
    MIND_COLS,
    NON_HC_GROUPS,
    SAA_POSITIVE_GROUPS,
    alias_scale_column,
    available_cols,
    coerce_numeric,
    ensure_dir,
    get_baseline_table,
    get_saa_positive_table,
    load_raw_dataframe,
    make_balanced_subject_split,
    zscore_frame,
)


def _enforce_global_plot_style():
    # Step4 plotting style is globally governed by config.py only.
    apply_style()


_enforce_global_plot_style()

# Aim 3: incremental predictive value in the Parkinson spectrum only.
# The pipeline uses a fixed 70/30 subject split, trains models only on the
# training set, and reports final performance on the held-out test set.

DATA_FILE = './scale/MIND_baseline_with_followup_V04_V12.csv'
BASE_OUTPUT_DIR = './MIND_Research_Results/ML_Prediction/Aim3_Incremental/'
SPLIT_OUTPUT_DIR = './data/step4_ml/'
SPLIT_FILE = os.path.join(SPLIT_OUTPUT_DIR, 'aim3_train_test_split.csv')
SPLIT_META_FILE = os.path.join(SPLIT_OUTPUT_DIR, 'aim3_train_test_split_meta.json')

RANDOM_STATE = 42
TRAIN_RATIO = 0.7
TEST_RATIO = 0.3
TRAIN_CV_SPLITS = 5
MIN_MODEL_N = 30

OUTCOME_WINDOWS = [
    {'event': 'V06', 'label': 'Baseline to V06', 'suffix': 'V06'},
    {'event': 'V10', 'label': 'Baseline to V10', 'suffix': 'V10'},
    {'event': 'V12', 'label': 'Baseline to V12', 'suffix': 'V12'},
]

PLAN2_WINDOWS_ENV = os.getenv('STEP4_PLAN2_WINDOWS', '').strip()
PLAN2_PREVIEW_PLOTS = os.getenv('STEP4_PLAN2_PREVIEW', '1') == '1'
PLAN2_SAVE_ROC_PLOTS = os.getenv('STEP4_PLAN2_SAVE_ROC_PLOTS', '1') == '1'

TARGET_SCALES = ['UPDRS3', 'MoCA']

MIND_COLS = [
    'MIND_Sig_Index', 'MIND_Visual', 'MIND_Somatomotor',
    'MIND_Dorsal_Attention', 'MIND_Ventral_Attention',
    'MIND_Limbic', 'MIND_Frontoparietal', 'MIND_Default',
]
DEMO_COLS = ['Age_at_Visit', 'Sex', 'Education']
CLINICAL_CANDIDATES = [
    'UPDRS3', 'MoCA', 'GDS15_all', 'RBDSQ_all', 'NP1APAT', 'NP1FATG',
    'ESS_all', 'SCOPA_AUT_all', 'LEDD_Baseline',
]

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
    'LEDD_Baseline': 'LEDD',
    'GDS15_all': 'GDS-15',
    'RBDSQ_all': 'RBDSQ',
    'NP1APAT': 'Apathy',
    'NP1FATG': 'Fatigue',
    'ESS_all': 'ESS',
    'SCOPA_AUT_all': 'SCOPA-AUT',
    'SAA_Binary': 'SAA Status',
}

SUMMARY_NOTES = [
    'Model E (conventional MRI comparator) not run: no ready-to-use conventional MRI feature set is wired in the current repository.',
    'Model F (clinical + SAA + conventional MRI + MIND) not run: conventional MRI comparator variables are unavailable in the current dataset/pipeline.',
    'SAA kinetic parameter module not run: only binary SAA status is available in the current analysis table.',
    'Phenoconversion / Cox survival analysis not run: no event-time phenoconversion labels are wired into the present pipeline.',
]

MODEL_ORDER = [
    'Model_A_Clinical',
    'Model_B_Clinical_SAA',
    'Model_C_Clinical_MIND',
    'Model_D_Clinical_SAA_MIND',
]


def _get_scale_col(df, scale):
    return alias_scale_column(df, scale)


def _available_clinical_cols(df):
    available = []
    for col in CLINICAL_CANDIDATES:
        if col == 'UPDRS3':
            try:
                available.append(_get_scale_col(df, 'UPDRS3'))
            except KeyError:
                continue
        elif col in df.columns:
            available.append(col)
    return list(dict.fromkeys(available))


def _load_raw_dataframe():
    return load_raw_dataframe(DATA_FILE)


def _encode_binary_columns(df):
    out = df.copy()
    if 'Sex' in out.columns:
        sex_series = out['Sex']
        if pd.api.types.is_numeric_dtype(sex_series):
            out['Sex'] = sex_series
        else:
            out['Sex'] = sex_series.map({'M': 1, 'F': 0, 'Male': 1, 'Female': 0, '1': 1, '0': 0})
    if 'SAA_Status' in out.columns:
        out['SAA_Binary'] = out['SAA_Status'].map({'Negative': 0, 'Positive': 1})
    return out


def _prepare_baseline_table(df_raw):
    df_bl = get_baseline_table(df_raw, groups=NON_HC_GROUPS)
    df_bl = df_bl[df_bl['SAA_Status'].isin(['Negative', 'Positive'])].copy()
    df_bl = df_bl.drop_duplicates(subset='Original_SUB_ID', keep='first').reset_index(drop=True)
    df_bl['SAA_Status'] = pd.Categorical(df_bl['SAA_Status'], categories=['Negative', 'Positive'], ordered=True)
    return _encode_binary_columns(df_bl)


def _prepare_train_test_split(df_bl):
    split_df = make_balanced_subject_split(
        df_bl[['Original_SUB_ID', 'Group_MIND', 'SAA_Status']].drop_duplicates().copy(),
        random_state=RANDOM_STATE,
        train_ratio=TRAIN_RATIO,
        test_ratio=TEST_RATIO,
    )

    os.makedirs(SPLIT_OUTPUT_DIR, exist_ok=True)
    split_df.to_csv(SPLIT_FILE, index=False, encoding='utf-8-sig')
    with open(SPLIT_META_FILE, 'w', encoding='utf-8') as f:
        json.dump(
            {
                'data_file': DATA_FILE,
                'random_state': RANDOM_STATE,
                'train_ratio': TRAIN_RATIO,
                'test_ratio': TEST_RATIO,
                'n_subjects': int(len(split_df)),
                'n_train': int((split_df['Split'] == 'train').sum()),
                'n_test': int((split_df['Split'] == 'test').sum()),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    return split_df


def _get_delta(df, scale, subjects, endpoint):
    scale_col = _get_scale_col(df, scale)
    df_work = df.copy()
    df_work[scale_col] = pd.to_numeric(df_work[scale_col], errors='coerce')
    df_work = df_work[df_work['Original_SUB_ID'].isin(subjects)].copy()

    bl = df_work[df_work['EVENT_ID'] == BL_EVENT][['Original_SUB_ID', scale_col]].copy()
    bl.columns = ['Original_SUB_ID', 'BL_score']
    bl = bl.drop_duplicates(subset='Original_SUB_ID', keep='first')

    followup = df_work[df_work['EVENT_ID'] == endpoint][['Original_SUB_ID', scale_col]].copy()
    followup.columns = ['Original_SUB_ID', 'FU_score']
    followup = followup.drop_duplicates(subset='Original_SUB_ID', keep='first')

    delta = pd.merge(bl, followup, on='Original_SUB_ID', how='inner')
    delta['Delta'] = delta['FU_score'] - delta['BL_score']
    delta = delta.dropna(subset=['Delta']).drop_duplicates(subset='Original_SUB_ID', keep='first')
    return delta[['Original_SUB_ID', 'Delta']]


def _define_models(df_model):
    available_cols = set(df_model.columns)
    demo_cols = [col for col in DEMO_COLS if col in available_cols]
    clinical_cols = [col for col in _available_clinical_cols(df_model) if col in available_cols]
    mind_cols = [col for col in MIND_COLS if col in available_cols]
    saa_cols = ['SAA_Binary'] if 'SAA_Binary' in available_cols else []

    return {
        'Model_A_Clinical': demo_cols + clinical_cols,
        'Model_B_Clinical_SAA': demo_cols + clinical_cols + saa_cols,
        'Model_C_Clinical_MIND': demo_cols + clinical_cols + mind_cols,
        'Model_D_Clinical_SAA_MIND': demo_cols + clinical_cols + saa_cols + mind_cols,
    }


def _coerce_feature_columns(df, cols):
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors='coerce')
    return out


def _make_pipeline():
    return Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('model', ElasticNet(max_iter=20000, random_state=RANDOM_STATE)),
    ])


def _fit_and_score_model(train_df, test_df, cols):
    usable_cols = [col for col in cols if train_df[col].notna().any()]
    if not usable_cols:
        return None

    scoring = {
        'r2': 'r2',
        'mae': 'neg_mean_absolute_error',
        'rmse': 'neg_root_mean_squared_error',
    }
    cv_splits = min(TRAIN_CV_SPLITS, max(2, len(train_df)))
    cv = KFold(n_splits=cv_splits, shuffle=True, random_state=RANDOM_STATE)

    grid = GridSearchCV(
        estimator=_make_pipeline(),
        param_grid={
            'model__alpha': np.logspace(-3, 1, 7),
            'model__l1_ratio': [0.1, 0.3, 0.5, 0.7, 0.9],
        },
        scoring=scoring,
        refit='rmse',
        cv=cv,
        n_jobs=-1,
        return_train_score=False,
    )

    X_train = train_df[usable_cols]
    y_train = train_df['Delta']
    X_test = test_df[usable_cols]
    y_test = test_df['Delta']

    grid.fit(X_train, y_train)

    best_idx = grid.best_index_
    cv_results = grid.cv_results_
    best_params = grid.best_params_

    train_cv_r2 = float(cv_results['mean_test_r2'][best_idx])
    train_cv_mae = float(-cv_results['mean_test_mae'][best_idx])
    train_cv_rmse = float(-cv_results['mean_test_rmse'][best_idx])

    best_model = grid.best_estimator_
    y_pred = best_model.predict(X_test)

    test_r2 = float(r2_score(y_test, y_pred)) if len(test_df) >= 2 else np.nan
    test_mae = float(mean_absolute_error(y_test, y_pred))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    pred_df = pd.DataFrame({
        'Original_SUB_ID': test_df['Original_SUB_ID'].values,
        'Observed_Delta': y_test.values,
        'Predicted_Delta': y_pred,
    })

    return {
        'used_cols': usable_cols,
        'train_cv_r2': train_cv_r2,
        'train_cv_mae': train_cv_mae,
        'train_cv_rmse': train_cv_rmse,
        'test_r2': test_r2,
        'test_mae': test_mae,
        'test_rmse': test_rmse,
        'best_alpha': float(best_params['model__alpha']),
        'best_l1_ratio': float(best_params['model__l1_ratio']),
        'best_estimator': best_model,
        'predictions': pred_df,
    }


def _build_model_frame(df_bl, split_df, df_raw, scale, endpoint):
    delta = _get_delta(df_raw, scale, df_bl['Original_SUB_ID'].unique(), endpoint['event'])
    if delta.empty:
        return pd.DataFrame()

    df_model = pd.merge(df_bl, delta, on='Original_SUB_ID', how='inner')
    df_model = pd.merge(df_model, split_df[['Original_SUB_ID', 'Split']], on='Original_SUB_ID', how='inner')
    df_model = df_model[df_model['Split'].isin(['train', 'test'])].copy()

    feature_sets = _define_models(df_model)
    used_cols = sorted({col for cols in feature_sets.values() for col in cols})
    df_model = _coerce_feature_columns(df_model, used_cols + ['Delta'])
    df_model = df_model.dropna(subset=['Delta']).reset_index(drop=True)
    return df_model


def _write_summary(summary_path, scale, endpoint, df_model, feature_sets, perf_df, best_model_name):
    train_n = int((df_model['Split'] == 'train').sum())
    test_n = int((df_model['Split'] == 'test').sum())
    total_n = int(len(df_model))

    if total_n >= 150:
        reliability = 'high'
    elif total_n >= 80:
        reliability = 'moderate'
    else:
        reliability = 'low'

    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('AIM 3: INCREMENTAL PREDICTIVE VALUE ASSESSMENT\n')
        f.write('Parkinson-spectrum only; HC excluded.\n')
        f.write(f'Outcome: {scale} Delta ({endpoint["event"]} - BL)\n')
        f.write(f'Window: {endpoint["label"]}\n')
        f.write(f'Sample size: {total_n}\n')
        f.write(f'Train/Test split: {train_n}/{test_n}\n\n')
        f.write(f'Reliability label: {reliability}\n')
        if reliability == 'low':
            f.write('Caution: low sample size window; interpret incremental differences conservatively.\n')
        f.write('\n')

        f.write('MODEL DEFINITIONS\n')
        for model_name in MODEL_ORDER:
            cols = feature_sets.get(model_name, [])
            f.write(f'- {model_name}: {", ".join(cols)}\n')

        f.write('\nTRAIN-CV AND TEST RESULTS\n')
        for _, row in perf_df.iterrows():
            f.write(
                f"{row['Model']}: "
                f"TrainCV R2={row['TrainCV_R2']:.3f}, MAE={row['TrainCV_MAE']:.3f}, RMSE={row['TrainCV_RMSE']:.3f}; "
                f"Test R2={row['Test_R2']:.3f}, MAE={row['Test_MAE']:.3f}, RMSE={row['Test_RMSE']:.3f}; "
                f"Delta vs A: dR2={row['Delta_R2_vs_A']:.3f}, dMAE={row['Delta_MAE_vs_A']:.3f}, dRMSE={row['Delta_RMSE_vs_A']:.3f}\n"
            )

        if best_model_name:
            f.write(f'\nBest test-RMSE model: {best_model_name}\n')

        f.write('\nUNAVAILABLE AIM 3 MODULES\n')
        for line in SUMMARY_NOTES:
            f.write(f'- {line}\n')


def _save_feature_importance(best_model, cols, test_df, out_dir, title_suffix):
    coef = best_model.named_steps['model'].coef_
    imp_df = pd.DataFrame({
        'Feature': [FEAT_SHORT.get(col, col) for col in cols],
        'Coefficient': coef,
        'Abs_Coefficient': np.abs(coef),
    }).sort_values('Abs_Coefficient', ascending=False)
    imp_df.to_csv(os.path.join(out_dir, 'Feature_Coefficients.csv'), index=False)
    return imp_df


def _make_binary_label(train_delta, test_delta):
    threshold = float(train_delta.median())
    train_y = (train_delta >= threshold).astype(int)
    test_y = (test_delta >= threshold).astype(int)
    return train_y, test_y, threshold


def _save_roc_plot(roc_rows, out_dir, title):
    if not roc_rows:
        return None

    if not PLAN2_SAVE_ROC_PLOTS:
        return None

    fig, ax = plt.subplots(figsize=(7.5, 6), constrained_layout=True)
    for row in roc_rows:
        ax.plot(row['FPR'], row['TPR'], linewidth=2.5, label=f"{row['Model']} (AUC={row['AUC']:.3f})")
    ax.plot([0, 1], [0, 1], color='black', linestyle='--', linewidth=1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title(title)
    ax.legend(frameon=False, fontsize=9)
    fig_path = os.path.join(out_dir, 'ROC_Curve.png')
    fig.savefig(fig_path, dpi=300, bbox_inches='tight')
    if PLAN2_PREVIEW_PLOTS:
        plt.show(block=True)
    plt.close(fig)
    return fig_path


def _selected_outcome_windows():
    if not PLAN2_WINDOWS_ENV:
        return OUTCOME_WINDOWS

    selected = {x.strip().upper() for x in PLAN2_WINDOWS_ENV.split(',') if x.strip()}
    filtered = [w for w in OUTCOME_WINDOWS if w['suffix'].upper() in selected or w['event'].upper() in selected]
    return filtered if filtered else OUTCOME_WINDOWS


def run_incremental_prediction():
    print('\n' + '=' * 60)
    print('Step 4: Aim 3 incremental prediction value assessment')
    print('=' * 60)

    df_raw = _load_raw_dataframe()
    df_bl = _prepare_baseline_table(df_raw)

    if df_bl['Original_SUB_ID'].nunique() < MIN_MODEL_N:
        print(f'Not enough baseline subjects after HC exclusion: {df_bl["Original_SUB_ID"].nunique()}')
        return

    split_df = _prepare_train_test_split(df_bl)
    print(f'Split saved to: {SPLIT_FILE}')

    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    preview_rows = []

    selected_windows = _selected_outcome_windows()
    print('Step4 Plan2 windows:', ', '.join([w['suffix'] for w in selected_windows]))

    for scale in TARGET_SCALES:
        print(f'\n>>> Outcome: {scale}')
        for endpoint in selected_windows:
            df_model = _build_model_frame(df_bl, split_df, df_raw, scale, endpoint)
            if df_model.empty:
                print(f"  [{endpoint['suffix']}] no paired follow-up data, skipped.")
                continue

            if len(df_model) < MIN_MODEL_N:
                print(f"  [{endpoint['suffix']}] insufficient paired subjects ({len(df_model)}), skipped.")
                continue

            train_df = df_model[df_model['Split'] == 'train'].copy()
            test_df = df_model[df_model['Split'] == 'test'].copy()

            if len(train_df) < 10 or len(test_df) < 5:
                print(f"  [{endpoint['suffix']}] train/test split too small ({len(train_df)}/{len(test_df)}), skipped.")
                continue

            feature_sets = _define_models(df_model)
            used_cols = sorted({col for cols in feature_sets.values() for col in cols})
            df_model = _coerce_feature_columns(df_model, used_cols + ['Delta'])
            train_df = df_model[df_model['Split'] == 'train'].copy()
            test_df = df_model[df_model['Split'] == 'test'].copy()

            print(f"  [{endpoint['suffix']}] usable subjects: {len(df_model)} (train={len(train_df)}, test={len(test_df)})")

            out_dir = os.path.join(BASE_OUTPUT_DIR, scale, endpoint['suffix'])
            os.makedirs(out_dir, exist_ok=True)

            rows = []
            test_predictions = pd.DataFrame({
                'Original_SUB_ID': test_df['Original_SUB_ID'].values,
                'Split': test_df['Split'].values,
                'Group_MIND': test_df['Group_MIND'].values,
                'SAA_Status': test_df['SAA_Status'].astype(str).values,
                'Observed_Delta': test_df['Delta'].values,
            })

            train_binary, test_binary, roc_threshold = _make_binary_label(train_df['Delta'], test_df['Delta'])
            roc_rows = []

            model_artifacts = {}
            for model_name in MODEL_ORDER:
                cols = feature_sets.get(model_name, [])
                if not cols:
                    continue

                result = _fit_and_score_model(train_df, test_df, cols)
                if result is None:
                    continue
                rows.append({
                    'Model': model_name,
                    'Features': ', '.join(result['used_cols']),
                    'n_features': len(result['used_cols']),
                    'TrainCV_R2': result['train_cv_r2'],
                    'TrainCV_MAE': result['train_cv_mae'],
                    'TrainCV_RMSE': result['train_cv_rmse'],
                    'Test_R2': result['test_r2'],
                    'Test_MAE': result['test_mae'],
                    'Test_RMSE': result['test_rmse'],
                    'Best_Alpha': result['best_alpha'],
                    'Best_L1_Ratio': result['best_l1_ratio'],
                })
                test_predictions[model_name] = result['predictions']['Predicted_Delta'].values
                model_artifacts[model_name] = {
                    'estimator': result['best_estimator'],
                    'cols': result['used_cols'],
                }

                try:
                    auc_value = float(roc_auc_score(test_binary, result['predictions']['Predicted_Delta'].values))
                    fpr, tpr, _ = roc_curve(test_binary, result['predictions']['Predicted_Delta'].values)
                    roc_rows.append({
                        'Model': model_name,
                        'AUC': auc_value,
                        'FPR': fpr,
                        'TPR': tpr,
                    })
                except ValueError:
                    pass

            perf_df = pd.DataFrame(rows)
            if perf_df.empty:
                print(f"  [{endpoint['suffix']}] no valid models were fit.")
                continue

            baseline_row = perf_df.loc[perf_df['Model'] == 'Model_A_Clinical']
            if not baseline_row.empty:
                baseline_test_r2 = float(baseline_row.iloc[0]['Test_R2'])
                baseline_test_mae = float(baseline_row.iloc[0]['Test_MAE'])
                baseline_test_rmse = float(baseline_row.iloc[0]['Test_RMSE'])
                perf_df['Delta_R2_vs_A'] = perf_df['Test_R2'] - baseline_test_r2
                perf_df['Delta_MAE_vs_A'] = perf_df['Test_MAE'] - baseline_test_mae
                perf_df['Delta_RMSE_vs_A'] = perf_df['Test_RMSE'] - baseline_test_rmse
            else:
                perf_df['Delta_R2_vs_A'] = np.nan
                perf_df['Delta_MAE_vs_A'] = np.nan
                perf_df['Delta_RMSE_vs_A'] = np.nan

            perf_df = perf_df[ [
                'Model', 'Features', 'n_features',
                'TrainCV_R2', 'TrainCV_MAE', 'TrainCV_RMSE',
                'Test_R2', 'Test_MAE', 'Test_RMSE',
                'Delta_R2_vs_A', 'Delta_MAE_vs_A', 'Delta_RMSE_vs_A',
                'Best_Alpha', 'Best_L1_Ratio',
            ] ]
            perf_df.to_csv(os.path.join(out_dir, 'Model_Performance.csv'), index=False, encoding='utf-8-sig')
            test_predictions.to_csv(os.path.join(out_dir, 'Test_Predictions.csv'), index=False, encoding='utf-8-sig')

            roc_summary_rows = []
            for row in roc_rows:
                roc_summary_rows.append({'Model': row['Model'], 'AUC': row['AUC'], 'Fast_Progressor_Threshold': roc_threshold})
            if roc_summary_rows:
                pd.DataFrame(roc_summary_rows).to_csv(os.path.join(out_dir, 'ROC_Summary.csv'), index=False, encoding='utf-8-sig')
                best_roc_model = sorted(roc_rows, key=lambda x: x['AUC'], reverse=True)[0]
                _save_roc_plot(
                    roc_rows,
                    out_dir,
                    f'ROC Curve | {scale} | {endpoint["suffix"]} | threshold={roc_threshold:.3f}',
                )
                with open(os.path.join(out_dir, 'ROC_Notes.txt'), 'w', encoding='utf-8') as f:
                    f.write('ROC analysis uses a train-only median threshold on Delta to define fast-progressor labels.\n')
                    f.write(f'Threshold: {roc_threshold:.6f}\n')
                    f.write(f'Best AUC model: {best_roc_model["Model"]} ({best_roc_model["AUC"]:.3f})\n')

            best_model_name = perf_df.sort_values('Test_RMSE').iloc[0]['Model']
            best_artifact = model_artifacts[best_model_name]
            _save_feature_importance(
                best_artifact['estimator'],
                best_artifact['cols'],
                test_df,
                out_dir,
                f'{scale} | {endpoint["suffix"]} | {best_model_name}',
            )

            _write_summary(
                os.path.join(out_dir, 'Prediction_Summary.txt'),
                scale,
                endpoint,
                df_model,
                feature_sets,
                perf_df,
                best_model_name,
            )

            print(f"  [{endpoint['suffix']}] best test-RMSE model: {best_model_name}")

            preview_rows.append({
                'Scale': scale,
                'Endpoint': endpoint['suffix'],
                'N': int(len(df_model)),
                'Train_N': int(len(train_df)),
                'Test_N': int(len(test_df)),
                'Reliability': 'high' if len(df_model) >= 150 else ('moderate' if len(df_model) >= 80 else 'low'),
                'Best_Model': best_model_name,
                'Best_Test_RMSE': float(perf_df.loc[perf_df['Model'] == best_model_name, 'Test_RMSE'].iloc[0]),
            })

    if preview_rows:
        pd.DataFrame(preview_rows).to_csv(os.path.join(BASE_OUTPUT_DIR, 'Aim3_Incremental_Overview.csv'), index=False, encoding='utf-8-sig')

    print(f'\n>>> Aim 3 incremental prediction complete. Results saved to: {BASE_OUTPUT_DIR}')


if __name__ == '__main__':
    run_incremental_prediction()
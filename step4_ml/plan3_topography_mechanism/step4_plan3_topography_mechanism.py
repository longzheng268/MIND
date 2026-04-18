import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import nibabel as nib
from sklearn.linear_model import LinearRegression

import abagen
from nilearn import datasets, plotting

from config import *
from step4_ml.step4_ml_shared import (
    DEMOGRAPHIC_COLS,
    MIND_COLS,
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
BASE_OUTPUT_DIR = './MIND_Research_Results/ML_Prediction/Aim3_Plan3_Topography_Mechanism/'
AHBA_ENABLE = os.getenv('STEP4_AHBA_ENABLE', '1') == '1'
AHBA_GENE_GROUP = os.getenv('STEP4_AHBA_GENE_GROUP', 'brain')
AHBA_DONORS_ENV = os.getenv('STEP4_AHBA_DONORS', 'all')


def _parse_ahba_donors(raw_value):
    text = str(raw_value).strip()
    if not text or text.lower() == 'all':
        return 'all'
    parts = [x.strip() for x in text.split(',') if x.strip()]
    return parts if parts else 'all'


def _safe_abagen_expression(atlas, atlas_info, gene_group_name='brain', donors='all'):
    genes = abagen.datasets.fetch_gene_group(gene_group_name)
    gene_set = {gene.upper() for gene in genes}
    expr = abagen.get_expression_data(
        atlas,
        atlas_info=atlas_info,
        donors=donors,
        data_dir=os.path.join(BASE_OUTPUT_DIR, '.abagen_cache'),
        return_counts=False,
        return_donors=False,
        verbose=0,
    )
    if isinstance(expr, pd.DataFrame):
        expr_df = expr.copy()
    else:
        expr_df = pd.DataFrame(expr)

    # Normalize orientation to regions x genes if needed.
    if expr_df.shape[0] < expr_df.shape[1]:
        expr_df = expr_df.T

    selected = [col for col in expr_df.columns if str(col).upper() in gene_set]
    if not selected:
        selected = expr_df.columns.tolist()

    regional_score = expr_df[selected].mean(axis=1)
    if regional_score.isna().all():
        regional_score = expr_df.mean(axis=1)
    regional_score = regional_score.fillna(regional_score.mean())
    return regional_score, genes, expr_df


def _run_ahba_overlay(base_out_dir, gene_group_name='brain'):
    ahba_dir = ensure_dir(os.path.join(base_out_dir, 'AHBA'))
    print(f'[Plan3] AHBA stage started (gene group: {gene_group_name})', flush=True)
    donor_candidates = []
    env_donors = _parse_ahba_donors(AHBA_DONORS_ENV)
    donor_candidates.append(env_donors)
    if env_donors == 'all':
        donor_candidates.extend([
            ['10021', '12876', '14380', '15496', '15697'],
            ['10021', '12876', '14380'],
            ['15496', '15697'],
        ])
    errors = []

    atlas = abagen.datasets.fetch_desikan_killiany(native=False, surface=False)

    for idx, donors in enumerate(donor_candidates, start=1):
        try:
            print(f'[Plan3] AHBA try {idx}/{len(donor_candidates)} | donors={donors}', flush=True)
            regional_score, genes, expr_df = _safe_abagen_expression(
                atlas['image'],
                atlas['info'],
                gene_group_name=gene_group_name,
                donors=donors,
            )
            expr_df.to_csv(os.path.join(ahba_dir, 'AHBA_Brain_Expression.csv'), index=False, encoding='utf-8-sig')
            pd.DataFrame({
                'Gene_Group': [gene_group_name],
                'Gene_Count': [len(genes)],
                'Donors_Used': [','.join(donors) if isinstance(donors, list) else str(donors)],
                'Regional_Mean': [float(regional_score.mean())],
            }).to_csv(os.path.join(ahba_dir, 'AHBA_Brain_Summary.csv'), index=False, encoding='utf-8-sig')
            ahba_fig_path = _save_ahba_overlay(ahba_dir, regional_score, atlas['image'], atlas['info'], f'{gene_group_name} gene group')
            print(f'[Plan3] AHBA stage complete: {ahba_fig_path}', flush=True)
            return ahba_fig_path
        except Exception as exc:
            errors.append(f'try {idx} donors={donors}: {exc}')
            # Corrupted partial download is common with remote AHBA fetches; clean microarray cache before retry.
            microarray_cache = os.path.join(base_out_dir, '.abagen_cache', 'microarray')
            if os.path.isdir(microarray_cache):
                shutil.rmtree(microarray_cache, ignore_errors=True)
            print(f'[Plan3] AHBA try {idx} failed: {exc}', flush=True)

    try:
        raise RuntimeError('\n'.join(errors) if errors else 'Unknown AHBA failure')
    except Exception as exc:
        with open(os.path.join(ahba_dir, 'AHBA_Fallback_Notes.txt'), 'w', encoding='utf-8') as f:
            f.write('AHBA overlay could not be generated.\n')
            f.write(f'Error: {exc}\n')
        print(f'[Plan3] AHBA stage failed: {exc}', flush=True)
        return None


def _feature_contrast(df, target_group, reference_group='prodromal_SAA+'):
    contrast_rows = []
    available_mind = [col for col in MIND_COLS if col in df.columns]
    covars = [col for col in DEMOGRAPHIC_COLS if col in df.columns]

    work = coerce_numeric(df, available_mind + [col for col in covars if col != 'Sex'])
    for col in available_mind:
        model_df = work[['Group_MIND', col] + [c for c in covars if c in work.columns]].copy()
        model_df[col] = pd.to_numeric(model_df[col], errors='coerce')
        model_df = model_df[model_df['Group_MIND'].isin([reference_group, target_group])].copy()
        model_df = model_df.dropna(subset=[col]).copy()
        if len(model_df) < 6:
            continue

        model_df['Group_Binary'] = (model_df['Group_MIND'] == target_group).astype(int)
        x_cols = ['Group_Binary'] + [c for c in covars if c in model_df.columns]
        x = model_df[x_cols].copy()
        if 'Sex' in x.columns:
            x['Sex'] = pd.to_numeric(x['Sex'], errors='coerce')
        x = x.fillna(x.median(numeric_only=True))
        y = model_df[col].astype(float)

        reg = LinearRegression()
        reg.fit(x, y)
        contrast_rows.append({
            'Feature': col,
            'Target_Group': target_group,
            'Reference_Group': reference_group,
            'N': int(len(model_df)),
            'Adjusted_Group_Effect': float(reg.coef_[0]),
            'Mean_Target': float(model_df.loc[model_df['Group_MIND'] == target_group, col].mean()),
            'Mean_Reference': float(model_df.loc[model_df['Group_MIND'] == reference_group, col].mean()),
            'Raw_Difference': float(
                model_df.loc[model_df['Group_MIND'] == target_group, col].mean()
                - model_df.loc[model_df['Group_MIND'] == reference_group, col].mean()
            ),
        })
    return pd.DataFrame(contrast_rows)


def _make_topography_index(df):
    mind_cols = [col for col in MIND_COLS if col in df.columns]
    if not mind_cols:
        raise ValueError('No MIND columns available for Plan 3.')

    zf = zscore_frame(df, mind_cols).fillna(0.0)
    out = df.copy()
    out['Topography_Index'] = zf.abs().mean(axis=1)
    out['Topography_Signed_Mean'] = zf.mean(axis=1)
    return out, mind_cols


def _save_feature_plot(contrast_df, out_dir):
    if contrast_df.empty:
        return None

    ordered = contrast_df.sort_values('Adjusted_Group_Effect')
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    colors = ['#b2182b' if val < 0 else '#2166ac' for val in ordered['Adjusted_Group_Effect']]
    ax.barh(ordered['Feature'], ordered['Adjusted_Group_Effect'], color=colors)
    ax.axvline(0, color='black', linewidth=1, alpha=0.7)
    ax.set_xlabel('Adjusted Group Effect')
    ax.set_ylabel('MIND Feature')
    ax.set_title('Plan 3 Topography Contrast')
    fig_path = os.path.join(out_dir, 'Plan3_Topography_Contrast.png')
    fig.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.show(block=True)
    plt.close(fig)
    return fig_path


def _save_ahba_overlay(out_dir, regional_score, atlas_img, atlas_info, title_suffix):
    atlas_labels = pd.read_csv(atlas_info).sort_values('id').reset_index(drop=True)
    atlas_img_obj = nib.load(atlas_img)
    atlas_data = atlas_img_obj.get_fdata().astype(int)
    overlay_data = np.zeros_like(atlas_data, dtype=float)

    # The abagen expression rows follow the atlas label ordering, so we map by atlas id.
    score_values = pd.Series(regional_score).reset_index(drop=True)
    if len(score_values) < len(atlas_labels):
        score_values = score_values.reindex(range(len(atlas_labels))).fillna(score_values.mean())

    for idx, label_id in enumerate(atlas_labels['id'].tolist()):
        overlay_data[atlas_data == int(label_id)] = float(score_values.iloc[idx])

    score_img = nib.Nifti1Image(overlay_data, affine=atlas_img_obj.affine, header=atlas_img_obj.header)
    fig = plotting.plot_stat_map(
        score_img,
        title=f'AHBA mechanism overlay | {title_suffix}',
        display_mode='ortho',
        colorbar=True,
        cmap='viridis',
        cut_coords=None,
    )
    fig_path = os.path.join(out_dir, 'AHBA_Mechanism_Overlay.png')
    fig.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close('all')
    return fig_path


def run_plan3_topography_mechanism():
    print('\n' + '=' * 60)
    print('Step 4 Plan 3: SAA+ topography-mechanism')
    print('=' * 60)

    df_raw = load_raw_dataframe(DATA_FILE)
    df = get_saa_positive_table(df_raw)
    df = df[df['Group_MIND'].isin(['prodromal_SAA+', 'PD_SAA+'])].copy()
    if df.empty:
        print('No SAA+ subjects available for Plan 3.')
        return

    print(f'[Plan3] baseline SAA+ subjects: {len(df)}', flush=True)
    df, mind_cols = _make_topography_index(df)
    ensure_dir(BASE_OUTPUT_DIR)

    out_rows = []
    feature_frames = []
    print('[Plan3] topography contrast stage started', flush=True)
    for target_group in ['PD_SAA+', 'prodromal_SAA+']:
        reference_group = 'prodromal_SAA+' if target_group == 'PD_SAA+' else 'PD_SAA+'
        contrast_df = _feature_contrast(df, target_group=target_group, reference_group=reference_group)
        if contrast_df.empty:
            continue
        contrast_df['Contrast_Pair'] = f'{target_group}_vs_{reference_group}'
        feature_frames.append(contrast_df)
        out_rows.append({
            'Contrast_Pair': f'{target_group}_vs_{reference_group}',
            'N_Features': int(len(contrast_df)),
            'Mean_Adjusted_Effect': float(contrast_df['Adjusted_Group_Effect'].mean()),
            'Mean_Raw_Difference': float(contrast_df['Raw_Difference'].mean()),
        })

    contrast_all = pd.concat(feature_frames, ignore_index=True) if feature_frames else pd.DataFrame()
    if contrast_all.empty:
        print('Plan 3 could not assemble feature contrasts.')
        return

    contrast_all.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan3_Topography_Feature_Contrasts.csv'), index=False, encoding='utf-8-sig')
    overview_df = pd.DataFrame(out_rows)
    overview_df.to_csv(os.path.join(BASE_OUTPUT_DIR, 'Plan3_Topography_Overview.csv'), index=False, encoding='utf-8-sig')
    print(f'[Plan3] topography contrasts saved: {len(contrast_all)} rows', flush=True)

    ahba_fig_path = None
    if AHBA_ENABLE:
        ahba_fig_path = _run_ahba_overlay(BASE_OUTPUT_DIR, gene_group_name=AHBA_GENE_GROUP)
    else:
        print('[Plan3] AHBA stage skipped (STEP4_AHBA_ENABLE=0)', flush=True)

    for pair_name, pair_df in contrast_all.groupby('Contrast_Pair'):
        pair_dir = ensure_dir(os.path.join(BASE_OUTPUT_DIR, pair_name))
        pair_df.to_csv(os.path.join(pair_dir, 'Feature_Contrasts.csv'), index=False, encoding='utf-8-sig')
        plot_path = _save_feature_plot(pair_df, pair_dir)
        with open(os.path.join(pair_dir, 'Plan3_Topography_Notes.txt'), 'w', encoding='utf-8') as f:
            f.write('PLAN 3: TOPOGRAPHY AND MECHANISM\n')
            f.write(f'Pair: {pair_name}\n')
            f.write(f'Available MIND features: {", ".join(mind_cols)}\n')
            f.write('Topography_Index = mean absolute z-score across available MIND features.\n')
            f.write(f'Plot: {plot_path or "not generated"}\n')
            f.write(f'AHBA overlay: {ahba_fig_path or "not generated"}\n')

    df[['Original_SUB_ID', 'Group_MIND', 'Topography_Index', 'Topography_Signed_Mean']].to_csv(
        os.path.join(BASE_OUTPUT_DIR, 'Plan3_Topography_Subject_Scores.csv'), index=False, encoding='utf-8-sig'
    )

    print(f'Plan 3 complete. Results saved to: {BASE_OUTPUT_DIR}')


if __name__ == '__main__':
    run_plan3_topography_mechanism()

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from config import *


DATA_FILE = './scale/MIND_baseline_with_followup_V04_V12.csv'
NON_HC_GROUPS = ['prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']
SAA_POSITIVE_GROUPS = ['prodromal_SAA+', 'PD_SAA+']
BL_EVENT = 'BL'

SAA_BURDEN_COLS = [
    'LEDD_Baseline', 'GDS15_all', 'RBDSQ_all', 'ESS_all',
    'SCOPA_AUT_all', 'NP1APAT', 'NP1FATG',
]

MIND_COLS = [
    'MIND_Sig_Index', 'MIND_Visual', 'MIND_Somatomotor',
    'MIND_Dorsal_Attention', 'MIND_Ventral_Attention',
    'MIND_Limbic', 'MIND_Frontoparietal', 'MIND_Default',
]

DEMOGRAPHIC_COLS = ['Age_at_Visit', 'Sex', 'Education']


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def load_raw_dataframe(data_file=DATA_FILE):
    if not os.path.exists(data_file):
        raise FileNotFoundError(f'Missing data file: {data_file}')
    return pd.read_csv(data_file)


def encode_binary_columns(df):
    out = df.copy()
    if 'Sex' in out.columns:
        sex_series = out['Sex']
        if not pd.api.types.is_numeric_dtype(sex_series):
            out['Sex'] = sex_series.map({'M': 1, 'F': 0, 'Male': 1, 'Female': 0, '1': 1, '0': 0})
    if 'SAA_Status' in out.columns:
        out['SAA_Binary'] = out['SAA_Status'].map({'Negative': 0, 'Positive': 1})
    return out


def _filter_groups(df, groups):
    out = df.copy()
    out = out[out['Group_MIND'].isin(groups)].copy()
    out = out[out['SAA_Status'].isin(['Negative', 'Positive'])].copy()
    return out


def get_baseline_table(df_raw, groups=None):
    groups = groups or NON_HC_GROUPS
    df_bl = df_raw[df_raw['EVENT_ID'] == BL_EVENT].copy()
    df_bl = _filter_groups(df_bl, groups)
    df_bl = df_bl.drop_duplicates(subset='Original_SUB_ID', keep='first').reset_index(drop=True)
    return encode_binary_columns(df_bl)


def get_saa_positive_table(df_raw):
    df_bl = get_baseline_table(df_raw, groups=SAA_POSITIVE_GROUPS)
    return df_bl[df_bl['Group_MIND'].isin(SAA_POSITIVE_GROUPS)].copy().reset_index(drop=True)


def available_cols(df, cols):
    return [col for col in cols if col in df.columns]


def coerce_numeric(df, cols):
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors='coerce')
    return out


def alias_scale_column(df, scale):
    aliases = {
        'MoCA': ['MoCA'],
        'UPDRS3': ['UPDRS3', 'UPDRSIII', 'UPDRSIII.1'],
    }
    for col in aliases.get(scale, [scale]):
        if col in df.columns:
            return col
    raise KeyError(f'Could not find scale column: {scale}')


def zscore_frame(df, cols):
    work = coerce_numeric(df, cols)
    out = pd.DataFrame(index=work.index)
    for col in cols:
        series = work[col]
        mean = series.mean(skipna=True)
        std = series.std(skipna=True, ddof=0)
        if pd.isna(std) or std == 0:
            out[col] = 0.0
        else:
            out[col] = (series - mean) / std
    return out


def make_balanced_subject_split(df_subjects, random_state=42, train_ratio=0.7, test_ratio=0.3, max_attempts=50):
    if 'Original_SUB_ID' not in df_subjects.columns:
        raise KeyError('Original_SUB_ID is required for subject-level splitting')

    split_df = df_subjects[['Original_SUB_ID']].drop_duplicates().copy()
    for col in ['Group_MIND', 'SAA_Status']:
        if col in df_subjects.columns:
            split_df = split_df.merge(
                df_subjects[['Original_SUB_ID', col]].drop_duplicates(),
                on='Original_SUB_ID',
                how='left',
            )

    split_df = split_df.sort_values('Original_SUB_ID').reset_index(drop=True)

    candidates = []
    if {'Group_MIND', 'SAA_Status'}.issubset(split_df.columns):
        split_df['Split_Strata'] = split_df['Group_MIND'].astype(str) + '__' + split_df['SAA_Status'].astype(str)
        candidates.append('Split_Strata')
    if 'Group_MIND' in split_df.columns:
        candidates.append('Group_MIND')

    chosen = None
    best_score = None
    for attempt in range(max_attempts):
        seed = random_state + attempt
        for strat_col in candidates:
            strata = split_df[strat_col]
            if strata.value_counts().min() < 2:
                continue
            try:
                train_ids, test_ids = train_test_split(
                    split_df['Original_SUB_ID'],
                    test_size=test_ratio,
                    train_size=train_ratio,
                    random_state=seed,
                    stratify=strata,
                )
            except ValueError:
                continue

            split_tmp = split_df.copy()
            split_tmp['Split'] = 'train'
            split_tmp.loc[split_tmp['Original_SUB_ID'].isin(test_ids), 'Split'] = 'test'

            # Prefer splits that preserve all observable disease groups in both folds.
            if 'Group_MIND' in split_tmp.columns:
                group_counts = split_tmp.groupby(['Group_MIND', 'Split']).size().unstack(fill_value=0)
                if (group_counts.min(axis=1) > 0).all():
                    return split_tmp.drop(columns=['Split_Strata'], errors='ignore')
                score = int((group_counts.min(axis=1) == 0).sum())
            else:
                score = 0

            if best_score is None or score < best_score:
                best_score = score
                chosen = split_tmp

    if chosen is None:
        raise ValueError('Could not construct a balanced train/test split')

    return chosen.drop(columns=['Split_Strata'], errors='ignore')

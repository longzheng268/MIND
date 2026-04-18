# Plan 2 - Incremental Predictive Value

## Scope
- Compare Model A/B/C/D in Parkinson-spectrum non-HC subjects.
- Primary outcomes: fixed-window delta of UPDRS3 and MoCA.
- Balanced 7:3 subject-level train/test split, train-only preprocessing, and ROC/AUC outputs on the held-out test set.

## Current implementation
- Active script remains `step4_ml/step4_ml_prediction.py`.

## Style
- Must follow global style in `config.py` via `apply_style()`.

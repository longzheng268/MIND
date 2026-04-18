# Step4 Aim 3 Workspace (Three-Plan Parallel Layout)

## Current active plan
- Active now: Plan 2 (incremental predictive value).
- Main runnable script: `step4_ml/step4_ml_prediction.py`.

## Implemented entry points
- `step4_ml/step4_ml_prediction.py`
  - Plan 2: incremental predictive value.
  - Uses a persisted, balanced 7:3 subject-level split and writes ROC/AUC outputs for the held-out test set.
- `step4_ml/plan2_incremental_prediction/step4_plan2_incremental_prediction.py`
  - Plan 2 package entry point.
- `step4_ml/plan1_burden_resilience/step4_plan1_burden_resilience.py`
  - Plan 1: SAA+ burden-resilience.
- `step4_ml/plan3_topography_mechanism/step4_plan3_topography_mechanism.py`
  - Plan 3: SAA+ topography-mechanism.
  - Includes an AHBA atlas overlay path via `abagen` + Desikan-Killiany.

## Module layout
- `step4_ml/step4_ml_shared.py`
  - Shared data loading, filtering, and encoding utilities.
- `step4_ml/__init__.py`
  - Package marker for Step4 imports.
- `step4_ml/plan1_burden_resilience/__init__.py`
- `step4_ml/plan2_incremental_prediction/__init__.py`
- `step4_ml/plan3_topography_mechanism/__init__.py`

## Directory layout
- `step4_ml/plan1_burden_resilience/`
  - Plan 1: SAA+ burden-resilience framework.
- `step4_ml/plan2_incremental_prediction/`
  - Plan 2: incremental predictive value (Model A/B/C/D and future E/F).
- `step4_ml/plan3_topography_mechanism/`
  - Plan 3: SAA+ topography-phenotype-mechanism framework.

## Style policy (mandatory)
- `config.py` is the absolute reference for plotting style.
- All Step4 scripts must call:
  - `from config import *`
  - `apply_style()`
- No script is allowed to define local style palettes, rcParams overrides, or custom global style that conflicts with `config.py`.

## Notes
- Keep `step4_ml/step4_ml_prediction.py` as a stable compatibility entry point.
- If plan-specific scripts are added, store them under the corresponding `plan*` folder and keep outputs separated under `MIND_Research_Results/ML_Prediction/`.

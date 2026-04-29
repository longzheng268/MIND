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
  - Includes Allen/AHBA atlas overlay stage (default enabled for full mode).
- `step4_ml/plan3_topography_mechanism/step4_plan3_topography_mechanism.py`
  - Plan 3: SAA+ topography-mechanism.
  - Focuses on topography contrasts; Allen/AHBA is no longer the default Plan3 stage.

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
- Optimization and redesign draft: `step4_ml/STEP4_Optimization_Activation_DimRed.md`

## Unified Entry

- Goal: one CLI to run Plan1/Plan2/Plan3 with a single start command.
- Implemented entry: `step4_ml/step4_entry.py`

Usage examples:

```bash
# interactive menu: choose 1/2/3/all/q at runtime
python step4_ml/step4_entry.py

# direct run without menu
python step4_ml/step4_entry.py --plan 1
python step4_ml/step4_entry.py --plan 2
python step4_ml/step4_entry.py --plan 3
python step4_ml/step4_entry.py --plan all

# run quick mode (faster, non-blocking friendly)
python step4_ml/step4_entry.py --plan all --mode quick

# quick mode with custom Plan2 windows
python step4_ml/step4_entry.py --plan 2 --mode quick --quick-windows V06,V10

# skip Allen/AHBA for Plan1
python step4_ml/step4_entry.py --plan 1 --mode quick

# custom AHBA cache directory (used by Plan1 Allen stage)
python step4_ml/step4_entry.py --plan 1 --cache-dir ./MIND_Research_Results/ML_Prediction/AHBA_CACHE

# report-only (do not run model; only summarize existing key artifacts)
python step4_ml/step4_entry.py --plan all --report-only

# generate Chinese markdown summary after run/report
python step4_ml/step4_entry.py --plan all --report-only --summary
```

Unified entry outputs:
- `MIND_Research_Results/ML_Prediction/Step4_Entry_Overview.csv`
- `MIND_Research_Results/ML_Prediction/Step4_Entry_RunLog.txt`
- `MIND_Research_Results/ML_Prediction/Step4_Entry_Summary_CN.md`

Summary markdown now includes a delta section that compares each plan with its previous recorded run
(status/artifact marker/duration difference) based on `Step4_Entry_Overview.csv`.

Quick mode behavior (v1):
- Plan1: disable interactive figure preview (`STEP4_PLAN1_PREVIEW=0`)
- Plan1: disable Allen/AHBA stage (`STEP4_PLAN1_ALLEN_ENABLE=0`)
- Plan2: run only `V06`, disable figure preview, and skip ROC curve image rendering
- Plan3: disable interactive figure preview

Recent robustness updates:
- Plan2 summary now writes `Reliability label` (high/moderate/low) based on sample size.
- Plan2 overview now includes `N`, `Train_N`, `Test_N`, and `Reliability` columns.
- Plan1 Allen/AHBA supports local fallback expression matrix via env var `STEP4_AHBA_LOCAL_EXPRESSION`.

## 最新结果快照（2026-04-18，mind 环境）

- Plan 1（burden-resilience）
  - 运行脚本：`step4_ml/plan1_burden_resilience/step4_plan1_burden_resilience.py`
  - 状态：已完成。
  - 输出目录：`MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/`
  - 关键汇总：
    - `UPDRS3`: `N=557`, `R2=0.0202`
    - `MoCA`: `N=566`, `R2=0.0889`

- Plan 2（incremental predictive value）
  - 主结果目录：`MIND_Research_Results/ML_Prediction/Aim3_Incremental/`
  - 关键汇总（`Aim3_Incremental_Overview.csv`）：
    - `UPDRS3 V06` 最优模型：`Model_B_Clinical_SAA`
    - `MoCA V06` 最优模型：`Model_D_Clinical_SAA_MIND`

- Plan 3（topography-mechanism）
  - 运行脚本：`step4_ml/plan3_topography_mechanism/step4_plan3_topography_mechanism.py`
  - topography 状态：已完成（16 行 contrasts 已写出）。
  - 当前可报告范围：topography 可报告。

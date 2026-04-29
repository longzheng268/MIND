# Plan 2 - Incremental Predictive Value

## Scope
- Compare Model A/B/C/D in Parkinson-spectrum non-HC subjects.
- Primary outcomes: fixed-window delta of UPDRS3 and MoCA.
- Balanced 7:3 subject-level train/test split, train-only preprocessing, and ROC/AUC outputs on the held-out test set.

## Current implementation
- Active script remains `step4_ml/step4_ml_prediction.py`.

## Style
- Must follow global style in `config.py` via `apply_style()`.

## 最新运行状态（2026-04-18，mind 环境）

- 主脚本：`step4_ml/step4_ml_prediction.py`
- 结果目录：`./MIND_Research_Results/ML_Prediction/Aim3_Incremental/`
- 关键汇总文件：
	- `Aim3_Incremental_Overview.csv`
	- `Aim3_ROC_Overview.csv`

关键汇总（Overview）：
- `UPDRS3 V06` 最优模型：`Model_B_Clinical_SAA`（Test RMSE `7.8736`）
- `UPDRS3 V10` 最优模型：`Model_A_Clinical`（Test RMSE `12.3552`）
- `MoCA V06` 最优模型：`Model_D_Clinical_SAA_MIND`（Test RMSE `1.9208`）
- `MoCA V10` 最优模型：`Model_A_Clinical`（Test RMSE `2.3909`）

当前解读：
- 增量价值在部分终点/时间窗成立（以 `MoCA V06` 最明显），并非所有任务均稳定提升。

## 下一步优化（2026-04-19）

- 降维与非线性特征工程：
	- 增加二阶交互特征（`PolynomialFeatures(interaction_only=True)`）
	- 在训练折内执行降维，避免信息泄漏
- 挑战模型补充：
	- 增加 `XGBoost`（`reg:pseudohubererror` / `reg:squaredlogerror`）
	- 保留 `ElasticNet` 作为可解释主模型
- 稳健性评估：
	- 按 endpoint 统一输出 delta 指标（相对 Model A 的 dR2/dRMSE）
	- 增加随机种子重复评估（split sensitivity）

统一入口设计见：`step4_ml/STEP4_Optimization_Activation_DimRed.md`

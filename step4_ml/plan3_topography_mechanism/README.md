# Plan 3 - Topography and Mechanism

## Scope
- SAA+ MIND topography phenotype construction.
- Domain-specific longitudinal mapping (motor/cognitive/non-motor).
- Hub vulnerability, epicenter, and imaging-transcriptomics annotation.
- Topography contrast reporting (Allen/AHBA not required in Plan3 default flow).

Allen/AHBA has been moved to Plan1 as the primary mechanism overlay path.
Plan3 keeps an optional legacy AHBA branch only when `STEP4_AHBA_ENABLE=1` is set manually.

## Script
- `step4_plan3_topography_mechanism.py`

## Style
- Must follow global style in `config.py` via `apply_style()`.

## 最新运行状态（2026-04-18，mind 环境）

- 运行脚本：`step4_plan3_topography_mechanism.py`
- topography 阶段：成功完成。
	- baseline SAA+ 样本：`569`
	- 对比输出：`16` 行
	- 关键文件：
		- `Plan3_Topography_Feature_Contrasts.csv`
		- `Plan3_Topography_Overview.csv`
		- `Plan3_Topography_Subject_Scores.csv`

当前可报告范围：
- 可报告：SAA+ topography 对比结果。

## 下一步优化（2026-04-19）

- 拓扑特征压缩：
	- 对异常拓扑值使用 `tanh` 压缩到 `[-1, 1]`
	- hub vulnerability 采用 softmax 加权，增强可解释性
- 空间关联优化：
	- 由 Pearson 扩展到 Spearman（rank-based）以捕捉单调非线性
- 机制层若需补充，建议统一走 Plan1 的 Allen/AHBA 输出路径。

统一入口设计见：`step4_ml/STEP4_Optimization_Activation_DimRed.md`

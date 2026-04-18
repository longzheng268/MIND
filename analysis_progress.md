# MIND Analysis — Progress Tracker

> Last updated: 2026-04-18

---

## Overall Pipeline

```
Step 1  →  Step 2a/b/c/d  →  Step 2_stats  →  Step 3  →  Step 4 (prediction / Aim 3)
 [✓]           [✓]              [✓]            [✓]          [ ]
```

---

## Recent fixes and current recommendation

- `step2a_global_mind_comparison.py` has been fixed for the `GROUP_ORDER` bug and now uses blocking display (`plt.show(block=True)`).
- `config.py` now uses `plt.ioff()` and a smaller default preview window while preserving `savefig.dpi=300`.
- `step2d_edgewise_analysis.py` runs successfully in the `mind` environment after the data path fix.
- `step2b_network_ancova_7nets.py` is the current recommended Step 2b inference script for four-group baseline MIND network differences.
- `step2b_connectome_viz.py` is kept only as a legacy visualization script and should not be treated as the primary inference path.
- `step3_lme_updrs.py` now auto-detects `UPDRS3/UPDRSIII/UPDRSIII.1` and runs successfully in the current dataset.
- `step3c_lme_multiscale.py` now supports both `FullTimeline` and `2Year` outputs with config-governed labels, xticks, sparse-visit filtering, save-first naming, and blocking preview.
- `step3d_baseline_regression.py` has been updated from an outdated wide-table assumption to the current long-table workflow and now runs successfully.
- `step3d_baseline_regression.py` now keeps `V10` and `V12` as the primary figure groups, restores paired Figure 1 / Figure 2 outputs for each endpoint, and previews the saved figures with blocking display.
- `step3d_baseline_regression.py` now aligns its boxplot / stripplot / title / grid conventions with the broader Step 2–3 config-driven style.
- `step3d_baseline_regression.py` Aim 3 now skips degenerate non-HC subsets instead of reporting spurious perfect `R²`.
- `step3e_lme_nonmotor_extended.py` now supports both `FullTimeline` and `2Year` outputs under config-governed time definitions, labels, and sparse-visit plotting thresholds.
- `step3f_saa_subgroup_analysis.py` analysis 2 now supports both `FullTimeline` and `2Year` LME outputs, while analysis 1 remains BL-only ANCOVA.
- `step4_ml/step4_ml_prediction.py` now pivots from a simple SAA-status prototype to an Aim 3 incremental-value framework that compares Model A/B/C/D across Parkinson-spectrum subsets using available baseline clinical, SAA, and MIND modules.
- `config.py` now governs the actual full Step 3 timeline as `BL/V04/V06/V08/V10/V12` (no `V02` in the current dataset), and plot titles/xticks are generated from config.

### Latest Step 3 findings (2026-04-09)

- `step3_lme_updrs.py`
  - Model A and Model B both completed.
  - `Time:MIND_BL` is not significant in the current data.
  - Significant time interactions are present for `prodromal_SAA+` and `PD_SAA+`.
- `step3c_lme_multiscale.py`
  - The 6 multiscale outcomes now produce paired `FullTimeline` and `2Year` artifacts per scale directory.
  - Full-timeline plotting now drops overly sparse late visits using the shared `STEP3_FULL_MIN_PLOT_N` rule before drawing trajectories.
- `step3d_baseline_regression.py`
  - Current primary outputs focus on paired `V10` and `V12` figure groups.
  - Each group restores two figures: `Aim2_Group_Delta_Boxplot_{V10/V12}.png` and `Aim2_MIND_Prediction_{V10/V12}.png`.
  - Latest matched sample sizes: `V10 n=144`, `V12 n=81`.
  - Aim 3 reports valid incremental-value results for `V10`, while `V12` is skipped because non-HC `n=3` is below the safeguard threshold.
- `step3f_saa_subgroup_analysis.py`
  - BL SAA+ vs SAA- ANCOVA: Global/Visual/Dorsal/Ventral/Limbic/Frontoparietal/Default are significant after FDR; Somatomotor is not.
  - SAA subgroup LME: neither `Time:MIND_BL` nor `Time:SAA_Status` interaction is significant for MoCA or UPDRS3 in the current data.
- `step4_ml/step4_ml_prediction.py`
  - Regression: MoCA Δ and UPDRS3 Δ both show weak predictive performance; best model is ElasticNet for both tasks.
  - Classification: SAA+ vs SAA- reaches best AUC with SVC (`~0.704`) and best accuracy with LogisticRegression (`~0.705`).

- `step4_ml/step4_ml_prediction.py`
  - Step 4 is being refactored toward Aim 3 incremental model comparison instead of predicting SAA status itself.
  - The current implementation targets Parkinson-spectrum subsets, fixed-window `UPDRS3` / `MoCA` progression deltas, and Model A/B/C/D comparisons; conventional MRI, SAA kinetics, and phenoconversion remain unavailable in the present repo state.

---

## Step 1 — Mean Surface Maps

| Script | Status | Outputs |
|---|---|---|
| `step1_mean_surface_maps.py` | ✅ Ready | Per-group mean surface plots via nilearn |

---

## Step 2a — Global MIND Comparison

| Script | Status | Outputs |
|---|---|---|
| `step2a_global_mind_comparison.py` | ✅ Ready | Radar, boxplot, brain surface T-map, connectome |

**Validated fixes (2026-04-09):**
- `GROUPS` → `GROUP_ORDER`
- blocking `plt.show(block=True)` restored
- display behavior unified through `config.py`

---

## Step 2b — 7-Network Level

| Script | Status | Outputs |
|---|---|---|
| `step2b_7network_radar_boxplot.py` | ✅ Ready | Radar chart + side-by-side boxplots |
| `step2b_network_ancova_7nets.py` | ✅ Ready | 7-network ANCOVA inference stats |
| `step2b_connectome_viz.py` | ⚠️ Legacy | Old nilearn connectome visualization |

**Current recommended result source:**
- Use `step2b_network_ancova_7nets.py` as the main Step 2b result for reporting.
- Latest observed ANCOVA + FDR results:

| Network | p_uncorrected | p_fdr |
|---|---:|---:|
| MIND_Visual | 0.000418 | 0.000975 |
| MIND_Somatomotor | 0.805643 | 0.805643 |
| MIND_Dorsal_Attention | 0.027740 | 0.032364 |
| MIND_Ventral_Attention | 0.019777 | 0.027688 |
| MIND_Limbic | 0.000557 | 0.000975 |
| MIND_Frontoparietal | 0.000155 | 0.000764 |
| MIND_Default | 0.000218 | 0.000764 |

---

## Step 2c — Nodal Strength

| Script | Merged from | Status | Output Dir |
|---|---|---|---|
| `step2c_nodal_strength_ancova.py` | `nodal_wise_ancova_stats.py` + `nodal_wise_ancova_stats_ver2.0.py` | ✅ **Merged** | `./nodal_statistical_results/` |

**Outputs preserved:**
- `Nodal_ANOVA_Results.csv`
- `Nodal_ANCOVA_Significance.png`
- `Top_Significant_Nodes_Bar.png`
- `Pairwise_Nodal_*.csv` (×6 pairs)
- `Nodal_T_Summary_Heatmap.png`
- `Best_Node_Boxplot.png`
- 3D brain surface T-maps per pair (nilearn)
- Hub Vulnerability correlation (printed)

---

## Step 2d — Edge-wise Analysis

| Script | Merged from | Status | Output Dir |
|---|---|---|---|
| `step2d_edgewise_analysis.py` | `step2d_edgewise_diff_heatmap.py` + `step2d_edgewise_violin_tmap.py` + `step2d_edgewise_anova_4group.py` + `step2d_edgewise_hub_module.py` | ✅ **Merged** | `./edgewise_results/` |

**Outputs preserved:**
- `Global_Edge_Boxplot.png`
- `Edge_Strength_Boxplot.png`
- `Nodal_Statistical_Results.csv`
- `Module_Level_Stats.csv`
- `Edge_ANCOVA_FDR_Map.png`
- `Top_Significant_Edge_Boxplot.png`
- `Edge_Diff_{g1}_vs_{g2}.png` (×6)
- `Edge_Tmap_{g1}_vs_{g2}.png` (×6, scipy t-test)
- `Edge_T_Map_{g1}_vs_{g2}.png` (×6, ANCOVA adjusted)
- `Nodal_ANCOVA_{g1}_vs_{g2}.csv` (×6)
- Hub Vulnerability correlation (printed per pair)

---

## Step 2 Stats — Connectome ANOVA

| Script | Merged from | Status | Output Dirs |
|---|---|---|---|
| `step2_stats_connectome_anova.py` | `step2_stats_connectome_anova_3group.py` + `step2_stats_connectome_anova_4group.py` | ✅ **Merged** | `./analysis_results_3group/` + `./analysis_results_4group/` |

**Outputs preserved:**
- `ANOVA_F_Matrix.csv` (per group variant)
- `ANOVA_Full_Edge_Table.csv` (per group variant, new: includes FDR)

| Script | Status | Outputs |
|---|---|---|
| `step2_stats_network_ancova.py` | ✅ Ready (standalone) | Network-level ANCOVA stats |
| `step2_stats_subgroup_aggregation.py` | ✅ Ready (standalone) | Subgroup data aggregation |

---

## Step 3 — LME Longitudinal Prediction

| Script | Merged from | Status | Output Dir |
|---|---|---|---|
| `step3_lme_updrs.py` | `step3a_lme_full_timepoints.py` + `step3b_lme_2year_updrs.py` | ✅ **Merged** | `./lme_updrs_results/` |

**Outputs preserved:**
- `ModelA_Full_TP_Trajectory.png` (MIND tertile, full timepoints)
- `ModelA_Full_TP_LME_Report.txt`
- `ModelB_2Year_Trajectory.png` (MIND binary, BL/V04/V06)
- `ModelB_2Year_LME_Report.txt`

| Script | Status | Outputs |
|---|---|---|
| `step3c_lme_multiscale.py` | ✅ Ready (standalone) | 6-scale LME with paired `FullTimeline` / `2Year` outputs per `./MIND_Research_Results/{scale}/` |
| `step3d_baseline_regression.py` | ✅ Ready (standalone) | Baseline regression prediction with `V10`/`V12` paired figures |
| `step3e_lme_nonmotor_extended.py` | ✅ Ready (standalone) | 5 新量表 LME（ESS/SCOPA/S-AI/T-AI/UPSIT） |
| `step3f_saa_subgroup_analysis.py` | ✅ Ready (standalone) | SAA 亚组：BL MIND ANCOVA + SAA 调节 LME |

---

## Step 4 — ML Prediction Model（Aim 3, downstream of the analysis steps）

**当前状态（2026-04-18）**：Step 4 是整条 MIND 分析链的预测收口阶段，承接 Step 1-3 的统计与纵向分析；当前已规整为三方案并行框架，主运行方案为方案二（增量预测价值评估）。

**三方案目录**：
- `step4_ml/plan1_burden_resilience/`：方案一（SAA+ burden-resilience）
- `step4_ml/plan2_incremental_prediction/`：方案二（incremental predictive value）
- `step4_ml/plan3_topography_mechanism/`：方案三（SAA+ topography-mechanism）

**方案二当前落地要点**：
- 主脚本：`step4_ml/step4_ml_prediction.py`
- 人群：Parkinson-spectrum 非 HC
- 结局：`UPDRS3` / `MoCA` 固定时间窗 delta（V06/V10/V12）
- 模型：Model A/B/C/D（ElasticNet 主模型）
- 验证：7:3 train/test split（subject-level、分层均衡、持久化到 `data/step4_ml/`）+ train-only CV + test-set 终评
- 新增输出：test-set ROC/AUC（`ROC_Curve.png`、`ROC_Summary.csv`、`ROC_Notes.txt`）
- 汇总输出：`MIND_Research_Results/ML_Prediction/Aim3_Incremental/Aim3_ROC_Overview.csv`
- 未落地模块：conventional MRI comparator、SAA kinetic、phenoconversion/Cox

**方案三当前进展（机制层）**：
- 已完成方案三核心拓扑产物落盘：`Plan3_Topography_Feature_Contrasts.csv`、`Plan3_Topography_Overview.csv`、`Plan3_Topography_Subject_Scores.csv`。
- 已接入 `abagen`（Allen Human Brain Atlas）与 Desikan-Killiany atlas 的叠加代码路径；AHBA 当前处于数据抓取/缓存执行阶段。

**图形样式规则**：
- `config.py` 仍是绝对参考；Step 4 相关可视化必须统一走 `apply_style()`，禁止局部样式覆写。

| Script | Status | Outputs |
|---|---|---|
| `step4_ml/step4_ml_prediction.py` | ✅ Active | 方案二：A/B/C/D 增量预测，train/test + test-set 终评 |

---

## Utility Files

| File | Purpose |
|---|---|
| `config.py` | Central visual constants + `apply_style()` |
| `utils_mindshow.py` | MIND visualization helpers |
| `MIND.py` | Core MIND computation |
| `MIND_helpers.py` | MIND helper functions |
| `getAllMindNet.py` | Batch MIND network extraction |
| `get_vertex_df.py` | Vertex data extraction |
| `register_and_vol2surf.py` | Volume-to-surface registration |

---

## Merge Summary

| New File | Source Files (deleted) |
|---|---|
| `step2c_nodal_strength_ancova.py` | `nodal_wise_ancova_stats.py`, `nodal_wise_ancova_stats_ver2.0.py` |
| `step2d_edgewise_analysis.py` | `step2d_edgewise_diff_heatmap.py`, `step2d_edgewise_violin_tmap.py`, `step2d_edgewise_anova_4group.py`, `step2d_edgewise_hub_module.py` |
| `step2_stats_connectome_anova.py` | `step2_stats_connectome_anova_3group.py`, `step2_stats_connectome_anova_4group.py` |
| `step3_lme_updrs.py` | `step3a_lme_full_timepoints.py`, `step3b_lme_2year_updrs.py` |

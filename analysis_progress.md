# MIND Analysis — Progress Tracker

> Last updated: 2026-04-07

---

## Overall Pipeline

```
Step 1  →  Step 2a/b/c/d  →  Step 2_stats  →  Step 3  →  Step 4 (TBD)
 [✓]           [✓]              [✓]            [✓]          [ ]
```

---

## Recent fixes and current recommendation

- `step2a_global_mind_comparison.py` has been fixed for the `GROUP_ORDER` bug and now uses blocking display (`plt.show(block=True)`).
- `config.py` now uses `plt.ioff()` and a smaller default preview window while preserving `savefig.dpi=300`.
- `step2d_edgewise_analysis.py` runs successfully in the `mind` environment after the data path fix.
- `step2b_network_ancova_7nets.py` is the current recommended Step 2b inference script for four-group baseline MIND network differences.
- `step2b_connectome_viz.py` is kept only as a legacy visualization script and should not be treated as the primary inference path.

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

**Validated fixes (2026-04-07):**
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
| `step3c_lme_2year_multiscale.py` | ✅ Ready (standalone) | 6-scale LME per `./MIND_Research_Results/{scale}/` |
| `step3d_baseline_regression.py` | ✅ Ready (standalone) | Baseline regression prediction |
| `step3e_lme_nonmotor_extended.py` | ✅ Ready (standalone) | 5 新量表 LME（ESS/SCOPA/S-AI/T-AI/UPSIT） |
| `step3f_saa_subgroup_analysis.py` | ✅ Ready (standalone) | SAA 亚组：BL MIND ANCOVA + SAA 调节 LME |

> ⚠️  `step3c_lme_2year_multiscale.py` still references `./量表/` — update to `./scale/`

---

## Step 4 — ML Prediction Model（Aim 3）

**目标**：在 Parkinson 连续谱中，评估 MIND 网络指标在 baseline clinical 和 SAA 之上的增量预测价值。

**推荐方案**（来自研究方案 4.4.13）：
- 主要结局：24 个月运动进展（UPDRS III 年化变化率）+ 24-36 个月认知进展（MoCA 年化变化率）
- 主模型：Elastic Net（连续 + 二分类），挑战模型：XGBoost
- 验证：nested cross-validation（外层 5-fold + 内层 5-fold）+ 独立测试集
- 模型层级：Model A (clinical) → B (+SAA) → C (+MIND) → D (+SAA+MIND) → E (+传统MRI) → F (全模态)

**当前数据可行性**（2026-03-31）：

| 指标 | 状态 | 说明 |
|---|---|---|
| BL+V06 配对 | 44 人 | prodromal_SAA-: 29, prodromal_SAA+: 6, PD_SAA+: 6 |
| BL+V04 配对 | 41 人 | — |
| ≥2 时间点 MoCA | 85 人 | prodromal_SAA-: 48, prodromal_SAA+: 9, PD_SAA+: 17 |
| ≥3 时间点 MoCA | 4 人 | 无法提取 LME slope |
| SAA kinetic 参数 | ❌ 无 | 仅 SAA_Status（二元） |
| 传统结构 MRI | ❌ 无 | data/ 仅含 MIND 矩阵，无 TIV/皮层厚度/灰质体积 |
| MIND 矩阵纵向 | ❌ 仅 BL | V04/V06 的 MIND 指标全缺失 |
| MIND 网络特征 | 8 维 | 全局 + 7 网络 |

**可行性评估**：
- **可做**：Elastic Net / XGBoost 预测 Δ（BL→V06），n=44，11 维特征（8 MIND + 3 人口学）
- **限制**：样本量极小（n=44），无法做完整 nested CV；SAA 亚组内 n=6，无法做有意义的分组预测
- **缺失**：Model E/F（传统 MRI 比较）不可行；SAA kinetic 探索不可行；Cox 生存模型不可行（事件数不足）
- **建议**：当前可先做简化版 Δ 预测 + 特征重要性，待后续数据补充后再扩展完整方案

**当前计划**：
- [ ] `step4_ml_prediction.py`：简化版 Δ 预测（Elastic Net / XGBoost），仅用现有 11 维特征
- [ ] 待补充：传统结构 MRI 数据、SAA kinetic 参数、更多纵向配对数据

| Script | Status | Outputs |
|---|---|---|
| `step4_ml/step4_ml_prediction.py` | ✅ 已创建 | SAA 亚组 Δ 预测（回归 + 分类） |

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

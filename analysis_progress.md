# MIND Analysis — Progress Tracker

> Last updated: 2026-03-27

---

## Overall Pipeline

```
Step 1  →  Step 2a/b/c/d  →  Step 2_stats  →  Step 3  →  Step 4 (TBD)
 [✓]           [✓]              [✓]            [✓]          [ ]
```

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

---

## Step 2b — 7-Network Level

| Script | Status | Outputs |
|---|---|---|
| `step2b_7network_radar_boxplot.py` | ✅ Ready | Radar chart + side-by-side boxplots |
| `step2b_network_ancova_7nets.py` | ✅ Ready | 7-network ANCOVA inference stats |
| `step2b_connectome_viz.py` | ✅ Ready | nilearn connectome visualization |

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

> ⚠️  `step3c_lme_2year_multiscale.py` still references `./量表/` — update to `./scale/`

---

## Step 4 — ML Prediction Model

| Script | Status | Notes |
|---|---|---|
| *(none yet)* | ❌ Not started | See `todolist.md` for scope |

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

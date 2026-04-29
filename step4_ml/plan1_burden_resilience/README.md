# Plan 1 - Aim 3 SAA+ Burden, Resilience and Mechanism Annotation

## Scope (aligned to 4.4.1-4.4.5)
- 4.4.1: Build `MIND burden score` in SAA+ using prior Step2 effect evidence (HC-referenced weighted composite), with fallback PCA.
- 4.4.2: Stage expression in SAA+ (`prodromal_SAA+` vs `PD_SAA+`) using regression with covariates.
- 4.4.3: Build motor/cognitive resilience using residual-based framework under burden and covariate adjustment.
- 4.4.4: Longitudinal validation with interaction terms `Time x Burden` and `Time x Resilience` in LME/OLS fallback.
- 4.4.5: Imaging-transcriptomics mechanism module: ROI abnormality map -> AHBA expression -> PLS -> hemisphere-preserving spatial null -> pathway/cell-type enrichment.

## Script
- `step4_plan1_burden_resilience.py`

## Style Policy
- Must follow global style in `config.py` via `apply_style()`.
- No local global-style override is allowed.

## Output Root
- `./MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/`

## Core Outputs
- Burden and stage:
	- `Plan1_Burden_Previous_Result_Evidence.csv`
	- `Plan1_Burden_Resilience_Summary.csv`
	- `Plan1_Stage_Expression_Logit.csv`
	- `Plan1_Stage_Expression_Summary.csv`
- Resilience and high-risk phenotype:
	- `Plan1_High_Risk_Phenotypes.csv`
- Longitudinal validation:
	- `Plan1_Longitudinal_Validation.csv`
	- `Plan1_Longitudinal_Fitted_Data.csv`
- Mechanism main outputs:
	- `Plan1_PLS_Region_Scores.csv`
	- `Plan1_PLS_Gene_Loadings.csv`
	- `Plan1_PLS_Null_Distribution.csv`
	- `Plan1_Pathway_Enrichment.csv` (if non-empty)
	- `Plan1_CellType_Enrichment.csv` (if non-empty)
	- `Plan1_Mechanism_Annotation.png`
	- `Mechanism/AHBA_Mechanism_Overlay.png`

## Figure Suite (A-E)
- `Figure_Suite/Figure_A_MIND_Abnormality_Map.png`
	- A1 surface map, A2 network summary, A3 region-wise top ranking.
- `Figure_Suite/Figure_B_PLS_Spatial_Null.png`
	- B1 component explained variance, B2 spatial null histogram, B3 region-wise association, B4 PLS1 surface map.
- `Figure_Suite/Figure_C_Gene_Level_Results.png`
	- C1 gene weights ranking, C2 top-gene network heatmap, C3 leading genes panel.
- `Figure_Suite/Figure_D_Pathway_Enrichment.png`
	- Positive/negative gene-list enrichment dot plots.
- `Figure_Suite/Figure_E_CellType_Enrichment.png`
	- E1 cell-type bubble plot, E2 sensitivity heatmap across Top-N gene sets.

## Supplementary Outputs
- `Supplementary/Supplementary_Figure_1_Workflow.png`
- `Supplementary/Supplementary_Figure_2_AHBA_Coverage.csv`
- `Supplementary/Supplementary_Figure_3_Spatial_Null.csv`
- `Supplementary/Supplementary_Figure_4_Sensitivity_Heatmap.csv` (if available)

## Statistics Annotation Table
- `Plan1_Figure_Statistics_Annotations.csv`
- Includes figure-wise statistics and metadata:
	- map/statistic type,
	- parcellation,
	- PLS1 explained variance,
	- spatial-null p-value,
	- correlation statistics,
	- FDR method and gene universe size.

## Allen / AHBA Path
- Plan1 AHBA output dir: `./MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/AHBA/`
- Raw Allen/AHBA resources: `./data/external/allen/`
- Cache dir: `./data/external/allen/cache/abagen/`

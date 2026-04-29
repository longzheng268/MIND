## 近期状态更新（2026-04-09）

- `step2b_connectome_viz.py` 已标记为 legacy visualization script，不再作为主分析链路的核心结果来源。
- `step3_lme_updrs.py` 已适配当前长表数据中的 `UPDRSIII/UPDRSIII.1` 命名，能够在 `mind` 环境中正常运行。
- `step3c_lme_multiscale.py` 已增加 `UPDRS3` 别名映射，能够兼容当前 CSV 列名并完成 6 个量表分析。
- `step3d_baseline_regression.py` 已从旧宽表假设切换为基于当前长表动态整理 BL/V04/V06/V10/V12 后再执行回归。
- `step3d_baseline_regression.py` 当前主输出聚焦 `V10` 与 `V12` 两组图片，并恢复每组 Figure 1 / Figure 2 成对结果。
- `step3d_baseline_regression.py` Aim 3 已加入退化样本保护，V12 非 HC 子样本不足时会自动跳过，避免出现 `R²=1.0000` 假完美结果。
- `step3d_baseline_regression.py` 绘图风格现已向 Step2/Step3 统一收敛，图幅、字体、grid、stripplot 样式、标题编号均受 `config.py` 监管。
- `step3d_baseline_regression.py` 现会先保存 PNG，再统一阻塞预览弹窗。
- `step4_ml/step4_ml_prediction.py` 是整条项目链路的预测阶段：在 Step 1-3 完成分析基础上，默认排除 HC，围绕 baseline clinical / SAA / MIND 三个模块比较 Model A/B/C/D，并以 `UPDRS3` / `MoCA` 固定时间窗进展结局为主。
- `step4_ml/step4_ml_prediction.py` 当前明确标注了 conventional MRI comparator、SAA kinetic 参数与 phenoconversion 事件分析在现有仓库状态下暂不可运行，避免把缺失模块误当成阴性结果；这部分仍属于 Step 4 的后续扩展，而不是独立项目。
- `step3c_lme_multiscale.py` 现已支持 `FullTimeline` 与 `2Year` 双时间窗输出，图标题、xtick、文件命名、阻塞预览和晚期时间点可视化阈值统一受 `config.py` 监管。
- `step3c_lme_multiscale.py` 当前每个量表目录可同时保留 `FullTimeline` / `2Year` 的 Figure 1、Figure 2、统计摘要与 OLS 保底报告，不再互相覆盖。
- `step3e_lme_nonmotor_extended.py` 现已支持 `FullTimeline` 与 `2Year` 双时间窗输出，图标题、xtick、文件命名和晚期时间点可视化阈值统一受 `config.py` 监管。
- `step3f_saa_subgroup_analysis.py` 的分析 2（LME）现已支持 `FullTimeline` 与 `2Year` 双时间窗输出；分析 1 仍保持 BL 基线 ANCOVA。
- `step3f_saa_subgroup_analysis.py` 已增加 `UPDRS3` 别名映射，能够兼容当前 CSV 中的 `UPDRSIII/UPDRSIII.1`。
- `step4_ml/step4_ml_prediction.py` 已增加 `UPDRS3` 别名映射，能够兼容当前 CSV 中的 `UPDRSIII/UPDRSIII.1`。
- `config.py` 已新增时间点过滤/映射/刻度辅助函数，Step 3/4 相关脚本正统一切换为受 config 控制。
- `config.py` 当前统一采用阻塞式显示（`plt.ioff()`），窗口默认收敛为较小预览尺寸。

## 近期状态更新（2026-04-29）

- 运行环境强调：Step4 实际执行统一使用 `conda activate mind`。
- **方案一已升级为 Aim 3 主框架**（`step4_ml/plan1_burden_resilience/step4_plan1_burden_resilience.py`）：
  - 五大模块：MIND burden score → stage expression → clinical resilience → longitudinal LME → AHBA/PLS 机制注释
  - 共享模块：`step4_ml/step4_ml_shared.py`（新增 `CLINICAL_COVARS`、`encode_binary_columns`）
  - 输出目录：`./MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/`
  - AHBA 阶段使用 `abagen` + Desikan-Killiany atlas + PLS + 半球保持置换 spatial null
  - 产出物：Figures A-E + Supplementary 1-5、PLS gene loadings、pathway/cell-type enrichment
  - **新增功能**（2026-04-29 补齐）：
    - Bootstrap 95% CI for burden score
    - Studentized residuals（替代 raw residuals）+ Spearman 单调性检验
    - Resilience/longitudinal 模型协变量升级为 CLINICAL_COVARS（Age/Sex/Education/LEDD/NHY）
    - Four-quadrant scatter plot（High/Low Burden × High/Low Resilience）
    - Forest plot（stage expression odds ratios）
    - GO-BP standalone dot plot（pathway enrichment）
    - PD/SAA- exploratory analysis（section 4.5，Kruskal-Wallis 检验）
- 方案二（incremental prediction）和方案三（topography）仍保留，但非当前主方向。

## 背景
用户按照论文分析流程将所有脚本组织为 Step1-4，Step2 内按分析层级用字母区分，辅助工具文件加 utils_ 前缀。

## 完整重命名映射

### Step 1 — 平均空间分布脑图
| 原文件名 | 新文件名 |
|---|---|
| baseline_group_mean_average_surface_viz.py | step1_mean_surface_maps.py |

### Step 2 — 组间统计差异（Nodal / Edge-wise）
| 原文件名 | 新文件名 | 说明 |
|---|---|---|
| baseline_professional_viz.py | step2a_global_mind_comparison.py | 全局对比：雷达图+箱线+脑表面T图+连接矩阵 |
| MIND_Network_Visualizer.py | step2b_7network_radar_boxplot.py | 7网络雷达图+并排箱线 |
| mind_inferential_analysis.py | step2b_network_ancova_7nets.py | 7网络列 ANCOVA 推断分析 |
| plot_mind_network.py | step2b_connectome_viz.py | nilearn 脑连接体可视化 |
| nodal_wise_ancova_stats.py | step2c_nodal_strength_ancova.py | 节点强度 ANCOVA（含 T-heatmap + 前10节点） |
| nodal_wise_ancova_stats_ver2.0.py | step2c_nodal_strength_ancova_surface.py | 节点强度 ANCOVA + 3D 脑表面渲染 |
| mind_nodal_and_edgewise_stats.py | step2d_edgewise_diff_heatmap.py | 边-wise 组间差异热力图 |
| mind_nodal_and_edgewise_stats_advanced.py | step2d_edgewise_hub_module.py | Hub 脆弱性 + 模块内/间连接分析 |
| mind_nodal_and_edgewise_stats_advanced-ver2.0.py | step2d_edgewise_violin_tmap.py | 全局小提琴图 + 边-wise T 矩阵 |
| mind_nodal_and_edgewise_stats_anova_advancedy_ver3.0.py | step2d_edgewise_anova_4group.py | 边 ANOVA（四组，FDR校正） |
| MIND_ANOVA_Connectome.py | step2_stats_connectome_anova_3group.py | 3组连接矩阵 ANOVA（纯统计） |
| MIND_ANOVA_Connectome-new.py | step2_stats_connectome_anova_4group.py | 4组连接矩阵 ANOVA（纯统计） |
| MIND_Network_Statistical_Test_P.py | step2_stats_network_ancova.py | 网络 ANCOVA 统计检验 |
| MIND_Network_Subgroup_Analysis.py | step2_stats_subgroup_aggregation.py | 子组数据聚合（无绘图） |

### Step 3 — LME 纵向预测
| 原文件名 | 新文件名 | 说明 |
|---|---|---|
| longitudinal_mind_prediction.py | step3a_lme_full_timepoints.py | 全时间点（BL~V12）LME |
| longitudinal_mind_prediction-v2-v4.py | step3b_lme_2year_updrs.py | 2年随访 UPDRS-III LME |
| longitudinal_mind_prediction-v2-v4-muli.py | step3c_lme_multiscale.py | 多量表 LME（现支持 FullTimeline + 2Year） |
| MIND_Scientific_Analysis.py | step3d_baseline_regression.py | 基线 MIND 回归预测（Aim1-3） |

### Step 4 — ML 预测模型
暂无现有文件，留空备用。

### 工具文件（utils_ 前缀）
| 原文件名 | 新文件名 |
|---|---|
| MINDshow.py | utils_mindshow.py |

### 核心计算文件（保持不变）
MIND.py、MIND_helpers.py、get_vertex_df.py、register_and_vol2surf.py、
batch_run_mind.py、getAllMindNet.py、analysis_data.py、MIND_Clinical_Master_Builder.py、
config.py

## 执行方式
- 全部用 `mv`（这些文件均为 git 未追踪状态，无需 git mv）
- 重命名后验证：`ls step*.py utils*.py | sort` 确认无遗漏
- 无需修改文件内部代码（文件名不被任何脚本相互引用）

## 验证
```bash
ls step1*.py step2*.py step3*.py utils*.py | sort
```
预期共输出 20 个新文件名。


合并记录（2026-03-27 执行）：

## 合并映射表

| 合并后文件 | 合并源文件（已删除） | 输出目录 |
|---|---|---|
| `step2c_nodal_strength_ancova.py` | `step2c_nodal_strength_ancova_surface.py` | `./nodal_statistical_results/` |
| `step2d_edgewise_analysis.py` | `step2d_edgewise_diff_heatmap.py`<br>`step2d_edgewise_violin_tmap.py`<br>`step2d_edgewise_anova_4group.py`<br>`step2d_edgewise_hub_module.py` | `./edgewise_results/` |
| `step2_stats_connectome_anova.py` | `step2_stats_connectome_anova_3group.py`<br>`step2_stats_connectome_anova_4group.py` | `./analysis_results_3group/`<br>`./analysis_results_4group/` |
| `step3_lme_updrs.py` | `step3a_lme_full_timepoints.py`<br>`step3b_lme_2year_updrs.py` | `./lme_updrs_results/` |

## 合并后现有脚本列表

Step 1 — 平均空间分布脑图
  step1_mean_surface_maps.py

Step 2 — 组间统计差异
  step2a_global_mind_comparison.py     ← 全局对比（雷达+箱线+T图+连接矩阵）
  step2b_7network_radar_boxplot.py     ← 7网络雷达图+并排箱线
  step2b_connectome_viz.py             ← nilearn 脑连接体图
  step2b_network_ancova_7nets.py       ← 7网络列 ANCOVA 推断
  step2c_nodal_strength_ancova.py      ← [合并] 节点强度 ANCOVA + 3D脑图（原2个→1个）
  step2d_edgewise_analysis.py          ← [合并] 差异热力图+小提琴+T矩阵+Hub+模块（原4个→1个）
  step2_stats_connectome_anova.py      ← [合并] 3组+4组 Connectome ANOVA（原2个→1个）
  step2_stats_network_ancova.py        ← 网络 ANCOVA 检验（独立）
  step2_stats_subgroup_aggregation.py  ← 子组数据聚合（独立）

Step 3 — LME 纵向预测
  step3_lme_updrs.py                   ← [合并] 全时间点+2年 UPDRS-III（原2个→1个）
  step3c_lme_multiscale.py             ← 多量表 LME（独立，现支持 FullTimeline + 2Year）
  step3d_baseline_regression.py        ← 基线回归预测（独立）

Step 4 — ML 预测（承接前序分析）

工具
  utils_mindshow.py

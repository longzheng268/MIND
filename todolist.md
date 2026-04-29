# MIND 分析待办清单

> 更新时间：2026-04-18

---

## Step 4 — Aim 3 预测阶段（三方案并行，承接前序分析）

- [x] 目录规整：`step4_ml/plan1_burden_resilience/`、`step4_ml/plan2_incremental_prediction/`、`step4_ml/plan3_topography_mechanism/`（2026-04-18）
- [x] 样式统一规则：Step4 保持 `config.py` 为绝对参考，不允许局部覆写（2026-04-18）

### 方案二（当前主运行）

- [x] `step4_ml/step4_ml_prediction.py`：按 Aim 3 递进模型框架重构主线（clinical / SAA / MIND，2026-04-12）
- [x] `step4_ml/step4_ml_prediction.py`：显式训练集 / 测试集 7:3 划分与 data 目录持久化（subject-level 分层均衡，2026-04-18）
- [x] `step4_ml/step4_ml_prediction.py`：补充 test-set ROC/AUC 输出（2026-04-18）
- [x] `MIND_Research_Results/ML_Prediction/Aim3_Incremental/Aim3_ROC_Overview.csv`：汇总全部终点 ROC 结果（2026-04-18）
- [ ] `step4_ml/step4_ml_prediction.py`：补充 conventional MRI comparator（若数据就绪）
- [ ] `step4_ml/step4_ml_prediction.py`：补充 SAA kinetic 参数模块（若数据就绪）
- [ ] `step4_ml/step4_ml_prediction.py`：补充 phenoconversion / Cox 生存分析（若事件标签就绪）
- [ ] `step4_ml/step4_ml_prediction.py`：加入训练折内非线性特征工程（交互项/降维）并评估对增量价值影响
- [ ] `step4_ml/step4_ml_prediction.py`：加入 XGBoost 挑战模型（Huber/SquaredLog 目标）

### 方案一（SAA+ burden-resilience + AHBA 机制注释，Aim 3 主框架）

- [x] burden score：HC 参照 z-score 加权 + PCA-PC1 降级，已输出（2026-04-18）
- [x] burden score bootstrap 95% CI（2026-04-29）
- [x] SAA+ 阶段表达：prodromal/SAA+ vs PD/SAA+ 逻辑回归，已输出（2026-04-18）
- [x] Stage expression forest plot（odds ratios + 95% CI）（2026-04-29）
- [x] motor/cognitive resilience：studentized residuals + Spearman 单调性检验（2026-04-29）
- [x] resilience 模型协变量升级为 CLINICAL_COVARS（Age/Sex/Education/LEDD/NHY）（2026-04-29）
- [x] 纵向验证：MixedLM `Time × Burden + Time × Resilience` + CLINICAL_COVARS（2026-04-29）
- [x] 高风险象限分型（High/Low Burden × High/Low Resilience）（2026-04-29）
- [x] Four-quadrant scatter plot 可视化（2026-04-29）
- [x] PD/SAA- exploratory analysis（section 4.5，Kruskal-Wallis）（2026-04-29）
- [x] AHBA/PLS 机制注释（空间 null、通路富集、细胞类型注释）（2026-04-29）
- [x] GO-BP standalone dot plot（2026-04-29）
- [x] Figures A-E + Supplementary 1-5 代码框架已完成（2026-04-29）
- [ ] 验证 step4_plan1_burden_resilience.py 在 mind 环境完整运行
- [ ] burden 非线性变换对比（Quantile / Yeo-Johnson / log1p）与稳定性评估

### 方案三（SAA+ topography-mechanism）

- [x] SAA+ 个体 MIND 异常拓扑表型构建（global + network topography，2026-04-18）
- [x] topography contrast 已成功输出 16 行结果（2026-04-18）
- [ ] 域特异纵向验证（motor / cognitive / non-motor）
- [ ] hub vulnerability 与 disease epicenter 分析
- [ ] imaging-transcriptomics 与 cell-type enrichment 注释（AHBA 代码路径已接入，待外部数据抓取/缓存完成全量运行）
- [ ] AHBA 缓存修复并重跑（当前错误：`unknown archive file format`，见 `AHBA_Fallback_Notes.txt`）
- [ ] 拓扑特征压缩与相关性升级（tanh + Spearman）

### Step4 统一入口（新增）

- [x] 新增 `step4_ml/step4_entry.py` 统一入口（`--plan {1,2,3,all}`，2026-04-19）
- [x] 支持 `--mode {quick,full}`、`--skip-ahba`、`--cache-dir`、`--report-only`（2026-04-19）
- [x] 输出统一运行汇总（`Step4_Entry_Overview.csv`）与运行日志（`Step4_Entry_RunLog.txt`）（2026-04-19）
- [x] 支持 quick 模式自定义 Plan2 时间窗（`--quick-windows`，2026-04-19）
- [x] 支持中文自动汇总报告输出（`--summary` -> `Step4_Entry_Summary_CN.md`，2026-04-19）
- [x] 中文汇总报告支持与上次运行差异对比（Delta：状态/产物标记/耗时，2026-04-19）

---

## 统计补充

- [ ] `step2c_nodal_strength_ancova.py`：运行并验证输出（含 3D 脑表面图）
- [ ] `step2d_edgewise_analysis.py`：四组 ANCOVA 耗时极长，考虑并行化（joblib）
- [ ] NBS（Network-Based Statistics）替代简单 T 检验，用于 edgewise 多重比较校正
- [ ] 多量表 FDR 校正（BH 法）：为 `step3c_lme_multiscale.py` 增加跨量表校正
- [x] `step3f_saa_subgroup_analysis.py`：SAA+ vs SAA- BL MIND 组间差异 + SAA 对临床变化速率的调节（2026-03-28）

## 可视化补充

- [ ] `step1_mean_surface_maps.py`：确认 nilearn FSAverage 路径在当前环境下可用
- [ ] `step2b_7network_radar_boxplot.py`：雷达图标签检查（YEO7 缩写是否完整）
- [ ] `step2b_connectome_viz.py`：nilearn connectome 图颜色映射与 config.py 对齐验证
- [x] `step3d_baseline_regression.py`：恢复 `V10` / `V12` 成对 Figure 1 / Figure 2 输出，并统一至 config 驱动样式（2026-04-09）
- [x] `step3d_baseline_regression.py`：恢复保存后统一阻塞预览弹窗（2026-04-09）
- [x] `step3c_lme_multiscale.py`：扩展为 `FullTimeline` / `2Year` 双时间窗 LME 输出（2026-04-12）
- [x] `step3e_lme_nonmotor_extended.py`：扩展为 `FullTimeline` / `2Year` 双时间窗 LME 输出（2026-04-09）
- [x] `step3f_saa_subgroup_analysis.py`：分析 2 扩展为 `FullTimeline` / `2Year` 双时间窗 LME 输出（2026-04-09）

## 数据文件

- [ ] 确认 `./data/MIND-Networks_newgroup/` 下四个子目录均已包含全部受试者矩阵
- [ ] 验证 `scale/MIND_Longitudinal_Clean_Data.csv` 中 `MIND_Sig_Index` 字段是否与
      `step3_lme_updrs.py` 及 `step3c_lme_multiscale.py` 引用路径一致
- [x] `step3c_lme_multiscale.py` 路径已从 `./量表/` 更新为 `./scale/`（2026-03-27）
- [x] `step3d_baseline_regression.py` 已完全改为读取 `./scale/MIND_baseline_with_followup_V04_V12.csv`，不再依赖旧宽表（2026-04-09）

---

## 已完成（供记录）

- [x] 统一 config.py 控制全部可视化常量（颜色、图幅、DPI 等）
- [x] 所有脚本按 Step1-4 规范重命名
- [x] 合并重复功能脚本（step2c / step2d / step2_stats / step3_lme_updrs）
- [x] 删除被合并的旧文件

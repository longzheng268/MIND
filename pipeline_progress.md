# MIND Pipeline — Session Progress Notes

> 最近更新：2026-04-18
> 用途：跨会话工作记忆，记录当前代码状态、已完成工作和待办事项

---

## 项目环境

- **Python 环境**：`conda activate mind`（`/home/sad/miniconda3/envs/mind`），所有执行须在 `mind` 环境中运行
- **工作目录**：`/mnt/d/Code_workspace/MIND`
- **Git 分支**：`data-analyze`（主分支为 `master`，PR 目标为 `master`）
- **核心控制文件**：`config.py`——所有可视化常量、LME 参数、Step 3/4 时间窗统一在此，脚本须 `from config import *; apply_style()`

---

## 近期已完成修复（2026-04-09）

- `step2a_global_mind_comparison.py`：修复 `GROUPS` 未定义，统一改为 `GROUP_ORDER`
- `step2a_global_mind_comparison.py`：恢复阻塞式显示，末尾使用 `plt.show(block=True)`
- `config.py`：全局从 `plt.ion()` 改为 `plt.ioff()`，统一为阻塞显示模式
- `config.py`：屏幕预览窗口默认收敛为小窗口（约 `800×600`），同时保持 `savefig.dpi=300`
- `step2d_edgewise_analysis.py`：修复数据文件路径问题，已可在 `mind` 环境下正常运行
- `step2b_network_ancova_7nets.py`：已成功跑通 7-network ANCOVA，得到 FDR 校正结果
- `step2b_connectome_viz.py`：已标记为 legacy visualization script，暂不作为主分析链路使用
- `step3_lme_updrs.py`：兼容 `UPDRS3/UPDRSIII/UPDRSIII.1` 列名，已在 `mind` 环境跑通全时间点与 2 年模型
- `step3c_lme_multiscale.py`：现已支持 `FullTimeline`（`BL/V04/V06/V08/V10/V12`）与 `2Year`（`BL/V04/V06`）双时间窗输出，图标题、xtick、保存命名、阻塞预览和晚期时间点可视化阈值统一受 `config.py` 控制
- `step3c_lme_multiscale.py`：每个量表目录现可同时保留 `FullTimeline` 与 `2Year` 的 Figure 1 / Figure 2 / Statistical Summary / OLS Backup 输出，不再互相覆盖
- `step3d_baseline_regression.py`：由旧宽表假设改为从当前长表动态整理 BL/V04/V06/V10/V12 后再回归，已在 `mind` 环境跑通
- `step3d_baseline_regression.py`：当前主输出聚焦 `V10` 与 `V12` 两组图片，并恢复每组“图一（组间箱线+散点）+ 图二（MIND 回归图）”的成对结果
- `step3d_baseline_regression.py`：Aim 3 现已加入退化样本保护；当非 HC 子样本过少、`SAA_Status` 无变异或残差自由度不足时，自动跳过增量价值分析，避免出现 `R²=1.0000` 这类假完美结果
- `step3d_baseline_regression.py`：绘图风格已向 Step2/Step3 统一收敛，图幅、字体、grid、stripplot 样式、标题编号均受 `config.py` 监管
- `step3d_baseline_regression.py`：保存 PNG 后支持统一 `plt.show(block=True)` 预览，不再出现“只保存不弹窗”的行为
- `step3e_lme_nonmotor_extended.py`：现已支持 `FullTimeline`（`BL/V04/V06/V08/V10/V12`）与 `2Year`（`BL/V04/V06`）双时间窗输出，图标题、xtick、保存命名和晚期时间点可视化阈值统一受 `config.py` 控制
- `step3f_saa_subgroup_analysis.py`：分析 2（SAA 状态调节 LME）现已支持 `FullTimeline` 与 `2Year` 双时间窗输出；分析 1 仍保持 BL 基线 ANCOVA，不扩展到随访
- `config.py`：Step 3/4 时间控制已进一步收敛到当前真实数据时间窗，full timeline 统一为 `BL/V04/V06/V08/V10/V12`，图标题与 xtick 由 config 统一生成

---

## Aim 3 推荐主方案（知识库更新，2026-04-12）

- **建模对象**：预测模型不纳入 HC；主分析纳入 `prodromal/SAA-`、`prodromal/SAA+`、`PD/SAA+`，`PD/SAA-` 作为探索性 discordant 组补充分析。
- **三层样本策略**：
  - 全连续谱主模型：prodromal + PD
  - SAA 阳性限定模型：`prodromal/SAA+` + `PD/SAA+`
  - prodromal 子集模型：评估前驱期恶化与 phenoconversion 风险
- **结局设计**：以连续结局为主、二分类结局为辅、时间事件结局为扩展。
  - 连续主结局：24 个月运动进展斜率（优先 `UPDRS3`/`UPDRS total` 年化变化或 LME 经验贝叶斯 slope），以及 24–36 个月认知进展斜率（优先 `MoCA` 或认知复合分数）
  - 二分类次级结局：快运动进展、快认知下降、快非运动恶化
  - 事件结局：prodromal → PD phenoconversion 时间；事件数不足时降级为固定时间窗二分类
- **输入模块分层**：
  - 固定协变量：年龄、性别、教育、病程、TIV、中心/扫描仪、药物状态或 `LEDD`、疾病阶段、必要时基线至末次随访间隔
  - baseline clinical：`UPDRS3/total`、`MoCA`/认知复合分数、非运动复合分数、RBD、`SCOPA-AUT`、`ESS`、情绪量表等
  - SAA 模块：主分析优先 `SAA_Status` 二元状态；kinetic 参数仅作扩展
  - MIND 模块：压缩为 10–15 个稳定 summary features，至少包含 global mean MIND，可加入网络级平均值、训练折内 nodal PCA 主成分、预定义高风险 summary score
  - traditional MRI comparator：平均皮层厚度、总灰质体积、少量预定义 ROI 厚度/体积
- **固定模型层级（每个主要结局都比较）**：
  - Model A：baseline clinical only
  - Model B：baseline clinical + SAA
  - Model C：baseline clinical + MIND
  - Model D：baseline clinical + SAA + MIND（Aim 3 核心模型）
  - Model E：baseline clinical + conventional MRI
  - Model F：baseline clinical + SAA + conventional MRI + MIND
- **模型选择原则**：
  - 主模型：`Elastic Net`（连续结局用线性回归，二分类结局用 logistic regression）
  - 挑战模型：`XGBoost`，用于检验非线性/阈值效应/高阶交互
  - 事件结局主模型：`Cox-Elastic Net`；随机生存森林仅作探索性补充
- **连续结局推荐流程**：
  - 第一步：先在纵向数据中建立不含影像预测因子的 LME，提取个体经验贝叶斯 slope
  - 第二步：以 slope 为目标做 `Elastic Net` / `XGBoost`，并按 Model A–F 递进比较
- **防止信息泄漏**：缺失值插补、标准化、PCA、site harmonization、特征选择、调参必须全部限制在训练折内完成。
- **验证策略**：
  - 优先：预留 20%–25% 独立测试集；若可能，优先时间切分或留中心做准外部验证
  - 训练阶段：nested CV（外层 5-fold，内层 5-fold），必要时 repeated nested CV / bootstrap CI
- **性能与增量价值判定**：
  - 连续结局：`R²`、`RMSE`、`MAE`、`ΔR²`、`ΔRMSE`
  - 二分类：`AUROC`、`AUPRC`、`Brier score`、校准截距/斜率、决策曲线
  - 时间事件：`C-index`、time-dependent AUC、integrated Brier score
  - 核心判断：比较 Model B→D、或不含 MIND → 含 MIND 的模型，在区分度、误差、校准和净获益上是否同步改善
- **解释性输出**：
  - `Elastic Net`：标准化回归系数 + 被保留变量
  - `XGBoost`：`SHAP summary plot` + 关键特征排序
  - 若 MIND 稳定入模，应进一步展示最关键的网络级/节点级 MIND 指标及其生物学解释
- **敏感性分析**：
  - 全连续谱 / SAA 阳性限定 / prodromal 子集分别重复
  - 更换运动或认知结局定义
  - 调整 MIND feature 压缩策略
  - 剔除 `PD/SAA-` 等 discordant 个体
  - 在可行时加入 conventional MRI、SAA kinetic 等扩展模块
- **当前推荐主线**：在 prodromal + PD 个体中，以 24 个月运动斜率和 24–36 个月认知斜率为主要结局，以 `Elastic Net` 为主模型、`XGBoost` 为挑战模型，使用 Model A–F、nested CV、独立测试/准外部验证、校准分析与决策曲线，系统评估 MIND 在 baseline clinical 与 SAA 之上的增量预测价值；同时在 SAA 阳性限定样本中重复，作为最直接回应课题核心问题的关键补充分析。

---

## 最新 Step 3 运行摘要（2026-04-09）

- `step3_lme_updrs.py`
  - 模型 A、模型 B 均成功运行
  - `Time:MIND_BL` 当前未见显著
  - 组别时间交互中，`prodromal_SAA+` 与 `PD_SAA+` 存在显著项
- `step3c_lme_multiscale.py`
  - 6 个量表现已同时输出 `FullTimeline` 与 `2Year` 两套结果
  - full timeline 可视化会按 `STEP3_FULL_MIN_PLOT_N` 自动过滤过稀的晚期随访点，避免误导性折线
- `step3d_baseline_regression.py`
  - 当前主输出聚焦 `V10` 与 `V12` 两组图片
  - 每组恢复两张图：`Aim2_Group_Delta_Boxplot_{V10/V12}.png` + `Aim2_MIND_Prediction_{V10/V12}.png`
  - 运行时会先保存图，再统一阻塞预览
  - 本次运行样本数：V10 `n=144`，V12 `n=81`
  - Aim 3：V10 正常输出；V12 因非 HC 子样本仅 `n=3` 被保护性跳过
- `step3f_saa_subgroup_analysis.py`
  - 基线 SAA+ vs SAA-：Global/Visual/Dorsal/Ventral/Limbic/Frontoparietal/Default 显著，Somatomotor 不显著
  - SAA 亚组 LME：MoCA 与 UPDRS3 的 `Time:MIND_BL` 和 `Time:SAA_Status` 交互当前均未达显著
- `step4_ml/step4_ml_prediction.py`
  - 当前已作为整个项目的预测阶段主脚本稳定运行（Step 1-3 提供分析基础，Step 4 承接做 Aim 3 增量价值评估）
  - 采用 Parkinson-spectrum 非 HC 样本、固定时间窗 `UPDRS3`/`MoCA` delta、Model A/B/C/D、7:3 subject-level 分层均衡拆分持久化、train-only CV 与 test-set 终评
  - 已新增 test-set ROC/AUC 输出（按 train-only 阈值定义 fast-progressor）
  - 已生成跨终点 ROC 汇总表：`MIND_Research_Results/ML_Prediction/Aim3_Incremental/Aim3_ROC_Overview.csv`
  - Step4 目录已规整为三方案并行：`plan1_burden_resilience`、`plan2_incremental_prediction`、`plan3_topography_mechanism`
  - 方案三已接入 AHBA 机制叠加代码路径（`abagen`），当前运行可能受外部数据抓取/缓存时长影响
  - 方案三核心拓扑输出已生成：`Plan3_Topography_Feature_Contrasts.csv`、`Plan3_Topography_Overview.csv`、`Plan3_Topography_Subject_Scores.csv`
  - 图形样式管理规则保持不变：`config.py` 为绝对参考，Step4 可视化必须统一 `apply_style()`，不得局部覆写

## 最新 Step 4 运行摘要（2026-04-18，mind 环境）

- 方案一（`step4_ml/plan1_burden_resilience/step4_plan1_burden_resilience.py`）运行成功，结果已落盘至
  `./MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/`。
  - `Plan1_Burden_Resilience_Summary.csv`：
    - `UPDRS3`: `N=557`, `Model_R2=0.0202`
    - `MoCA`: `N=566`, `Model_R2=0.0889`

- 方案二（`step4_ml/step4_ml_prediction.py` / plan2）延续使用
  `./MIND_Research_Results/ML_Prediction/Aim3_Incremental/`。
  - `Aim3_Incremental_Overview.csv`：`UPDRS3 V06` 最优模型为 `Model_B_Clinical_SAA`，`MoCA V06` 最优模型为 `Model_D_Clinical_SAA_MIND`。

- 方案三（`step4_ml/plan3_topography_mechanism/step4_plan3_topography_mechanism.py`）
  - Topography 阶段已成功完成并输出 16 行对比。
  - AHBA 阶段失败：`AHBA_Fallback_Notes.txt` 记录多次 donor 重试仍报
    `unknown archive file format`（缓存 zip 异常）。
  - 当前建议：先报告拓扑结果；机制层结论待 AHBA 缓存修复后补充。

## Step4 Aim 3 框架更新（2026-04-29）

- **核心变化**：方案一（Plan1）已从简单的 burden-resilience 概念验证升级为完整的 Aim 3 实现框架，包含五大模块：
  1. **MIND burden score**（4.4.1）：HC 参照 z-score 加权合成或 PCA-PC1 降级方案；权重来自 Step2 已有效应量结果；含 bootstrap 95% CI
  2. **Stage expression**（4.4.2）：prodromal/SAA+ vs PD/SAA+ 逻辑回归，验证 burden 与疾病阶段的关系；含 forest plot 可视化
  3. **Clinical resilience**（4.4.3）：临床评分 ~ burden + CLINICAL_COVARS（Age/Sex/Education/LEDD/NHY）回归；使用 studentized residuals；含 Spearman 单调性检验
  4. **Longitudinal validation**（4.4.4）：MixedLM `Time × Burden + Time × Resilience` 交互，协变量包含完整 CLINICAL_COVARS
  5. **Imaging-transcriptomics**（4.4.5）：AHBA + Desikan-Killiany 对齐 → PLS 回归 → 半球保持置换空间 null → 通路/细胞类型富集；含 standalone GO-BP dot plot
- **新增产出物**：
  - Four-quadrant scatter plot（High/Low Burden × High/Low Resilience）
  - Forest plot（stage expression odds ratios）
  - GO-BP standalone dot plot（pathway enrichment）
  - PD/SAA- exploratory analysis（section 4.5，含 Kruskal-Wallis 检验）
  - Bootstrap 95% CI for burden score
  - Studentized residuals 替代 raw residuals
- **产出物总览**：Figures A-E + Supplementary 1-5 + GO-BP dot plot + four-quadrant scatter + forest plot
- **脚本**：`step4_ml/plan1_burden_resilience/step4_plan1_burden_resilience.py`
- **共享模块**：`step4_ml/step4_ml_shared.py`（CLINICAL_COVARS、DEMOGRAPHIC_COLS、SAA_BURDEN_COLS、alias_scale_column、coerce_numeric、encode_binary_columns 等）
- **方案二**（incremental prediction）仍保留但非当前主方向；方案三（topography）为 Plan1 的补充视角

## Step4 优化设计更新（2026-04-19）

- 新增优化文档：`step4_ml/STEP4_Optimization_Activation_DimRed.md`
- 设计更新要点：
  - Plan1：非线性变换（Quantile / Yeo-Johnson / log1p）+ 拓扑信息保留
  - Plan2：降维 + 非线性交互特征 + XGBoost 挑战模型
  - Plan3：tanh 压缩 + Spearman 空间相关 + AHBA 本地化/替代策略
- Step4 统一入口（文档设计阶段）：
  - 计划新增 `step4_ml/step4_entry.py`
  - 统一参数：`--plan`、`--mode`、`--skip-ahba`、`--report-only`

---

## 代码架构现状

### 脚本命名规范

| 前缀 | 功能层级 |
|---|---|
| `step1_` | 平均空间分布脑图 |
| `step2a/b/c/d_` | 组间统计差异（global → 7网络 → 节点 → 连边） |
| `step2_stats_` | 纯统计文件（无可视化） |
| `step3_` / `step3c_` / `step3d_` / `step3e_` / `step3f_` | LME 纵向预测 / 多量表 / 基线回归 / 非运动扩展量表 / SAA 亚组敏感性 |
| `utils_` | 辅助工具 |
| `config.py` | 全局参数中心 |

### 合并历史（已完成）

| 合并后 | 原文件（已删） |
|---|---|
| `step2c_nodal_strength_ancova.py` | `step2c_nodal_strength_ancova_surface.py` |
| `step2d_edgewise_analysis.py` | 4 个 `step2d_*` 文件 |
| `step2_stats_connectome_anova.py` | `step2_stats_connectome_anova_3group.py` + `_4group.py` |
| `step3_lme_updrs.py` | `step3a_lme_full_timepoints.py` + `step3b_lme_2year_updrs.py` |

---

## LME 分析设计（research_design_lme_mind.md）

### 双模型结构（step3_lme_updrs.py / step3c / step3e 均已实现）

```python
# 模型1：四组轨迹差异（参照组 HC）
formula1 = "Y ~ Time * C(Group_MIND, Treatment('HC')) + Y_BL + Age_at_Visit + C(Sex) + Education"

# 模型2：控制分组后，MIND 对变化速率的独立预测（核心创新）
formula2 = ("Y ~ Time * C(Group_MIND, Treatment('HC'))"
            " + Time * MIND_BL + Y_BL + Age_at_Visit + C(Sex) + Education")
```

### 三级降级策略（通用函数 `_fit_lme()`）

```
① re_formula=LME_RE_FORMULA（随机截距+斜率，来自 config.py）
② re_formula=None（仅随机截距）
③ 抛出异常 → 外层 except → OLS 保底
```

### config.py 关键 LME 参数

```python
LME_METHODS    = ['lbfgs', 'powell', 'nm', 'bfgs']
LME_RE_FORMULA = "~Time"   # 等价 R 的 (1 + Time | Subject_ID)
```

---

## 数据文件路径

| 变量 | 路径 |
|---|---|
| 基线/随访分析表 | `./scale/MIND_baseline_with_followup_V04_V12.csv` |
| 纵向长格式（填补后） | `./scale/MIND_Longitudinal_Clean_Data_filled.csv` |
| MIND 矩阵 | `./data/MIND-Networks_newgroup/{Group}/{ID}_MIND.csv` |
| step3d 当前输入 | `./scale/MIND_baseline_with_followup_V04_V12.csv` |

---

## 未完成 / 待确认

- [ ] 多量表 FDR 校正（BH 法）：step3c 当前每个量表独立检验，跨量表 FDR 尚未实现
- [ ] 事后组间斜率两两比较（emtrends Python 等价）：仅报告整体 Time:MIND_BL 系数，未做组间 post-hoc
- [ ] Step 4 ML 预测模型：继续完善现有脚本与结果解释

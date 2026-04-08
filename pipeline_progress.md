# MIND Pipeline — Session Progress Notes

> 最近更新：2026-04-09
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
- `step3c_lme_2year_multiscale.py`：新增量表别名映射，已兼容 `UPDRSIII` 并在 `mind` 环境跑通
- `step3d_baseline_regression.py`：由旧宽表假设改为从当前长表动态整理 BL/V04/V06/V10/V12 后再回归，已在 `mind` 环境跑通
- `step3d_baseline_regression.py`：当前主输出聚焦 `V10` 与 `V12` 两组图片，并恢复每组“图一（组间箱线+散点）+ 图二（MIND 回归图）”的成对结果
- `step3d_baseline_regression.py`：Aim 3 现已加入退化样本保护；当非 HC 子样本过少、`SAA_Status` 无变异或残差自由度不足时，自动跳过增量价值分析，避免出现 `R²=1.0000` 这类假完美结果
- `step3d_baseline_regression.py`：绘图风格已向 Step2/Step3 统一收敛，图幅、字体、grid、stripplot 样式、标题编号均受 `config.py` 监管
- `step3d_baseline_regression.py`：保存 PNG 后支持统一 `plt.show(block=True)` 预览，不再出现“只保存不弹窗”的行为
- `step3e_lme_nonmotor_extended.py`：现已支持 `FullTimeline`（`BL/V04/V06/V08/V10/V12`）与 `2Year`（`BL/V04/V06`）双时间窗输出，图标题、xtick、保存命名和晚期时间点可视化阈值统一受 `config.py` 控制
- `step3f_saa_subgroup_analysis.py`：分析 2（SAA 状态调节 LME）现已支持 `FullTimeline` 与 `2Year` 双时间窗输出；分析 1 仍保持 BL 基线 ANCOVA，不扩展到随访
- `config.py`：Step 3/4 时间控制已进一步收敛到当前真实数据时间窗，full timeline 统一为 `BL/V04/V06/V08/V10/V12`，图标题与 xtick 由 config 统一生成

---

## 最新 Step 3 运行摘要（2026-04-09）

- `step3_lme_updrs.py`
  - 模型 A、模型 B 均成功运行
  - `Time:MIND_BL` 当前未见显著
  - 组别时间交互中，`prodromal_SAA+` 与 `PD_SAA+` 存在显著项
- `step3c_lme_2year_multiscale.py`
  - 6 个量表均完成分析
  - `Time:MIND_BL`：UPDRS3 p=0.381，MoCA p=0.722，GDS15_all p=0.078，RBDSQ_all p=0.067，NP1APAT p=0.983，NP1FATG p=0.293
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
  - 回归任务：MoCA Δ 最佳为 ElasticNet（R²≈0.001），UPDRS3 Δ 最佳也为 ElasticNet（R²≈-0.011），当前预测性能有限
  - 分类任务：SAA+ vs SAA- 最佳为 SVC，AUC≈0.704，LogisticRegression 准确率≈0.705

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

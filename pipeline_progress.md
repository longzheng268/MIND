# MIND Pipeline — Session Progress Notes

> 最近更新：2026-03-28
> 用途：跨会话工作记忆，记录当前代码状态、已完成工作和待办事项

---

## 项目环境

- **Python 环境**：`conda activate mind`（`/home/sad/miniconda3/envs/mind`），所有执行须用 `conda run -n mind python3`
- **工作目录**：`/mnt/e/Code_workspace/MIND`
- **Git 分支**：`data-analyze`（主分支为 `master`，PR 目标为 `master`）
- **核心控制文件**：`config.py`——所有可视化常量、LME 参数统一在此，脚本须 `from config import *; apply_style()`

---

## 代码架构现状

### 脚本命名规范

| 前缀 | 功能层级 |
|---|---|
| `step1_` | 平均空间分布脑图 |
| `step2a/b/c/d_` | 组间统计差异（global → 7网络 → 节点 → 连边） |
| `step2_stats_` | 纯统计文件（无可视化） |
| `step3_` / `step3c_` / `step3d_` / `step3e_` | LME 纵向预测 / 多量表 / 基线回归 / 非运动扩展量表 |
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

### step3c 量表列表与当前结果（2026-03-27 跑通）

| 量表 | Time:MIND_BL β | p |
|---|---|---|
| UPDRS3 | −57.4 | 0.005 ✓ |
| MoCA   | +34.4 | <0.001 ✓ |
| GDS15_all | +19.0 | <0.001 ✓ |
| RBDSQ_all | −11.1 | 0.093 |
| NP1APAT | +7.4 | 0.014 ✓ |
| NP1FATG | −13.6 | <0.001 ✓ |

### step3e 扩展非运动量表（2026-03-28 跑通）

`step3e_lme_nonmotor_extended.py`：5 个新量表，含 `_safe_col()` 处理特殊字符（S-AI/T-AI 含 `-`）

| 量表 | Time:MIND_BL β | 95% CI | p | 备注 |
|---|---|---|---|---|
| ESS_all（嗜睡） | +5.4 | [−9.1, 19.9] | 0.464 | 不显著 |
| SCOPA_AUT_all（自主神经） | −5.7 | [−60.4, 49.0] | 0.839 | 不显著 |
| S-AI（状态焦虑） | +88.9 | [26.3, 151.5] | 0.005 ✓ | 显著 |
| T-AI（特质焦虑） | +90.4 | [32.9, 147.8] | 0.002 ✓ | 显著 |
| UPSIT_PRCNTGE（嗅觉） | — | — | — | LME 全部失败，OLS 保底（β=100.9, p=0.036） |

---

## UPDRS-III 逻辑修正说明

**问题**：旧版 step3_lme_updrs.py 公式缺少 `C(Group_MIND)`，导致 `Time:MIND_BL` 系数混淆疾病阶段效应。

**修正**：两个模型均加入 Group，Y 轴标注 `↑ = Worse Motor Function`，MIND 分组改用 `MIND_LEVEL_ORDER`。

---

## 数据文件路径

| 变量 | 路径 |
|---|---|
| 纵向长格式（全时间点） | `./MIND_Longitudinal_Clean_Data.csv` |
| 纵向长格式（填补后） | `./scale/MIND_Longitudinal_Clean_Data_filled.csv` |
| MIND 矩阵 | `./data/MIND-Networks_newgroup/{Group}/{ID}_MIND.csv` |
| step3d 宽格式 | `MIND_Final_Analysis_Table.csv`（**路径未确认**） |

---

## 未完成 / 待确认

- [ ] `step3d_baseline_regression.py`：读取宽格式文件 `MIND_Final_Analysis_Table.csv`，字段名（`BL_Age`、`V04_UPDRS3`等）与其他脚本不同，需确认文件路径并修复
- [ ] 多量表 FDR 校正（BH 法）：step3c 当前每个量表独立检验，跨量表 FDR 尚未实现
- [ ] 事后组间斜率两两比较（emtrends Python 等价）：仅报告整体 Time:MIND_BL 系数，未做组间 post-hoc
- [ ] Step 4 ML 预测模型：尚无脚本，需从头开发

---

## config.py 核心常量速查

```python
GROUP_ORDER      = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']
GROUP_COLORS     = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3']
GROUP_PALETTE    = dict(zip(GROUP_ORDER, GROUP_COLORS))
TIME_MAP_3PT     = {'BL': 0, 'V04': 1, 'V06': 2}
TIME_LABELS_3    = ['Baseline (BL)', 'Year 1 (V04)', 'Year 2 (V06)']
MIND_LEVEL_ORDER = ['High MIND (Mean+1SD)', 'Mid MIND (Mean)', 'Low MIND (Mean-1SD)']
DPI              = 300
LME_METHODS      = ['lbfgs', 'powell', 'nm', 'bfgs']
LME_RE_FORMULA   = "~Time"
```
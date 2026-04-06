# MIND Pipeline — Session Progress Notes

> 最近更新：2026-04-07
> 用途：跨会话工作记忆，记录当前代码状态、已完成工作和待办事项

---

## 项目环境

- **Python 环境**：`conda activate mind`（`/home/sad/miniconda3/envs/mind`），所有执行须在 `mind` 环境中运行
- **工作目录**：`/mnt/d/Code_workspace/MIND`
- **Git 分支**：`data-analyze`（主分支为 `master`，PR 目标为 `master`）
- **核心控制文件**：`config.py`——所有可视化常量、LME 参数统一在此，脚本须 `from config import *; apply_style()`

---

## 近期已完成修复（2026-04-07）

- `step2a_global_mind_comparison.py`：修复 `GROUPS` 未定义，统一改为 `GROUP_ORDER`
- `step2a_global_mind_comparison.py`：恢复阻塞式显示，末尾使用 `plt.show(block=True)`
- `config.py`：全局从 `plt.ion()` 改为 `plt.ioff()`，统一为阻塞显示模式
- `config.py`：屏幕预览窗口默认收敛为小窗口（约 `800×600`），同时保持 `savefig.dpi=300`
- `step2d_edgewise_analysis.py`：修复数据文件路径问题，已可在 `mind` 环境下正常运行
- `step2b_network_ancova_7nets.py`：已成功跑通 7-network ANCOVA，得到 FDR 校正结果
- `step2b_connectome_viz.py`：已标记为 legacy visualization script，暂不作为主分析链路使用

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
| step3d 宽格式 | `MIND_Final_Analysis_Table.csv`（**路径未确认**） |

---

## 未完成 / 待确认

- [ ] `step3d_baseline_regression.py`：读取宽格式文件 `MIND_Final_Analysis_Table.csv`，字段名（`BL_Age`、`V04_UPDRS3`等）与其他脚本不同，需确认文件路径并修复
- [ ] 多量表 FDR 校正（BH 法）：step3c 当前每个量表独立检验，跨量表 FDR 尚未实现
- [ ] 事后组间斜率两两比较（emtrends Python 等价）：仅报告整体 Time:MIND_BL 系数，未做组间 post-hoc
- [ ] Step 4 ML 预测模型：继续完善现有脚本与结果解释

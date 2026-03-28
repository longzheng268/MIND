# MIND 网络预测临床恶化 — LME 研究方案

> 文件生成日期：2026-03-23
> 方法学来源：纵向症状轨迹 + 混合效应模型高分 SCI 框架（定制化设计）

---

## 一、核心科学问题

1. **分组轨迹差异**：HC / prodromal_SAA- / prodromal_SAA+ / PD_SAA+ 四组在 2 年内的
   MoCA 和 UPDRS-III 变化速率是否存在显著差异？
2. **网络独立预测**：控制疾病分组后，基线 MIND 网络属性（全局强度、节点、连边、
   默认网络连接强度等）能否独立预测临床量表评分随时间的恶化速率？

---

## 二、数据结构

- **格式**：长格式，每人 × 每时间点各占一行
- **时间点**：Year0（BL）= 0、Year1（V04）= 1、Year2（V06）= 2
- **因变量 Y**：`MoCA_score`、`UPDRS3`（两个量表分别建模）
- **核心预测变量 X**：
  - `Group`：4 水平分类变量，参照组 = HC
  - `MIND_baseline`：连续变量，建议先选 1–2 个核心指标（全局强度 / 节点指标 /
    连边指标 / 默认网络强度），再做探索性多指标分析
- **时间变量**：`Time`（数值，单位年：0 / 1 / 2）
- **随机效应**：`Subject_ID`（受试者 ID）
- **协变量**：`Age`、`Sex`、`Education`（对 MoCA 尤其重要），
  可加入 `Baseline_Score`（基线评分作为协变量，强化对变化速率的解读）

---

## 三、统计模型

### 模型 1 — 四组轨迹差异

> 回答科学问题 1：疾病阶段是否调制临床变化速率？

```
Y ~ Time * Group + Age + Sex + Education + (1 + Time | Subject_ID)
```

- **关键项**：`Time:Group` 交互项的显著性
- **事后比较**：计算各组对 Time 的简单斜率，进行 Tukey 校正两两比较

### 模型 2 — 基线 MIND 的独立预测（核心创新）

> 回答科学问题 2：MIND 网络特征是否调制临床变化速率？

```
Y ~ Time * Group + Time * MIND_baseline + Age + Sex + Education + (1 + Time | Subject_ID)
```

- **关键项**：`Time:MIND_baseline` 交互项
  - 显著 (p < 0.05) → 基线 MIND 调制了评分随时间的变化速率
  - 系数为正 → MIND 越高，下降越慢（保护性）；为负 → 相反
- **简单斜率分析**：在 MIND_baseline = 均值−1SD / 均值 / 均值+1SD 三水平上，
  分别计算 Y 随时间的变化斜率，并两两比较

---

## 四、Python 实现要点（与当前代码的关键差异）

### ① 随机斜率（当前代码缺失）

当前代码只有随机截距：
```python
smf.mixedlm(formula, data, groups=data['Subject_ID'])
```

应改为随机截距 + 随机斜率：
```python
smf.mixedlm(formula, data, groups=data['Subject_ID'], re_formula="~Time")
```

> `re_formula="~Time"` 等价于 R 的 `(1 + Time | Subject_ID)`

### ② 模型 2 公式

当前 `formula2` 中未同时包含 `Time * Group` 和 `Time * MIND_BL`，
应改为：
```python
formula2 = f"{scale} ~ Time * C(Group_MIND, Treatment('HC')) + Time * MIND_BL + {scale}_BL + Age_at_Visit + C(Sex) + Education"
```

### ③ 简单斜率分析（Python 实现 emtrends 等价）

```python
# 在三个 MIND 水平上计算各自的预测轨迹
m_val = df_clean['MIND_BL'].mean()
s_val = df_clean['MIND_BL'].std()

mind_levels = {
    'High (Mean+1SD)': m_val + s_val,
    'Mid (Mean)':      m_val,
    'Low (Mean-1SD)':  m_val - s_val,
}
# 对每个水平，构建 pseudo-dataset，固定 MIND_BL，预测三个时间点的值，
# 用 np.polyfit 拟合线性斜率，即为该水平的简单斜率估计
```

### ④ 协变量：加入基线评分

```python
# 在 formula2 中加入 {scale}_BL，控制基线起点差异
formula2 = f"{scale} ~ Time * MIND_BL + {scale}_BL + C(Group_MIND) + Age_at_Visit + C(Sex) + Education"
```

---

## 五、敏感性分析与进阶策略

| 策略 | 目的 | 操作 |
|---|---|---|
| 控制基线评分 | 在相同起点上比较变化速率 | 加入 `{scale}_BL` 作为协变量 |
| 缺失数据处理 | 避免非随机缺失偏倚 | `dropna` / 多重插补 |
| 多指标探索 | 避免 I 类错误膨胀 | PCA 降维 → 主成分建模，或 FDR 校正（BH 法） |
| 亚组敏感性 | 验证 SAA 分层的贡献 | 分别在前驱期、PD 亚组重复模型 2 |

---

## 六、预期产出

### 表格

| 编号 | 内容 |
|---|---|
| Table 1 | 四组基线特征（人口学、MoCA、UPDRS-III、核心 MIND 指标）|

### 图形

| 编号 | 内容 | 数据来源 |
|---|---|---|
| Figure 1 | 四组纵向轨迹图（估计边际均值 + 95% CI） | 模型 1 |
| Figure 2 | 交互效应图：高/中/低 MIND 三条预测轨迹 | 模型 2 简单斜率 |

### 结果报告示例

> "基线全局 MIND 强度每降低 1 个 SD，MoCA 的年下降速度加快 0.8 分
> （β = −0.8, 95% CI: −1.3 ~ −0.3, p = 0.002）。"

---

---

## 五、论文方法学章节撰写模板（Python 版）

> 用于投稿时的"统计方法"部分，括号内变量名按实际情况替换。

---

采用线性混合效应模型（Linear Mixed-Effects Model, LME）分析纵向临床数据。
以 MoCA（或 UPDRS-III）评分为因变量，以时间、疾病分组、基线 MIND 指标及其交互项
作为固定效应，并纳入年龄、性别、教育年限作为协变量；模型允许每位受试者拥有
独立的随机截距与随机斜率。通过检验时间（`Time`）与基线 MIND 指标（`MIND_BL`）
的交互项（`Time:MIND_BL`）来评估脑网络特征对临床变化速率的预测作用。
模型拟合采用 Python 3.9、statsmodels 0.14（`MixedLM`），优化方法依次尝试
lbfgs / powell / nm / bfgs，以 REML=False 估计；若仍不收敛则降级为仅随机截距，
必要时最终降级为 OLS 保底。事后简单斜率分析在
MIND_BL = 均值 ± 1 SD 三水平上进行，95% 置信区间由 Bootstrap 或 Delta 方法估计。
所有假设检验均为双侧，显著性水平 α = 0.05；多量表分析的 p 值采用
Benjamini–Hochberg 方法进行 FDR 校正。

---

## 六、扩展量表（GDS-15 / RBDSQ / NP1APAT / NP1FATG）

**答：已在 `step3c_lme_2year_multiscale.py` 中统一处理，无需单独建模。**

该脚本通过 `SCALES` 列表循环，对以下 6 个量表全部执行相同的双模型框架：

| 量表 | 临床意义 |
|---|---|
| `UPDRS3` | 运动功能（帕金森核心症状） |
| `MoCA` | 认知功能 |
| `GDS15_all` | 抑郁（Geriatric Depression Scale） |
| `RBDSQ_all` | REM 睡眠行为障碍（非运动症状） |
| `NP1APAT` | 淡漠（Apathy，非运动域子项） |
| `NP1FATG` | 疲劳（Fatigue，非运动域子项） |

每个量表独立输出：
- `Fig1_Group_Progression.png` — 四组轨迹图（模型 1）
- `Fig2_MIND_Prediction.png` — 三水平 MIND 预测轨迹图（模型 2）
- `Statistical_Summary.txt` — 两个模型的完整系数表

结果存放在 `./MIND_Research_Results/{量表名}/` 下。

---

## 六-扩展2：非运动精神症状量表（step3e）

**答：已在 `step3e_lme_nonmotor_extended.py` 中处理。**

5 个新量表，含 `_safe_col()` 处理特殊字符（S-AI/T-AI 含 `-`，patsy 需 `Q()` 包裹）：

| 量表 | 临床意义 | Time:MIND_BL β | p |
|---|---|---|---|
| `ESS_all` | 嗜睡（Epworth Sleepiness Scale） | +5.4 | 0.464 |
| `SCOPA_AUT_all` | 自主神经障碍（SCOPA-AUT） | −5.7 | 0.839 |
| `S-AI` | 状态焦虑（State Anxiety Inventory） | +88.9 | 0.005 ✓ |
| `T-AI` | 特质焦虑（Trait Anxiety Inventory） | +90.4 | 0.002 ✓ |
| `UPSIT_PRCNTGE` | 嗅觉功能（UPSIT 百分比） | — | OLS 保底 |

> **UPSIT 特殊情况**：绝大多数数据集中在 BL（V04 仅 21 人、V06 仅 33 人），LME 随机斜率和随机截距均无法收敛，最终 OLS 保底。

---

## 七、实现进度（对应 step3 脚本）

- [x] `step3c_lme_2year_multiscale.py`：加入 `re_formula=LME_RE_FORMULA`（三级降级，来自 config.py）
- [x] `step3c_lme_2year_multiscale.py`：`formula2` 同时包含 `Time * Group` 和 `Time * MIND_BL`
- [x] `step3c_lme_2year_multiscale.py`：简单斜率（Time:MIND_BL β/SE/95%CI/p）输出到 Statistical_Summary.txt
- [x] `step3_lme_updrs.py`：重构为双模型结构，补充 `C(Group_MIND)` 消除疾病阶段混淆
- [x] `config.py` 新增 `LME_RE_FORMULA = "~Time"` 和 `LME_METHODS`
- [x] `step3e_lme_nonmotor_extended.py`：5 个非运动/精神症状量表，含 `_safe_col()` 处理特殊字符

## 八、仍待确认

- [ ] `step3d_baseline_regression.py`：读取 `MIND_Final_Analysis_Table.csv`（宽格式），该文件路径未知，字段名与其他脚本不同，需确认
- [ ] 多量表 FDR 校正（BH 法）：step3c 当前无跨量表 FDR，若论文需要需补充
- [ ] 事后组间斜率两两比较（emtrends 等价 Python 实现）：当前仅报告 Time:MIND_BL 整体系数

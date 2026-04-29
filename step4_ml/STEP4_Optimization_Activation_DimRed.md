# Step4 优化方案：激活函数与降维策略（Plan1-3）

> 更新时间：2026-04-19
> 适用范围：Step4 三方案（Plan1 burden-resilience / Plan2 incremental ML / Plan3 topography-mechanism）
> 环境约束：统一在 `conda mind` 环境执行

## 一、当前结果问题诊断

| 方案 | 核心问题 | 原因分析 | 优先改进方向 |
|---|---|---|---|
| Plan 1（MIND 负荷/韧性） | burden 与临床表型相关，但解释度中等偏低 | burden score 过于聚合，拓扑信息损失；resilience 残差法在小样本下不稳定 | 非线性变换 + 网络拓扑维度保留 |
| Plan 2（机器学习预测） | 增量价值局部成立，不是全终点、全天窗成立 | MIND 特征维度设置可能不当；高维下有过拟合风险；非线性关系未被捕捉 | 特征降维 + 非线性特征工程 |
| Plan 3（拓扑/机制分析） | 拓扑效应较小；AHBA 获取失败 | 拓扑指标区分度不足；AHBA 缓存/下载失败导致机制层中断 | 拓扑特征压缩 + AHBA 本地化/替代 |

---

## 二、激活函数与非线性变换推荐

### 2.1 Plan 1：MIND Burden Score 构建

样本量有限，不建议直接深度学习；优先做可解释特征工程非线性变换。

| 方法 | 激活函数/变换 | 适用场景 | 推荐程度 |
|---|---|---|---|
| 对数变换 | `log(1+x)` | 偏态分布 MIND 指标 | ★★★★★ |
| Box-Cox / Yeo-Johnson | 自动选择最优参数 | 非正态标准化（含负值建议 Yeo-Johnson） | ★★★★☆ |
| Sigmoid 压缩 | `1/(1+e^{-z})` | 压缩极端值到 `[0,1]` | ★★★★☆ |
| 分位数变换 | `QuantileTransformer` | 转换到均匀/正态分布 | ★★★★☆ |
| 样条基展开 | B-spline | 捕捉 burden-临床关系非线性 | ★★★☆☆ |

推荐实现（示意）：

```python
from sklearn.preprocessing import QuantileTransformer, PowerTransformer
import numpy as np

# 方法1: Yeo-Johnson（支持负值）
pt = PowerTransformer(method='yeo-johnson')
mind_transformed = pt.fit_transform(mind_features)

# 方法2: 分位数变换到正态（优先）
qt = QuantileTransformer(output_distribution='normal')
mind_transformed = qt.fit_transform(mind_features)

# 方法3: 对偏态指标做 log(1+x)
mind_log = np.log1p(mind_features)

# 方法4: Sigmoid 压缩
mind_sigmoid = 1 / (1 + np.exp(-mind_features))
```

### 2.2 Plan 2：机器学习预测模型

| 模型层 | 推荐激活/非线性 | 原因 |
|---|---|---|
| ElasticNet 主模型 | `PolynomialFeatures(degree=2, interaction_only=True)` | 捕捉 MIND × SAA 等交互 |
| XGBoost 挑战模型 | `reg:pseudohubererror` / `reg:squaredlogerror` | 对异常值鲁棒，适配临床评分 |
| MLP 补充模型 | ReLU + LeakyReLU 思路（sklearn 中用 `relu`/`tanh`） | 中等样本下补充非线性能力 |
| 核映射补充 | RBF kernel | 处理线性不可分映射 |

推荐实现（示意）：

```python
from sklearn.preprocessing import PolynomialFeatures
from sklearn.neural_network import MLPRegressor
import xgboost as xgb

# 方法1: 二阶交互特征
poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
X_poly = poly.fit_transform(X)

# 方法2: 小型 MLP
mlp = MLPRegressor(
    hidden_layer_sizes=(32, 16),
    activation='relu',
    alpha=0.01,
    early_stopping=True,
    max_iter=500,
)

# 方法3: XGBoost（Huber 风格目标）
model = xgb.XGBRegressor(
    objective='reg:pseudohubererror',
    tree_method='hist',
    max_depth=4,
    learning_rate=0.05,
    n_estimators=100,
)

# 方法4: XGBoost（Squared Log Error）
model_sle = xgb.XGBRegressor(
    objective='reg:squaredlogerror',
    max_depth=4,
    learning_rate=0.05,
    n_estimators=100,
)
```

### 2.3 Plan 3：网络拓扑与机制分析

| 分析步骤 | 推荐激活/方法 | 作用 |
|---|---|---|
| 拓扑特征提取 | `tanh` 压缩 | 压缩异常值到 `[-1, 1]`，保留方向 |
| hub vulnerability | softmax 加权 | 节点 hubness 概率化权重 |
| 空间相关 | Spearman（rank-based） | 捕捉单调非线性关系 |
| 机制映射 | kernel PLS (RBF) | 捕捉基因-影像非线性关联 |

推荐实现（示意）：

```python
import numpy as np
from scipy import stats

# 方法1: tanh 压缩
compressed = np.tanh(mind_topology)

# 方法2: softmax hub 加权
def softmax_hub_weight(hub_scores):
    exp_scores = np.exp(hub_scores - np.max(hub_scores))
    return exp_scores / exp_scores.sum()

hub_weights = softmax_hub_weight(nodal_hub_scores)

# 方法3: Spearman 相关
rho, p_value = stats.spearmanr(mind_abnormality, gene_expression)
```

AHBA 获取失败应对：
- 优先本地缓存目录（固定 cache path）和损坏 zip 清理重拉。
- 备选转录组资源：PsychENCODE、BrainSpan、Human Protein Atlas。

---

## 三、Step4 三方案统一入口设计（先文档设计）

### 3.1 目标

为 Step4 提供一个统一 CLI 入口，避免分别手动执行多个脚本，支持按方案、按阶段、按资源模式运行。

### 3.2 建议入口

- 新入口脚本：`step4_ml/step4_entry.py`（已实现 v1）
- 统一命令示例：
  - `python step4_ml/step4_entry.py --plan 1`
  - `python step4_ml/step4_entry.py --plan 2`
  - `python step4_ml/step4_entry.py --plan 3 --skip-ahba`
  - `python step4_ml/step4_entry.py --plan all --mode quick`

### 3.3 参数设计

- `--plan {1,2,3,all}`：选择单方案或全流程。
- `--mode {quick,full}`：快速模式（跳过重计算）/ 全量模式。
- `--skip-ahba`：Plan3 跳过 AHBA，先落拓扑结果。
- `--cache-dir PATH`：指定 AHBA 本地缓存目录。
- `--report-only`：仅汇总已存在结果，不重跑模型。

当前已实现参数：
- `--plan {1,2,3,all}`

当前交互模式：
- 直接执行 `python step4_ml/step4_entry.py` 时弹出交互菜单，支持 `1/2/3/a/q`。

### 3.4 执行前检查

- 检查当前环境是否为 `mind`。
- 检查输入数据文件是否存在。
- 检查输出目录权限与剩余磁盘空间。

### 3.5 输出汇总规范

- 统一汇总 CSV：`MIND_Research_Results/ML_Prediction/Step4_Entry_Overview.csv`
- 统一运行日志：`MIND_Research_Results/ML_Prediction/Step4_Entry_RunLog.txt`

### 3.6 Allen / AHBA 固定目录结构

- 原始 Allen / AHBA 资源：`./data/external/allen/`
- atlas 文件：`./data/external/allen/atlas/`
- expression summaries / local fallback：`./data/external/allen/expression/`
- abagen cache：`./data/external/allen/cache/abagen/`
- Plan 3 最终机制输出：`./MIND_Research_Results/ML_Prediction/Aim3_Plan3_Topography_Mechanism/AHBA/`

Allen / AHBA 仅作为 Plan 3 的机制注释层，不属于 Plan 2 预测特征主线。

---

## 四、分阶段落地顺序（建议）

1. 先实现统一入口（仅调度现有脚本，不改算法）。
2. Plan1 加入非线性变换与 burden 对比评估。
3. Plan2 增加交互特征与 XGBoost 挑战模型。
4. Plan3 增加拓扑压缩与 AHBA 缓存修复策略。
5. 最后统一生成跨方案对比报告。

## 五、当前状态标记

- 本文档为“优化设计草案 V1”，先用于对齐方向。
- 代码实现建议分 PR/分 commit 逐步落地，避免一次性大改导致回归风险。

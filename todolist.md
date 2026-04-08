# MIND 分析待办清单

> 更新时间：2026-04-09

---

## Step 4 — 机器学习预测模型（尚未开发）

- [ ] 特征工程：从基线 MIND 矩阵提取节点强度、连边上三角、网络指标
- [ ] 模型选型：随机森林 / SVR / Elastic Net 回归预测 UPDRS-III 斜率
- [ ] 交叉验证框架（Leave-One-Out 或 5-fold）
- [ ] SHAP 特征重要性可视化
- [ ] 对比基线人口学变量的增量预测力（R² 增益）

---

## 统计补充

- [ ] `step2c_nodal_strength_ancova.py`：运行并验证输出（含 3D 脑表面图）
- [ ] `step2d_edgewise_analysis.py`：四组 ANCOVA 耗时极长，考虑并行化（joblib）
- [ ] NBS（Network-Based Statistics）替代简单 T 检验，用于 edgewise 多重比较校正
- [ ] 多量表 FDR 校正（BH 法）：为 `step3c_lme_2year_multiscale.py` 增加跨量表校正
- [x] `step3f_saa_subgroup_analysis.py`：SAA+ vs SAA- BL MIND 组间差异 + SAA 对临床变化速率的调节（2026-03-28）

## 可视化补充

- [ ] `step1_mean_surface_maps.py`：确认 nilearn FSAverage 路径在当前环境下可用
- [ ] `step2b_7network_radar_boxplot.py`：雷达图标签检查（YEO7 缩写是否完整）
- [ ] `step2b_connectome_viz.py`：nilearn connectome 图颜色映射与 config.py 对齐验证
- [x] `step3d_baseline_regression.py`：恢复 `V10` / `V12` 成对 Figure 1 / Figure 2 输出，并统一至 config 驱动样式（2026-04-09）
- [x] `step3d_baseline_regression.py`：恢复保存后统一阻塞预览弹窗（2026-04-09）

## 数据文件

- [ ] 确认 `./data/MIND-Networks_newgroup/` 下四个子目录均已包含全部受试者矩阵
- [ ] 验证 `scale/MIND_Longitudinal_Clean_Data.csv` 中 `MIND_Sig_Index` 字段是否与
      `step3_lme_updrs.py` 及 `step3c_lme_2year_multiscale.py` 引用路径一致
- [x] `step3c_lme_2year_multiscale.py` 路径已从 `./量表/` 更新为 `./scale/`（2026-03-27）
- [x] `step3d_baseline_regression.py` 已完全改为读取 `./scale/MIND_baseline_with_followup_V04_V12.csv`，不再依赖旧宽表（2026-04-09）

---

## 已完成（供记录）

- [x] 统一 config.py 控制全部可视化常量（颜色、图幅、DPI 等）
- [x] 所有脚本按 Step1-4 规范重命名
- [x] 合并重复功能脚本（step2c / step2d / step2_stats / step3_lme_updrs）
- [x] 删除被合并的旧文件

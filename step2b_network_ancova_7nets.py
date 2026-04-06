import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from nilearn import plotting, datasets
from config import *

# 1. 读取并筛选基线数据
df = pd.read_csv('./scale/MIND_baseline_with_followup_V04_V12.csv')
df_bl = df[df['EVENT_ID'] == 'BL'].copy()

# 2. 定义分析目标 (7大子网)
networks = [c for c in df_bl.columns if 'MIND_' in c and c != 'MIND_Sig_Index']
results = []

print(">>> 正在进行 ANCOVA 分析 (带协变量)...")

for net in networks:
    # 构建 ANCOVA 模型
    model = ols(f"{net} ~ C(Group_MIND) + Age_at_Visit + C(Sex) + Education", data=df_bl).fit()
    anova_table = sm.stats.anova_lm(model, typ=2)
    p_val = anova_table.loc['C(Group_MIND)', 'PR(>F)']
    
    # 记录结果
    results.append({'Network': net, 'p_uncorrected': p_val})

# 3. FDR 校正
res_df = pd.DataFrame(results)
res_df['p_fdr'] = multipletests(res_df['p_uncorrected'], method='fdr_bh')[1]
print(res_df)

# 4. 可视化示例：如何画出“脑子” (以特定 T 值图为例)
def plot_brain_map(t_values_68, title="Group Difference"):
    """
    注意：此函数需要你提供 68 个脑区的 T 值列表。
    使用的是 Desikan-Killiany (DK) 模板。
    """
    # 加载 DK 模板的坐标
    atlas = datasets.fetch_atlas_desikan_killiany()
    # 假设你已经计算好了 68 个脑区的差异，将其映射到图上
    # 这里仅为逻辑展示，实际需传入对应的节点数值
    plotting.plot_markers(t_values_68, atlas.centroids, title=title,
                         node_cmap=CMAP_TRAJECTORY, display_mode='z')
    plotting.show()

# 保存结果供下一步画图
res_df.to_csv('./ANCOVA_Results_Baseline.csv', index=False)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from math import pi

# 1. 加载数据
df = pd.read_csv('./MIND_Detailed_Network_Analysis.csv')

# 2. 设置分组顺序和颜色 (与你之前的图保持一致)
group_order = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']
colors = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3"] # 对应绿、橙、蓝、紫
networks = ['Visual', 'Somatomotor', 'Dorsal_Attention', 'Ventral_Attention', 'Limbic', 'Frontoparietal', 'Default']
net_cols = [f'MIND_{n}' for n in networks]

# --- 绘图 1: 子网趋势并排箱线图 ---
print(">>> 正在生成子网趋势箱线图...")
plt.figure(figsize=(20, 10))
for i, net in enumerate(networks):
    plt.subplot(2, 4, i+1)
    sns.boxplot(x='Group_MIND', y=f'MIND_{net}', data=df, order=group_order, palette=colors, showfliers=False)
    sns.stripplot(x='Group_MIND', y=f'MIND_{net}', data=df, order=group_order, color=".3", alpha=0.3, size=2)
    plt.title(f'Network: {net}', fontsize=14)
    plt.xlabel('')
    plt.ylabel('MIND Strength')
    plt.xticks(rotation=15)

plt.tight_layout()
plt.savefig('MIND_7Networks_Boxplots.png', dpi=300)
print("已保存: MIND_7Networks_Boxplots.png")

# --- 绘图 2: 组间受损雷达图 ---
print(">>> 正在生成网络受损雷达图...")
# 计算每组的均值
group_means = df.groupby('Group_MIND')[net_cols].mean().reindex(group_order)

# 设置雷达图参数
labels = networks
num_vars = len(labels)
angles = [n / float(num_vars) * 2 * pi for n in range(num_vars)]
angles += angles[:1] # 闭合圆圈

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

for i, group in enumerate(group_order):
    values = group_means.loc[group].tolist()
    values += values[:1] # 闭合
    ax.plot(angles, values, color=colors[i], linewidth=2, label=group)
    ax.fill(angles, values, color=colors[i], alpha=0.1)

# 添加标签
ax.set_theta_offset(pi / 2)
ax.set_theta_direction(-1)
plt.xticks(angles[:-1], labels, fontsize=12)

# 设置刻度（根据你的数据分布自动调整，假设在0.1-0.25之间）
# ax.set_rlabel_position(0)
# plt.yticks([0.15, 0.18, 0.21], ["0.15", "0.18", "0.21"], color="grey", size=10)

plt.title('MIND Network Profile across 4 Stages', size=20, y=1.1)
plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
plt.savefig('MIND_7Networks_Radar.png', dpi=300)
print("已保存: MIND_7Networks_Radar.png")

plt.show()
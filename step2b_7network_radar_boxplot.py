import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from math import pi
from config import *

apply_style()

# 1. 加载数据
df = pd.read_csv('./scale/MIND_baseline_with_followup_V04_V12.csv')

# 2. 分组与网络定义从 config 统一导入
net_cols = [f'MIND_{n}' for n in NETWORKS]

# --- 绘图 1: 子网趋势并排箱线图 ---
print(">>> 正在生成子网趋势箱线图...")
plt.figure(figsize=FIG_MULTI_NETWORK)
for i, net in enumerate(NETWORKS):
    plt.subplot(2, 4, i+1)
    sns.boxplot(x='Group_MIND', y=f'MIND_{net}', data=df, order=GROUP_ORDER, palette=GROUP_COLORS, showfliers=False)
    sns.stripplot(x='Group_MIND', y=f'MIND_{net}', data=df, order=GROUP_ORDER, color=STRIP_COLOR, alpha=ALPHA_STRIP, size=STRIP_SIZE)
    plt.title(f'Network: {net}', fontsize=FONT_TITLE)
    plt.xlabel('')
    plt.ylabel('MIND Strength')
    plt.xticks(rotation=15)

plt.tight_layout()
plt.savefig('MIND_7Networks_Boxplots.png', dpi=DPI)
print("已保存: MIND_7Networks_Boxplots.png")

# --- 绘图 2: 组间受损雷达图 ---
print(">>> 正在生成网络受损雷达图...")
# 计算每组的均值
group_means = df.groupby('Group_MIND')[net_cols].mean().reindex(GROUP_ORDER)

# 设置雷达图参数
labels = NETWORKS
num_vars = len(labels)
angles = [n / float(num_vars) * 2 * pi for n in range(num_vars)]
angles += angles[:1]  # 闭合圆圈

fig, ax = plt.subplots(figsize=FIG_RADAR, subplot_kw=dict(polar=True))

for i, group in enumerate(GROUP_ORDER):
    values = group_means.loc[group].tolist()
    values += values[:1]  # 闭合
    ax.plot(angles, values, color=GROUP_COLORS[i], linewidth=LINEWIDTH_THIN, label=group)
    ax.fill(angles, values, color=GROUP_COLORS[i], alpha=ALPHA_FILL)

# 添加标签
ax.set_theta_offset(pi / 2)
ax.set_theta_direction(-1)
plt.xticks(angles[:-1], labels, fontsize=FONT_AXIS)

plt.title('MIND Network Profile across 4 Stages', size=FONT_SUPTITLE + 4, y=1.1)
plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
plt.savefig('MIND_7Networks_Radar.png', dpi=DPI)
print("已保存: MIND_7Networks_Radar.png")

plt.show()
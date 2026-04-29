"""config.py — MIND 项目统一可视化配置。

在每个分析脚本顶部加入：
    from config import *
    apply_style()
"""

import matplotlib.pyplot as plt
import seaborn as sns

# ── 分组定义 ──────────────────────────────────────────────────────────────────
# 四组疾病阶段，按疾病进展顺序排列
GROUP_ORDER   = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']
# 对应颜色：绿 / 橙 / 蓝紫 / 粉紫
GROUP_COLORS  = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3']
# 字典形式，可直接传给 seaborn palette 参数
GROUP_PALETTE = dict(zip(GROUP_ORDER, GROUP_COLORS))

# ── 脑网络定义 ────────────────────────────────────────────────────────────────
# 完整名称列表，用于生成列名（如 MIND_Visual、MIND_Somatomotor 等）
NETWORKS = [
    'Visual', 'Somatomotor', 'Dorsal_Attention', 'Ventral_Attention',
    'Limbic', 'Frontoparietal', 'Default',
]

# Yeo 7 网络 ROI 映射（DK68 分区，1-indexed）
# 缩写键名与各文件内部逻辑保持一致
YEO7_MAP = {
    'Visual':         [1, 2, 3, 4, 5, 6, 7, 8, 35, 36, 37, 38, 39, 40, 41, 42],
    'Somatomotor':    [9, 10, 11, 12, 13, 14, 43, 44, 45, 46, 47, 48],
    'Dorsal_Attn':    [15, 16, 17, 49, 50, 51],
    'Ventral_Attn':   [18, 19, 20, 52, 53, 54],
    'Limbic':         [21, 22, 55, 56],
    'Frontoparietal': [23, 24, 25, 26, 57, 58, 59, 60],
    'Default':        [27, 28, 29, 30, 31, 32, 33, 34, 61, 62, 63, 64, 65, 66, 67, 68],
}

# ── 时间映射 ──────────────────────────────────────────────────────────────────
# 完整随访时间点（单位：年）
TIME_MAP_FULL = {'BL': 0, 'V04': 1, 'V06': 2, 'V08': 3, 'V10': 4, 'V12': 5}
# 2年随访时间点
TIME_MAP_3PT  = {'BL': 0, 'V04': 1, 'V06': 2}
# 2年随访 X 轴刻度标签
TIME_LABELS_3 = ['Baseline (BL)', 'Year 1 (V04)', 'Year 2 (V06)']
TIME_WINDOW_3PT_LABEL = 'BL/V04/V06'
TIME_WINDOW_3PT_TITLE = '2-Year Fixed Timepoints'
TIME_WINDOW_FU1_LABEL = 'Baseline to Year 1'
TIME_WINDOW_FU2_LABEL = 'Baseline to Year 2'
STEP3D_REGRESSION_ENDPOINTS = [
    {'event': 'V04', 'label': 'Baseline to Year 1', 'suffix': 'V04'},
    {'event': 'V06', 'label': 'Baseline to Year 2', 'suffix': 'V06'},
    {'event': 'V10', 'label': 'Baseline to Year 4', 'suffix': 'V10'},
    {'event': 'V12', 'label': 'Baseline to Year 5', 'suffix': 'V12'},
]
STEP3D_PRIMARY_ENDPOINTS = ['V10', 'V12']
# 全时间点 X 轴刻度标签
TIME_LABELS_FULL = ['Baseline (BL)', 'Year 1 (V04)', 'Year 2 (V06)', 'Year 3 (V08)', 'Year 4 (V10)', 'Year 5 (V12)']
TIME_WINDOW_FULL_LABEL = 'BL/V04/V06/V08/V10/V12'
TIME_WINDOW_FULL_TITLE = 'Full Available Timepoints'
STEP3_FULL_MIN_PLOT_N = 100

TIMEPOINTS_FULL = list(TIME_MAP_FULL.keys())
TIMEPOINTS_3PT = list(TIME_MAP_3PT.keys())
BL_EVENT = TIMEPOINTS_3PT[0]
FOLLOWUP_EVENT_1Y = TIMEPOINTS_3PT[1]
FOLLOWUP_EVENT_2Y = TIMEPOINTS_3PT[2]


def filter_event_rows(df, time_map, event_col='EVENT_ID'):
    return df[df[event_col].isin(time_map.keys())].copy()


def add_time_from_event(df, time_map, event_col='EVENT_ID', clean_col='EVENT_ID_Clean', time_col='Time'):
    df = filter_event_rows(df, time_map, event_col=event_col)
    df[clean_col] = df[event_col]
    df[time_col] = df[clean_col].map(time_map)
    return df


def get_time_ticks_and_labels(time_map, labels=None):
    tick_values = list(time_map.values())
    tick_labels = labels if labels is not None else list(time_map.keys())
    return tick_values, tick_labels

# MIND 水平分组标签（纵向轨迹图用）
MIND_LEVEL_ORDER = ['High MIND (Mean+1SD)', 'Mid MIND (Mean)', 'Low MIND (Mean-1SD)']

# ── 图像尺寸（英寸，宽×高） ───────────────────────────────────────────────────
FIG_SINGLE           = (10,  6)   # 标准单图
FIG_SMALL            = ( 8,  6)   # 紧凑单图（散点回归图等）
FIG_BRAIN_SURFACE    = (14,  5)   # 脑表面图（左+右半球并排）
FIG_BRAIN_SURFACE_SM = (12,  5)   # 较小的脑表面图
FIG_HEATMAP_LG       = (12, 10)   # 大热力图
FIG_HEATMAP_SM       = (10,  8)   # 中等热力图
FIG_HEATMAP_SQ       = ( 8,  7)   # 正方形热力图
FIG_MULTI_NETWORK    = (20, 10)   # 2×4 子网络多图排版
FIG_RADAR            = (10, 10)   # 完整雷达图（极坐标）
FIG_RADAR_SM         = ( 7,  7)   # 紧凑雷达图
FIG_WIDE_BAR         = (15,  6)   # 显著性条形图（宽幅）

# ── 保存分辨率 ────────────────────────────────────────────────────────────────
DPI = 300  # 出版级分辨率

# ── 色彩映射 ──────────────────────────────────────────────────────────────────
CMAP_DIVERGING  = 'RdBu_r'    # T 图、组间差异矩阵（发散型）
CMAP_SEQUENTIAL = 'viridis'   # 通用连续型（密度、原始数值）
CMAP_PVAL       = 'viridis_r' # FDR 校正 p 值图（p 越小越亮）
CMAP_CONNECTOME = 'YlOrRd'    # 脑连接体边权重
CMAP_TRAJECTORY = 'coolwarm'  # MIND 水平纵向轨迹线

# ── Seaborn 调色板（非分组颜色的图） ─────────────────────────────────────────
PALETTE_BOX    = 'Set2'   # 箱线图 / 条形图（无分组颜色时）
PALETTE_VIOLIN = 'muted'  # 小提琴图

# ── 单色常量 ──────────────────────────────────────────────────────────────────
STRIP_COLOR    = '.3'    # 散点叠加（stripplot / swarmplot）的点颜色（深灰）
COLOR_BAR_SIG  = 'teal'  # 显著性条形图的填充色
COLOR_REF_LINE = 'red'   # 阈值 / 参考线颜色

# ── 点线大小 ──────────────────────────────────────────────────────────────────
MARKER          = 'o'    # 默认标记形状
MARKERSIZE      = 8      # 默认标记大小
MARKERSIZE_LG   = 10     # 较大标记（重点轨迹图）
LINEWIDTH       = 2.5    # 默认线宽
LINEWIDTH_THIN  = 2      # 细线（雷达图、边框）
LINEWIDTH_THICK = 3      # 粗线（重要轨迹线）
STRIP_SIZE      = 2      # 散点叠加的点大小

# ── 透明度 ────────────────────────────────────────────────────────────────────
ALPHA_FILL  = 0.1   # 雷达图面积填充
ALPHA_STRIP = 0.3   # 散点叠加数据点
ALPHA_GRID  = 0.6   # 背景网格线

# ── 字体大小 ──────────────────────────────────────────────────────────────────
FONT_SUPTITLE = 16   # 总标题（suptitle）
FONT_TITLE    = 14   # 子图标题
FONT_AXIS     = 12   # 坐标轴标签 / 刻度标签

# ── 网格线样式 ────────────────────────────────────────────────────────────────
GRID_LINESTYLE = ':'  # 虚线网格（更柔和）

# ── seaborn lineplot 误差条 ───────────────────────────────────────────────────
ERRORBAR = ('ci', 95)  # 95% 置信区间

# ── 混合效应模型（LME）参数 ────────────────────────────────────────────────────
# 优化器尝试顺序：从快到健壮，任一成功即停止，全失败后降级为 OLS
LME_METHODS = ['lbfgs', 'powell', 'nm', 'bfgs']
# 随机效应公式：随机截距 + 随机斜率（等价于 R 的 (1 + Time | Subject_ID)）
# 若样本量不足导致奇异矩阵，代码自动降级为仅随机截距（re_formula=None）
LME_RE_FORMULA = "~Time"

# ── 脑连接体可视化参数（nilearn） ─────────────────────────────────────────────
CONNECTOME_NODE_COLOR     = 'darkred'  # 节点颜色
CONNECTOME_NODE_SIZE      = 40         # 节点大小
CONNECTOME_EDGE_CMAP      = CMAP_CONNECTOME  # 边权重色彩映射
CONNECTOME_EDGE_THRESHOLD = '95%'     # 只显示前 5% 最强连接
BRAIN_THRESHOLD           = 0.01      # 脑表面图阈值

# ── 全局主题函数 ──────────────────────────────────────────────────────────────
def apply_style():
    """统一应用 matplotlib/seaborn 视觉主题，每个脚本调用一次即可。"""
    sns.set_theme(style='ticks', font_scale=1.1)
    plt.rcParams.update({
        'figure.dpi':        100,
        'savefig.dpi':       DPI,
        'savefig.bbox':      'tight',
        'figure.figsize':    (8, 6),
        'figure.facecolor':  'white',
        'axes.facecolor':    'white',
        'figure.max_open_warning': 0,
        'axes.spines.top':   False,
        'axes.spines.right': False,
        'legend.frameon':    False,
        'axes.labelsize':    FONT_AXIS,
        'axes.titlesize':    FONT_TITLE,
        'xtick.labelsize':   FONT_AXIS,
        'ytick.labelsize':   FONT_AXIS,
        'grid.linestyle':    GRID_LINESTYLE,
        'grid.alpha':        ALPHA_GRID,
    })
    plt.ioff()


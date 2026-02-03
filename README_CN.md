# MIND（形态学逆散度）

本仓库包含了用于估算大脑结构相似性网络的形态学逆散度（MIND）计算的 Python 实现。

## 安装
你可以通过如下方式克隆本代码：
```
git clone https://github.com/isebenius/MIND.git
```

## MIND 计算
计算 MIND 网络的主函数为 MIND.py 中的 compute_mind()。你可以如下导入：
```
import sys
sys.path.insert(1, '/path/to/MIND/code/')
from MIND import compute_MIND
```

本实现可自动处理 FreeSurfer 的标准输出，自动计算 MIND 网络。最简单的用法如下：

```
# 指定 surfer 目录路径，即包含 surf、mri、label 等 FreeSurfer 输出的文件夹路径
path_to_surf_dir = '/path/to/surfer/dir'

# 指定参与 MIND 计算的特征。以下缩写分别代表 ?h.thickness, ?h.curv, ?h.volume, ?h.sulc, ?h.area
features = ['CT','MC','Vol','SD','SA']

# 选择分区方案。已在 Desikan Killiany (DK)、HCP-Glasser、DK-308 和 DK-318 上测试。
parcellation = 'aparc'

# 返回一个区域×区域的 DataFrame，即最终的 MIND 网络。
MIND = compute_MIND(path_to_surf_dir, features, parcellation)
```

## 所需文件
基本用法需要 FreeSurfer 表面 overlay 格式的顶点级数据（默认在 surf/ 文件夹下，如 ?h.curv, ?h.thickness 等），以及 label/ 文件夹下的 .annot 文件用于分区。

注意：本代码仅在 FreeSurfer v5.3 输出和 DK、DK-318、HCP 分区方案下测试过。若使用其他模板或 FreeSurfer 版本，需根据命名规则做适当调整。例如，不同分区方案下“unknown”脑区的命名不同，需手动修改代码（如 get_vertex_df.py 第 149 行的 unknown_regions 变量）。

## compute_MIND 命令的特征参数说明
默认 features 参数接受 [CT,MC,Vol,SD,SA] 的任意组合，分别对应 FreeSurfer 的 ?h.thickness, ?h.curv, ?h.volume, ?h.sulc, ?h.area。

你也可以传入其他特征的完整路径，只要它们是 FreeSurfer 的表面 overlay 格式且命名为“?h.feature”。例如：
```
features = ['CT', 'path/to/?h.feature']
```

features 参数的完整说明如下（详见 get_vertex_df.py 的函数说明）：

```
def get_vertex_df(surf_dir, features, parcellation):
    '''
    输入说明：
    • surf_dir (str)：包含 FreeSurfer 输出（label, mri, surf 等）的目录路径。
    • features (list)：
        可包含如下类型：
            str：
                • ['CT','Vol','SA','MC','SD'] 之一。会自动在 surf_dir/surf 下查找对应文件：
                    CT: ?h.thickness
                    Vol: ?h.volume
                    SA: ?h.area
                    MC: ?h.curv
                    SD: ?h.sulc
                • 也可直接传入 'thickness', 'volume', 'sulc' 等字符串，分别对应 surf_dir/surf/lh.thickness 和 surf_dir/surf/rh.thickness。
                • 还可传入完整路径，问号 ? 代表半球，如 "full/path/to/?h.feature"，会查找 full/path/to/lh.feature 和 full/path/to/rh.feature。
            tuple: (path/to/lh_surface_feature, path/to/rh_surface_feature)
                • 也可直接传入左右半球特征文件路径的元组。
                （文件需能被 nibabel 的 read_morph_data 读取，即 FreeSurfer 表面格式）
                例如：
                (path/to/lh.FA.mgh, path/to/rh.FA.mgh)
        features 参数可混合上述多种类型，如：['CT','SD',(path/to/lh_feature1, path/to/rh_feature1), (path/to/lh_feature2, path/to/rh_feature2)]
    • parcellation (str)：分区方案名称。label 目录下需有 'lh.' + parcellation + '.annot' 和 'rh.' + parcellation + '.annot' 文件。
    '''
```

## 包含体积特征
本仓库还提供了基于 nipype 的体积 MRI 特征投影到表面的函数，见 register_and_vol2surf.py。
- register_and_vol2surf：将体积图像配准到 T1 并投影到白质表面。
- calculate_surface_t1t2_ratio：将 T2 配准到 T1，计算 T1/T2 比值并投影到白质表面。

使用这些函数需安装 Freesurfer 和 afni，并确保已用 recon-all 处理过被试。

```
function register_and_vol2surf(mov, subject_id, out_dir, b0 = None, feature_name = 'vol-feature', contrast = 't2', sampling_units = 'frac', sampling_range = (0.2,0.8,0.1), sampling_method = 'average', cleanup=True):
  '''
  将体积图像配准到 T1 并投影到白质表面。
  参数说明略。
  '''

function calculate_surface_t1t2_ratio(t2_loc, subject_id, out_dir, t1_loc = None, feature_name = 'T2', contrast = 't2', sampling_units = 'frac', sampling_range = (0.2,0.8,0.1), sampling_method = 'average', cleanup=True):
  '''
  将 T2 配准到 T1，计算 T1/T2 比值并投影到白质表面。
  参数说明略。
  '''
```

运行上述命令后，输出的表面文件即可作为特征传入 compute_MIND。

## 重复值与单变量网络
MIND 仅适用于严格连续分布的数据。如果顶点级数据有大量重复值，MIND 结果会失效，代码也会报错。最常见于只用单一特征时。若遇到准连续分布但有重复值，可用 'resample' 标志在 calculate_mind_network 函数中实现区内重采样。

## 参考文献
如在研究中使用本软件计算 MIND 网络，请引用：

Sebenius, I., Seidlitz, J., Warrier, V. et al. Robust Estimation of Cortical Similarity Networks from Brain MRI. Nat Neurosci 26, 1461–1471 (2023). https://doi.org/10.1038/s41593-023-01376-7

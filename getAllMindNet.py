import sys
import os
import pickle
import numpy as np
import pandas as pd
from MIND import compute_MIND

# freesurfer预处理后的被试所在主路径，请提前删除掉此文件夹中的’fasverage‘
main_folder = './/data//PAResult'
# 皮层分区文件所在主路径
parcel_location = './/data//parcellation/'

# 遍历主文件夹中的所有子文件夹
for subdir in os.listdir(main_folder):
    subdir_path = main_folder + '/' + subdir
    print(subdir_path)

    # 读取area、curv、thickness、volume、sulc等结构特征
    features = [subdir_path + '/surf/?h.area.fsaverage.mgh',
                subdir_path + '/surf/?h.curv.fsaverage.mgh',
                subdir_path + '/surf/?h.thickness.fsaverage.mgh',
                subdir_path + '/surf/?h.volume.fsaverage.mgh',
                subdir_path + '/surf/?h.sulc.fsaverage.mgh',]

    # 读取大脑分区文件
    # parcellation = 'aparc'  # DK68
    # parcellation = 'aparc.a2009s'  # Destrieux Atlas 148
    parcellation = '500.aparc'  # DK308
    # parcellation = 'aparc_HCP_MMP1.freesurfer'  # HCP
    # parcellation = 'atl-Schaefer2018_space-fsaverage_hemi-L_desc-500Parcels7Networks_deterministic'

    # 计算 MIND net
    np.seterr(divide='ignore', invalid='ignore')  # 消除被除数为0的警告
    MIND = compute_MIND(main_folder, features, parcellation, parcel_location)

    # 输出并保存 MIND net
    print(MIND)
    dataType = type(MIND)
    print("The data type is:", dataType)

    # 仅保存为Python的pickle文件
    surfer_location = subdir_path + '/'
    output_file = os.path.join(surfer_location, 'MIND.pkl')
    with open(output_file, 'wb') as f:
        pickle.dump(MIND, f)
    print("Data saved to:", output_file)


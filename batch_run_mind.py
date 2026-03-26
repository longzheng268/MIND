import os
import pandas as pd
from MIND import compute_MIND

# 1. 路径设置 (务必带 /)
FS_ROOT = './data/Recon-Result/'
SAVE_ROOT = './data/MIND-Networks/'
os.makedirs(SAVE_ROOT, exist_ok=True)

# 2. 参数设置
features = ['CT', 'Vol', 'SA', 'MC', 'SD']
parcellation = 'aparc'

# 3. 开始循环
groups = ['HC', 'PD', 'prodromal']
for group in groups:
    group_in = os.path.join(FS_ROOT, group)
    group_out = os.path.join(SAVE_ROOT, group)
    os.makedirs(group_out, exist_ok=True)
    
    if not os.path.exists(group_in):
        continue

    subjs = [s for s in os.listdir(group_in) if os.path.isdir(os.path.join(group_in, s))]
    print(f"\n>>> 正在处理组: {group} (共 {len(subjs)} 个被试)")
    
    for subj in subjs:
        # 路径结尾加 /
        subj_dir = os.path.join(group_in, subj) + '/'
        output_file = os.path.join(group_out, f"{subj}_MIND.csv")
        
        if os.path.exists(output_file):
            continue
            
        try:
            print(f"正在计算: {subj} ...", end='\r')
            # --- 修正点：传入了 4 个参数，第四个参数也是 subj_dir ---
            mind_net = compute_MIND(subj_dir, features, parcellation, subj_dir)
            
            mind_net.to_csv(output_file)
        except Exception as e:
            print(f"\n!!! 失败: {subj}, 原因: {e}")

print("\n\n所有任务已完成！结果保存在 data/MIND-Networks/")
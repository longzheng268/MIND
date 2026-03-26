import os
import pandas as pd
import numpy as np
import glob
import re

# --- 路径配置 ---
MIND_ROOT = './data/MIND-Networks_newgroup/'
SAA_FILE = './量表/患者编号和SAA状态.csv'
SCALE_NEW_FILE = './量表/sub_20260319newest.csv'
LEDD_FILE = './量表/20260112_服药LEDD_Results.csv'
ANOVA_FILE = './analysis_results-new/ANOVA_F_Matrix.csv'
OUTPUT_FILE = './MIND_Longitudinal_Clean_Data.csv'

YEO_7_CONFIG = {
    'Visual': [15, 17, 19, 21, 23, 49, 51, 53, 55, 57],
    'Somatomotor': [20, 24, 25, 54, 58, 59],
    'Dorsal_Attention': [22, 26, 28, 56, 60, 62],
    'Ventral_Attention': [1, 10, 31, 35, 44, 65],
    'Limbic': [4, 27, 30, 38, 61, 64],
    'Frontoparietal': [2, 12, 16, 36, 46, 50],
    'Default': [3, 8, 11, 29, 37, 42, 45, 63]
}

def clean_id(s):
    """提取 ID 中的 subXXX 部分"""
    s = str(s).lower()
    match = re.search(r'sub\d+', s)
    return match.group(0) if match else s.strip()

def build_advanced_table():
    # 1. 加载显著边掩模 (ANOVA)
    print(">>> 正在加载显著边掩模...")
    sig_df = pd.read_csv(ANOVA_FILE, index_col=0)
    sig_mask = sig_df.values > 0
    upper_indices = np.triu_indices(68, k=1)
    sig_edge_indices = [i for i, val in enumerate(sig_mask[upper_indices]) if val]

    # 2. 提取影像特征并建立索引
    print(">>> 正在提取影像特征...")
    mind_dict = {}
    groups = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']
    for group in groups:
        path = os.path.join(MIND_ROOT, group)
        if not os.path.exists(path): continue
        for f in glob.glob(os.path.join(path, "*.csv")):
            raw_id = os.path.basename(f).split('_MIND')[0]
            std_id = clean_id(raw_id)
            matrix = pd.read_csv(f, index_col=0).values
            
            # 计算特征
            global_sig = np.mean(matrix[upper_indices][sig_edge_indices])
            net_vals = {}
            for net_name, nodes in YEO_7_CONFIG.items():
                n_idx = [n-1 for n in nodes if n-1 < 68]
                sub_mat = matrix[np.ix_(n_idx, n_idx)]
                sub_up = sub_mat[np.triu_indices(len(n_idx), k=1)]
                net_vals[f'MIND_{net_name}'] = np.mean(sub_up) if len(sub_up) > 0 else np.nan
            
            # 以标准 ID 为键存储特征
            mind_dict[std_id] = {
                'Original_SUB_ID': raw_id,
                'Group_MIND': group,
                'MIND_Sig_Index': global_sig,
                **net_vals
            }

    # 3. 处理映射表：建立 PATNO 到 SUB_ID 的映射
    print(">>> 正在建立 PATNO 映射...")
    df_saa = pd.read_csv(SAA_FILE, encoding='utf-8-sig')
    df_saa['MATCH_ID'] = df_saa['SUB_NO'].apply(clean_id)
    # 只保留那些在影像文件夹里真实存在的 ID
    df_saa = df_saa[df_saa['MATCH_ID'].isin(mind_dict.keys())]
    
    # 建立 PATNO -> MATCH_ID 的映射字典
    patno_to_sub = dict(zip(df_saa['PATNO'], df_saa['MATCH_ID']))
    patno_to_saa = dict(zip(df_saa['PATNO'], df_saa['SAA_Status']))

    # 4. 加载全量量表并筛选
    print(">>> 正在清洗全量随访量表...")
    df_scale = pd.read_csv(SCALE_NEW_FILE, low_memory=False, encoding='utf-8-sig')
    
    # 【关键步骤】：只保留那些有影像数据的病人
    df_scale = df_scale[df_scale['PATNO'].isin(patno_to_sub.keys())].copy()

    # 5. 合并数据
    final_rows = []
    # 预加载 LEDD 基线以备参考
    df_ledd = pd.read_csv(LEDD_FILE)
    df_ledd['STARTDT'] = pd.to_datetime(df_ledd['STARTDT'], errors='coerce')
    df_ledd_bl = df_ledd.sort_values(['PATNO', 'STARTDT']).groupby('PATNO').first().reset_index()

    for patno, group_df in df_scale.groupby('PATNO'):
        std_id = patno_to_sub[patno]
        m_feat = mind_dict[std_id]
        saa_stat = patno_to_saa[patno]
        
        # 获取该病人的基线 LEDD
        match_ledd = df_ledd_bl[df_ledd_bl['PATNO'] == patno]
        ledd_bl = match_ledd.iloc[0]['LEDD'] if not match_ledd.empty else 0

        for _, s_row in group_df.iterrows():
            # 过滤不需要的访问点，保留 V02 等随访
            if s_row['EVENT_ID'] not in ['BL', 'V02', 'V04', 'V06', 'V08', 'V10', 'V12']:
                continue

            res = {
                'PATNO': patno,
                'SUB_NO': std_id,
                'EVENT_ID': s_row['EVENT_ID'],
                'SAA_Status': saa_stat,
                'Age_at_Visit': s_row.get('AGE_AT_VISIT', np.nan),
                'Sex': s_row.get('SEX', np.nan),
                'Education': s_row.get('EDUCYRS', np.nan),
                'LEDD_Baseline': ledd_bl,
                'MoCA': s_row.get('MCATOT', np.nan),
                'UPDRS3': s_row.get('NP3TOT', np.nan)
            }
            # 将该病人的影像特征加入这一行
            res.update(m_feat)
            final_rows.append(res)

    # 6. 输出结果
    if not final_rows:
        print(" [!] 匹配后无有效数据。")
        return

    df_final = pd.DataFrame(final_rows)
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    print(f"\n>>> 任务成功完成！")
    print(f"最终生成的长表行数: {len(df_final)}")
    print(f"每个 PATNO 都对应了唯一的 SUB_NO。")
    print(f"包含随访点: {df_final['EVENT_ID'].unique()}")
    print(f"结果文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_advanced_table()
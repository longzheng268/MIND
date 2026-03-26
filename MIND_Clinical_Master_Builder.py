import os
import pandas as pd
import numpy as np
import glob

# --- 路径配置 ---
MIND_ROOT = './data/MIND-Networks_newgroup/'
SAA_FILE = './量表/患者编号和SAA状态.csv'
SCALE_FILE = './量表/患者量表数据和基本信息.csv'
ANOVA_FILE = './analysis_results-new/ANOVA_F_Matrix.csv'
OUTPUT_FILE = './MIND_Detailed_Network_Analysis_ver2.csv'

YEO_7_CONFIG = {
    'Visual': [15, 17, 19, 21, 23, 49, 51, 53, 55, 57],
    'Somatomotor': [20, 24, 25, 54, 58, 59],
    'Dorsal_Attention': [22, 26, 28, 56, 60, 62],
    'Ventral_Attention': [1, 10, 31, 35, 44, 65],
    'Limbic': [4, 27, 30, 38, 61, 64],
    'Frontoparietal': [2, 12, 16, 36, 46, 50],
    'Default': [3, 8, 11, 29, 37, 42, 45, 63]
}

def build_advanced_table():
    # 1. 加载显著边掩模
    print(">>> 正在加载显著边掩模...")
    sig_df = pd.read_csv(ANOVA_FILE, index_col=0)
    sig_mask = sig_df.values > 0
    upper_indices = np.triu_indices(68, k=1)
    
    sig_edge_indices = []
    idx_counter = 0
    for r in range(68):
        for c in range(r + 1, 68):
            if sig_mask[r, c]: sig_edge_indices.append(idx_counter)
            idx_counter += 1

    # 2. 遍历提取 MIND 特征
    print(">>> 正在从各组目录提取 7 大子网特征...")
    mind_records = []
    groups = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']
    
    for group in groups:
        path = os.path.join(MIND_ROOT, group)
        if not os.path.exists(path): continue
        for f in glob.glob(os.path.join(path, "*.csv")):
            subj_id = os.path.basename(f).split('_MIND')[0]
            matrix = pd.read_csv(f, index_col=0).values
            
            # 全脑显著指标
            global_sig = np.mean(matrix[upper_indices][sig_edge_indices])
            
            # 子网指标
            net_values = {}
            for net_name, nodes in YEO_7_CONFIG.items():
                nodes_0base = [n-1 for n in nodes if n-1 < 68]
                sub_matrix = matrix[np.ix_(nodes_0base, nodes_0base)]
                sub_upper = sub_matrix[np.triu_indices(len(nodes_0base), k=1)]
                net_values[f'MIND_{net_name}'] = np.mean(sub_upper) if len(sub_upper) > 0 else np.nan
            
            mind_records.append({
                'SUB_NO': subj_id,
                'Group_MIND': group,
                'MIND_Sig_Index': global_sig,
                **net_values
            })
            
    df_mind = pd.DataFrame(mind_records)

    # 3. 加载临床 CSV 数据
    print(">>> 正在加载临床 CSV 数据进行全量汇总...")
    df_saa = pd.read_csv(SAA_FILE, encoding='utf-8-sig') 
    df_scale = pd.read_csv(SCALE_FILE, low_memory=False, encoding='utf-8-sig')
    
    # 统一 ID 格式
    df_saa['SUB_NO_str'] = df_saa['SUB_NO'].astype(str).str.strip()
    df_mind['SUB_NO_str'] = df_mind['SUB_NO'].astype(str).str.strip()

    # 4. 融合逻辑
    print(">>> 正在执行全量字段对齐...")
    final_data = []
    
    for _, m_row in df_mind.iterrows():
        # A. 匹配 PATNO
        match_saa = df_saa[df_saa['SUB_NO_str'].apply(lambda x: x in m_row['SUB_NO_str'])]
        if match_saa.empty: continue
        
        patno = match_saa.iloc[0]['PATNO']
        saa_status_val = match_saa.iloc[0]['SAA_Status']
        
        # B. 匹配该 PATNO 下的所有量表行
        p_scales = df_scale[df_scale['PATNO'] == patno].copy()
        if p_scales.empty: continue
        
        # C. 提取基线/关键协变量 (从第一行有数据的行抓取)
        # 我们优先取 EVENT_ID 为 BL 或 SC 的行
        baseline_row = p_scales[p_scales['EVENT_ID'].isin(['BL', 'SC', 'V00'])]
        if baseline_row.empty:
            baseline_row = p_scales.iloc[0:1] # 如果没标BL，强行取第一条记录
        else:
            baseline_row = baseline_row.iloc[0:1]

        # 构建这一行的基础字典
        # 1. 基础人口学 (Age, Sex, Educ)
        res = {
            'PATNO': patno,
            'Group_MIND': m_row['Group_MIND'],
            'SAA_Status_Clinical': saa_status_val,
            'Age': baseline_row['AGE_AT_VISIT'].values[0],
            'Sex': baseline_row['SEX'].values[0],
            'Education': baseline_row['EDUCYRS'].values[0]
        }
        
        # 2. 存入 MIND 特征
        res.update(m_row.to_dict())
        
        # 3. 纵向得分平铺 (针对重要的 MoCA 和 UPDRS)
        for _, s_row in p_scales.iterrows():
            ev = s_row['EVENT_ID']
            if ev in ['BL', 'V04', 'V06', 'V08', 'V10']:
                res[f'{ev}_UPDRS3'] = s_row.get('NP3TOT', np.nan)
                res[f'{ev}_MoCA'] = s_row.get('MCATOT', np.nan)
        
        # 4. 全量字段合并 (把 baseline_row 里的所有原始列都塞进去，前缀加 Raw_)
        # 这样你以后想分析任何一个字段都能直接在表里找到
        raw_info = baseline_row.to_dict(orient='records')[0]
        for k, v in raw_info.items():
            if k not in res: # 避免重复
                res[f'Raw_{k}'] = v
        
        final_data.append(res)

    # 5. 生成最终 CSV
    df_final = pd.DataFrame(final_data)
    
    # 补齐协变量缺失 (防止某些被试 baseline 没记)
    for col in ['Age', 'Sex', 'Education']:
        df_final[col] = df_final.groupby('PATNO')[col].transform('first')

    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"\n>>> 终极融合任务完成！")
    print(f"样本总数: {len(df_final)}")
    print(f"表格列数: {len(df_final.columns)} (包含所有临床原始字段)")
    print(f"已生成文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_advanced_table()
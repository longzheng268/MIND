import os
import pandas as pd
import numpy as np
import glob

# --- 路径配置 ---
MIND_ROOT = './data/MIND-Networks_newgroup/'
SAA_FILE = './量表/患者编号和SAA状态.xlsx'
SCALE_FILE = './量表/患者量表数据和基本信息.xlsx'
ANOVA_FILE = './analysis_results-new/ANOVA_F_Matrix.csv'
OUTPUT_FILE = './MIND_Detailed_Network_Analysis.csv'

# --- 1. 定义 DK68 到 Yeo 7 网络的标准映射 (基于解剖位置索引) ---
# 注意：DK68 矩阵通常左脑 34 个区在前，右脑 34 个区在后。
# 以下是根据脑图谱定义的常用索引分类
YEO_7_CONFIG = {
    'Visual': [15, 17, 19, 21, 23, 49, 51, 53, 55, 57], # 枕叶、舌回等
    'Somatomotor': [20, 24, 25, 54, 58, 59], # 中央前后回、旁中央小叶
    'Dorsal_Attention': [22, 26, 28, 56, 60, 62], # 上顶叶、额叶眼动区
    'Ventral_Attention': [1, 10, 31, 35, 44, 65], # 岛叶、带状回
    'Limbic': [4, 27, 30, 38, 61, 64], # 内嗅、颞极、旁海马
    'Frontoparietal': [2, 12, 16, 36, 46, 50], # 额中回、外侧前额叶
    'Default': [3, 8, 11, 29, 37, 42, 45, 63] # 后扣带、内侧前额叶、海马
}

def build_advanced_table():
    # 1. 加载 924 条显著边掩模
    print(">>> 正在加载 924 条显著边掩模...")
    sig_df = pd.read_csv(ANOVA_FILE, index_col=0)
    roi_names = sig_df.columns.tolist()
    sig_mask = sig_df.values > 0
    upper_indices = np.triu_indices(68, k=1)
    
    # 预计算显著边在扁平化向量中的位置
    sig_edge_indices = []
    idx_counter = 0
    for r in range(68):
        for c in range(r + 1, 68):
            if sig_mask[r, c]: sig_edge_indices.append(idx_counter)
            idx_counter += 1

    # 2. 提取特征
    print(">>> 正在提取 7 大功能子网特征...")
    mind_list = []
    groups = ['HC', 'prodromal_SAA-', 'prodromal_SAA+', 'PD_SAA+']
    
    for group in groups:
        path = os.path.join(MIND_ROOT, group)
        if not os.path.exists(path): continue
        for f in glob.glob(os.path.join(path, "*.csv")):
            subj_id = os.path.basename(f).split('_MIND')[0]
            matrix_df = pd.read_csv(f, index_col=0)
            matrix = matrix_df.values
            
            # A. 计算全脑显著平均值
            flat = matrix[upper_indices]
            global_sig = np.mean(flat[sig_edge_indices])
            
            # B. 计算各子网内部平均值 (只算子网内部节点之间的连边)
            net_values = {}
            for net_name, nodes in YEO_7_CONFIG.items():
                # 调整为 0-based 索引
                nodes_0base = [n-1 for n in nodes if n-1 < 68]
                if not nodes_0base:
                    net_values[f'MIND_{net_name}'] = np.nan
                    continue
                # 提取子矩阵
                sub_matrix = matrix[np.ix_(nodes_0base, nodes_0base)]
                # 只取子矩阵的上三角（不含对角线）
                sub_upper = sub_matrix[np.triu_indices(len(nodes_0base), k=1)]
                net_values[f'MIND_{net_name}'] = np.mean(sub_upper) if len(sub_upper) > 0 else np.nan
            
            res_row = {
                'sub编号': subj_id,
                'Group_MIND': group,
                'MIND_Sig_Index': global_sig,
                **net_values
            }
            mind_list.append(res_row)
            
    df_mind = pd.DataFrame(mind_list)

    # 3. 关联临床量表 (复用你之前的逻辑)
    print(">>> 正在关联量表与 SAA 状态...")
    df_saa = pd.read_excel(SAA_FILE, engine='openpyxl')
    df_saa['编号_str'] = df_saa['编号'].astype(str).str.strip()
    df_scale = pd.read_excel(SCALE_FILE, engine='openpyxl')
    
    final_rows = []
    for _, m_row in df_mind.iterrows():
        match_saa = df_saa[df_saa['编号_str'].apply(lambda x: x in m_row['sub编号'])]
        if match_saa.empty: continue
        
        patno = match_saa.iloc[0]['PATNO']
        base_info = {
            'PATNO': patno,
            'SAA_Status': match_saa.iloc[0]['SAA_Status'],
            **m_row.to_dict()
        }
        
        # 提取 longitudinal 量表
        p_scales = df_scale[df_scale['PATNO'] == patno]
        for _, s_row in p_scales.iterrows():
            ev = s_row['EVENT_ID']
            if ev in ['BL', 'V04', 'V06']:
                base_info[f'{ev}_UPDRS3'] = s_row.get('NP3TOT', np.nan)
                base_info[f'{ev}_MoCA'] = s_row.get('MCATOT', np.nan)
        
        final_rows.append(base_info)

    df_final = pd.DataFrame(final_rows)
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"\n>>> 任务完成！生成了包含 7 大子网的终极表：{OUTPUT_FILE}")
    print(f"新增列：{list(YEO_7_CONFIG.keys())}")

if __name__ == "__main__":
    build_advanced_table()
import pandas as pd
import numpy as np
import pingouin as pg

# 1. 加载数据
df = pd.read_csv('./scale/MIND_baseline_with_followup_V04_V12.csv')

# --- 自动列名修正 ---
# 检查是否存在 Age 相关的列
all_cols = df.columns.tolist()
age_col = None
for candidate in ['BL_Age', 'Age', 'AGE_AT_VISIT', 'V00_Age']:
    if candidate in all_cols:
        age_col = candidate
        break

if not age_col:
    print(f" [!] 错误：在表格中找不到年龄列。当前列名有：{all_cols[:10]}...")
    # 如果实在找不到，我们先跳过协变量，只做单因素 ANOVA
    covariates = []
    print(" >>> 警告：未发现年龄列，将回退到普通单因素 ANOVA 检验。")
else:
    covariates = [age_col]
    print(f" >>> 检测到年龄列: {age_col}，将作为协变量进行 ANCOVA。")

networks = ['Visual', 'Somatomotor', 'Dorsal_Attention', 'Ventral_Attention', 'Limbic', 'Frontoparietal', 'Default']
results = []

# 2. 统计检验
for net in networks:
    col_name = f'MIND_{net}'
    if col_name not in df.columns:
        continue
        
    temp_df = df.dropna(subset=[col_name] + covariates).copy()
    
    if len(covariates) > 0:
        # ANCOVA
        aov = pg.ancova(data=temp_df, dv=col_name, covar=covariates, between='Group_MIND')
        p_unc = aov.loc[aov['Source'] == 'Group_MIND', 'p-unc'].values[0]
        f_val = aov.loc[aov['Source'] == 'Group_MIND', 'F'].values[0]
    else:
        # 普通 ANOVA
        aov = pg.anova(data=temp_df, dv=col_name, between='Group_MIND')
        p_unc = aov.loc[aov['Source'] == 'Group_MIND', 'p-unc'].values[0]
        f_val = aov.loc[aov['Source'] == 'Group_MIND', 'F'].values[0]
    
    results.append({
        'Network': net,
        'F_value': f_val,
        'P_uncorrected': p_unc
    })

# 3. FDR 校正
res_df = pd.DataFrame(results)
if not res_df.empty:
    # 使用 Benjamini-Hochberg 校正
    _, p_fdr = pg.multicomp(res_df['P_uncorrected'].values, method='fdr_bh')
    res_df['P_FDR'] = p_fdr

    print("\n=== ANCOVA/ANOVA 统计结果汇总 ===")
    print(res_df.sort_values('P_FDR').to_string(index=False))

    # 4. 事后检验 (只针对 FDR < 0.05 的网络)
    sig_nets = res_df[res_df['P_FDR'] < 0.05]['Network'].tolist()
    if sig_nets:
        print(f"\n>>> 发现 {len(sig_nets)} 个显著网络，执行事后两两比较 (Tukey-HSD)...")
        for net in sig_nets:
            col_name = f'MIND_{net}'
            # 事后检验不带协变量，看组间直接差异
            posthoc = pg.pairwise_tukey(data=df, dv=col_name, between='Group_MIND')
            print(f"\n--- {net} 网络对比结果 ---")
            # 过滤出显著的两两比较
            print(posthoc[posthoc['p-tukey'] < 0.05][['A', 'B', 'mean(A)', 'mean(B)', 'diff', 'p-tukey']])
    else:
        print("\n [!] 没有网络通过 FDR 校正。")
else:
    print(" [!] 未提取到任何网络数据。")
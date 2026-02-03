import pandas as pd
import matplotlib.pyplot as plt

# 加载 DataFrame
# df = pd.read_pickle('D:/Linux/rootfs/home/HCResult/sub1/MIND.pkl')
# df = pd.read_pickle('D:/Linux/rootfs/home/HCResult/demo1dcmnii/MIND.pkl')
df = pd.read_pickle('.//data//HCResult//sub1//MIND.pkl')

# 绘制彩色矩阵
plt.imshow(df, cmap='viridis', interpolation='nearest')
plt.colorbar()
# plt.xticks(range(len(df.columns)), df.columns, rotation=90)
# plt.yticks(range(len(df.index)), df.index)
plt.xlabel('Regions')
plt.ylabel('Regions')
plt.title('MIND network')

# 保存图片
plt.savefig('similarity_matrix.png')

# 显示图像（可选）
plt.show()

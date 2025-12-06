import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.gridspec as gridspec

# 设置绘图风格
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.facecolor'] = '#f9f9f9'
plt.rcParams['axes.facecolor'] = '#f9f9f9'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.color'] = '#dddddd'
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['legend.frameon'] = True
plt.rcParams['legend.framealpha'] = 0.8
plt.rcParams['legend.edgecolor'] = '#dddddd'

# 创建自定义颜色映射
colors = ['#5975a4', '#5f9e6e', '#b55d60', '#857aab', '#8a7c64', '#6d9cab']
custom_palette = sns.color_palette(colors)
sns.set_palette(custom_palette)

# 创建图表目录
charts_dir = 'data/charts'
os.makedirs(charts_dir, exist_ok=True)

# 辅助函数：转换NumPy类型为Python原生类型
def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    else:
        return obj

# 读取CSV文件
try:
    df = pd.read_csv('data/input.csv')
    print(f"成功读取CSV文件，共{len(df)}行，{len(df.columns)}列")
    print(f"列名: {', '.join(df.columns)}")
except Exception as e:
    print(f"读取CSV文件失败: {str(e)}")
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump({"error": f"读取CSV文件失败: {str(e)}"}, f, ensure_ascii=False)
    exit(1)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 设置matplotlib默认字体为英文
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 加载数据
data_path = 'data/input.csv'
df = pd.read_csv(data_path)

# 数据预处理
# 假设所有数值列都是浮点数，进行类型转换
for col in ['销售额', '利润', '成本']:
    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, (int, float)) else np.nan)

# 删除包含NaN的行
df.dropna(inplace=True)

# 数据分析
total_sales = df['销售额'].sum()
average_profit = df['利润'].mean()

# 可视化设置
sns.set(style="whitegrid", palette="muted")

# 生成图表并保存到指定目录
charts_dir = 'data/charts/'
plt.figure(figsize=(10, 6))

# 销售额分布图
sns.histplot(df['销售额'], kde=True)
plt.title('Sales Distribution')
plt.xlabel('Sales')
plt.ylabel('Frequency')
plt.savefig(f'{charts_dir}sales_distribution.png')

# 利润与成本的关系图
plt.figure(figsize=(10, 6))
sns.scatterplot(x='成本', y='利润', data=df)
plt.title('Profit vs Cost')
plt.xlabel('Cost')
plt.ylabel('Profit')
plt.savefig(f'{charts_dir}profit_vs_cost.png')

# 数据结果保存到JSON文件
result = {
    'total_sales': total_sales,
    'average_profit': average_profit
}
with open('data/result.json', 'w') as f:
    json.dump(result, f)

print("Analysis completed. Results saved to data/result.json and charts saved to data/charts/")


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

# 加载数据
data = pd.read_csv('data/input.csv')

# 数据预览
print(data.head())

# 数据清洗：假设销售额、利润和成本列都是数值型，这里进行简单的类型转换检查
numeric_columns = ['销售额', '利润', '成本']
for column in numeric_columns:
    data[column] = pd.to_numeric(data[column], errors='coerce')

# 保存结果到JSON文件
data.to_json('data/result.json', orient='records', force_ascii=True)

# 设置图表风格和默认字体
sns.set(style="whitegrid")

# 创建目录以存储图表
import os
if not os.path.exists('data/charts/'):
    os.makedirs('data/charts/')

# 可视化销售额分布
plt.figure(figsize=(10, 6))
sns.histplot(data['销售额'], kde=True)
plt.title('Sales Distribution')
plt.xlabel('Sales')
plt.ylabel('Frequency')
plt.savefig('data/charts/sales_distribution.png', bbox_inches='tight')

# 可视化利润和成本的关系
plt.figure(figsize=(10, 6))
sns.scatterplot(x='成本', y='利润', data=data)
plt.title('Cost vs Profit')
plt.xlabel('Cost')
plt.ylabel('Profit')
plt.savefig('data/charts/cost_vs_profit.png', bbox_inches='tight')

# 可视化每个地区的销售额
plt.figure(figsize=(10, 6))
sns.barplot(x='地区', y='销售额', data=data)
plt.title('Sales by Region')
plt.xlabel('Region')
plt.ylabel('Sales')
plt.savefig('data/charts/sales_by_region.png', bbox_inches='tight')

# 显示图表（如果需要）
plt.show()

# 确保所有输出都是英文或ASCII字符
print("Data analysis and visualization completed.")


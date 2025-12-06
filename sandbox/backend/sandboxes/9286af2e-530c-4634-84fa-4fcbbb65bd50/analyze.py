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
from matplotlib.ticker import FuncFormatter

# 加载数据
data = pd.read_csv('data/input.csv')

# 数据预处理
# 假设需要对销售额、利润和成本进行一些基本的清洗操作，例如去除空值等
data.dropna(inplace=True)

# 分析与可视化
# 设置图表样式
sns.set(style="whitegrid")

# 销售额分布
plt.figure(figsize=(10, 6))
sns.histplot(data['销售额'], kde=True)
plt.title('Sales Distribution')
plt.xlabel('Sales Amount')
plt.ylabel('Frequency')
plt.savefig('data/charts/sales_distribution.png')

# 利润与成本的关系
plt.figure(figsize=(10, 6))
sns.scatterplot(x='利润', y='成本', data=data)
plt.title('Profit vs Cost')
plt.xlabel('Profit')
plt.ylabel('Cost')
plt.savefig('data/charts/profit_vs_cost.png')

# 成本占比分析
total_cost = data['成本'].sum()
cost_percentage = (data['成本'] / total_cost) * 100
data['成本百分比'] = cost_percentage

plt.figure(figsize=(10, 6))
sns.barplot(x='地区', y='成本百分比', data=data)
plt.title('Cost Percentage by Region')
plt.xlabel('Region')
plt.ylabel('Percentage of Total Cost (%)')
plt.savefig('data/charts/cost_percentage_by_region.png')

# 结果保存
result = {
    'average_sales': float(data['销售额'].mean()),
    'max_profit': float(data['利润'].max()),
    'min_cost': float(data['成本'].min())
}

with open('data/result.json', 'w') as f:
    json.dump(result, f)

# 显示结果
print("Average Sales: ", result['average_sales'])
print("Max Profit: ", result['max_profit'])
print("Min Cost: ", result['min_cost'])

plt.show()


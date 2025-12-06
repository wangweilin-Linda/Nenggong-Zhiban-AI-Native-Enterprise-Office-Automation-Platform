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

# 设置matplotlib默认字体为英文或ASCII字符
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']

# 读取CSV文件
df = pd.read_csv('data/input.csv')

# 数据预处理
# 假设数据列名为'地区', '销售额', '利润', '成本'
# 将非数值转换为NaN并填充缺失值
df['销售额'] = df['销售额'].replace(r'^\s*$', np.nan, regex=True).astype(float)
df['利润'] = df['利润'].replace(r'^\s*$', np.nan, regex=True).astype(float)
df['成本'] = df['成本'].replace(r'^\s*$', np.nan, regex=True).astype(float)

# 删除包含缺失值的行
df.dropna(inplace=True)

# 数据分析和可视化
# 计算总销售额、利润和成本
total_sales = df['销售额'].sum()
total_profit = df['利润'].sum()
total_cost = df['成本'].sum()

print(f"Total Sales: {total_sales}")
print(f"Total Profit: {total_profit}")
print(f"Total Cost: {total_cost}")

# 利润与销售额的关系
sns.scatterplot(x='销售额', y='利润', data=df)
plt.title('Sales vs. Profit')
plt.xlabel('Sales')
plt.ylabel('Profit')
plt.savefig('data/charts/sales_vs_profit.png')

# 成本与销售额的关系
sns.scatterplot(x='销售额', y='成本', data=df)
plt.title('Sales vs. Cost')
plt.xlabel('Sales')
plt.ylabel('Cost')
plt.savefig('data/charts/sales_vs_cost.png')

# 保存结果到JSON文件
result = {
    'total_sales': total_sales,
    'total_profit': total_profit,
    'total_cost': total_cost
}
with open('data/result.json', 'w') as f:
    json.dump(result, f)

print("Analysis completed. Results saved to data/result.json and charts saved to data/charts/")


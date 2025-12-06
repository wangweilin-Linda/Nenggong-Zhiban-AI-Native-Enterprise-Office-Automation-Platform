
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.gridspec as gridspec

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 设置更好看的图表样式
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

# 读取数据
df = pd.read_csv('data/input.csv')

# 数据预处理，确保销售额为数值型
df['销售额'] = df['销售额'].astype(float)

# 找出销售额最高的前三个地区
top_three_regions = df.nlargest(3, '销售额')[['地区', '销售额']].reset_index(drop=True)
top_three_regions.to_json('data/result.json', orient='records')

# 可视化
plt.figure(figsize=(12, 8))
sns.barplot(x='地区', y='销售额', data=top_three_regions, palette='viridis')
plt.title('销售额最高的前三个地区', fontsize=16, fontweight='bold')
plt.xlabel('地区')
plt.ylabel('销售额')
plt.grid(True)
plt.tight_layout()
plt.savefig('data/charts/top_three_regions_sales.png')

# 显示图表
plt.show()
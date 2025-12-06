
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

# 设置图表保存路径
charts_dir = 'data/charts/'

# 读取CSV文件
df = pd.read_csv('data/input.csv')

# 数据预处理
# 假设数据中存在缺失值，这里进行简单的填充或删除操作。
df.dropna(inplace=True)

# 计算利润率
df['利润率'] = (df['利润'] / df['销售额']) * 100

# 分析和可视化
plt.figure(figsize=(12, 6))

# 利润率的箱形图
sns.boxplot(x='地区', y='利润率', data=df)
plt.title('各地区的利润率分布')
plt.xlabel('地区')
plt.ylabel('利润率 (%)')
plt.savefig(f'{charts_dir}利润率分布.png')

# 销售额柱状图
df.groupby('地区')['销售额'].sum().sort_values(ascending=False).plot(kind='bar', color=sns.color_palette("Blues"))
plt.title('各地区的销售额')
plt.xlabel('地区')
plt.ylabel('销售额')
plt.xticks(rotation=45)
plt.savefig(f'{charts_dir}销售额分布.png')

# 成本与利润的关系图
sns.scatterplot(x='成本', y='利润', hue='地区', data=df, palette="viridis")
plt.title('成本与利润关系图')
plt.xlabel('成本')
plt.ylabel('利润')
plt.legend(title='地区')
plt.savefig(f'{charts_dir}成本与利润.png')

# 保存结果到JSON文件
result = df.to_dict(orient='records')
with open('data/result.json', 'w') as f:
    import json
    json.dump(result, f)

print("数据处理和可视化完成！")
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
from datetime import datetime

# 设置matplotlib默认字体为英文
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def load_data(file_path):
    """ 加载数据 """
    data = pd.read_csv(file_path)
    return data

def analyze_data(data):
    """ 分析数据 """
    summary_stats = {
        'mean_sales': float(np.mean(data['销售额'])),
        'median_profit': float(np.median(data['利润'])),
        'total_cost': float(np.sum(data['成本']))
    }

    # 计算每个地区的总销售额、平均利润和总成本
    grouped_data = data.groupby('地区').agg({
        '销售额': ['sum', 'mean'],
        '利润': ['sum'],
        '成本': ['sum']
    }).reset_index()
    grouped_data.columns = ['地区', '总销售额', '平均销售额', '总利润', '总成本']

    return summary_stats, grouped_data

def visualize_data(data):
    """ 可视化数据 """
    # 创建图表目录
    charts_dir = 'data/charts/'
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)

    # 销售额分布图
    plt.figure(figsize=(10, 6))
    sns.histplot(data['销售额'], kde=True)
    plt.title('Sales Distribution')
    plt.xlabel('Sales Amount')
    plt.ylabel('Frequency')
    plt.savefig(f'{charts_dir}sales_distribution.png')

    # 利润与成本关系图
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='利润', y='成本', data=data)
    plt.title('Profit vs Cost')
    plt.xlabel('Profit')
    plt.ylabel('Cost')
    plt.savefig(f'{charts_dir}profit_vs_cost.png')

def save_results(summary_stats, grouped_data):
    """ 保存结果到JSON文件 """
    result = {
        'summary_statistics': summary_stats,
        'grouped_data': grouped_data.to_dict(orient='records')
    }

    with open('data/result.json', 'w') as f:
        json.dump(result, f)

if __name__ == '__main__':
    # 加载数据
    data = load_data('data/input.csv')

    # 数据分析
    summary_stats, grouped_data = analyze_data(data)

    # 可视化
    visualize_data(data)

    # 保存结果
    save_results(summary_stats, grouped_data)


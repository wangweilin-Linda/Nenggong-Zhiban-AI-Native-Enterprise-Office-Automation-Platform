
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 创建图表目录
charts_dir = 'data/charts'
os.makedirs(charts_dir, exist_ok=True)

# 读取CSV文件
try:
    df = pd.read_csv('data/input.csv')
    print(f"成功读取CSV文件，共{len(df)}行，{len(df.columns)}列")
except Exception as e:
    print(f"读取CSV文件失败: {str(e)}")
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump({"error": f"读取CSV文件失败: {str(e)}"}, f, ensure_ascii=False)
    exit(1)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json

# 读取数据
data = pd.read_csv('data/input.csv')

# 检查数据列名，确保存在用于绘图的列
if 'date' in data.columns and 'value' in data.columns:
    # 数据摘要
    summary = {
        "summary": {
            "total_rows": len(data),
            "unique_dates": data['date'].nunique(),
            "mean_value": data['value'].mean()
        }
    }

    # 绘制折线图
    plt.figure(figsize=(10, 6))
    sns.lineplot(x='date', y='value', data=data)
    plt.title('Line Chart of Value Over Time')
    plt.xlabel('Date')
    plt.ylabel('Value')
    chart_path = 'data/charts/line_chart.png'
    plt.savefig(chart_path)

    # 将结果保存为JSON
    result = {
        "summary": summary,
        "chart_path": chart_path
    }
    with open('data/result.json', 'w') as f:
        json.dump(result, f)
else:
    print("数据中缺少必要的列：'date' 或 'value'")
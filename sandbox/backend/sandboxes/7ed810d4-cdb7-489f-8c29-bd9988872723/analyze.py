
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

# 读取数据
data = pd.read_csv('data/input.csv')

# 检查数据摘要
summary = data.describe().to_dict()

# 绘制折线图
plt.figure(figsize=(10, 6))
for column in data.columns:
    plt.plot(data.index, data[column], label=column)
plt.title('Line Chart of Data')
plt.xlabel('Index')
plt.ylabel('Value')
plt.legend()
chart_path = 'data/charts/line_chart.png'
plt.savefig(chart_path)

# 准备结果数据
result_data = {
    "summary": summary,
    "key_findings": "This chart shows the trend of each column in the dataset.",
    "charts": [chart_path]
}

# 保存结果到JSON文件
import json
with open('data/result.json', 'w') as f:
    json.dump(result_data, f)
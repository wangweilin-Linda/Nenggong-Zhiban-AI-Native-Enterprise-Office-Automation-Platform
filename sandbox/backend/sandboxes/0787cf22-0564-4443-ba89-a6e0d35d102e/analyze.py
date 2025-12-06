import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import re
from pathlib import Path

# 设置matplotlib避免字体问题
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

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
    
    # 识别列类型
    column_types = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            column_types[col] = 'numeric'
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            column_types[col] = 'datetime'
        else:
            column_types[col] = 'categorical'
            
    # 打印列类型信息供参考
    print("\n列类型信息:")
    for col, col_type in column_types.items():
        print(f"  {col}: {col_type}")
        
except Exception as e:
    print(f"读取CSV文件失败: {str(e)}")
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump({"error": f"读取CSV文件失败: {str(e)}"}, f, ensure_ascii=False)
    exit(1)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json

# 加载数据
df = pd.read_csv('data/input.csv')

# 显示所有列名供用户选择
print(df.columns)

# 假设用户选择了以下列名
selected_columns = ['地区', '销售额', '利润', '成本']

# 筛选所需列
df = df[selected_columns]

# 计算每个地区的总销售额、总利润和平均成本
region_summary = df.groupby('地区').agg({
    '销售额': 'sum',
    '利润': 'sum',
    '成本': 'mean'
}).reset_index()

# 保存结果到JSON文件
with open('data/result.json', 'w') as f:
    json.dump(region_summary.to_dict(orient='records'), f, ensure_ascii=False)

# 可视化每个地区的总销售额和利润
plt.figure(figsize=(10, 6))
sns.barplot(x='地区', y='销售额', data=region_summary)
plt.title('Total Sales by Region')
plt.savefig('data/charts/total_sales_by_region.png')

plt.figure(figsize=(10, 6))
sns.barplot(x='地区', y='利润', data=region_summary)
plt.title('Total Profit by Region')
plt.savefig('data/charts/total_profit_by_region.png')

# 结果总结
message = "分析了每个地区的总销售额和总利润，以及平均成本。"
print(message)

# 保存结果到JSON文件
try:
    # 确保result变量存在
    if 'result' not in locals() and 'result' not in globals():
        result = {"error": "分析代码未定义result变量", "message": "分析过程中出现错误"}
    
    # 转换NumPy类型为Python原生类型
    result = convert_numpy_types(result)
    
    # 保存结果
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("分析完成，结果已保存到result.json")
except Exception as e:
    print(f"保存结果失败: {str(e)}")
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump({"error": f"保存结果失败: {str(e)}", "message": "分析过程中出现错误"}, f, ensure_ascii=False)

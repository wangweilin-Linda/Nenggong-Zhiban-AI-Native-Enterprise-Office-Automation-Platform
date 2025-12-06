
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 读取CSV文件
try:
    df = pd.read_csv('data/input.csv')
    print(f"成功读取CSV文件，共{len(df)}行，{len(df.columns)}列")
except Exception as e:
    print(f"读取CSV文件失败: {str(e)}")
    exit(1)

# 创建图表目录
charts_dir = 'data/charts'
os.makedirs(charts_dir, exist_ok=True)

# 基础统计分析
result = {
    "row_count": len(df),
    "column_count": len(df.columns),
    "columns": df.columns.tolist(),
    "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
    "categorical_columns": df.select_dtypes(include=['object']).columns.tolist(),
    "summary": {},
    "charts": []
}

# 计算数值列的统计信息
for col in result["numeric_columns"]:
    result["summary"][col] = {
        "mean": float(df[col].mean()),
        "median": float(df[col].median()),
        "std": float(df[col].std()),
        "min": float(df[col].min()),
        "max": float(df[col].max())
    }

# 生成图表
for col in result["numeric_columns"]:
    try:
        # 直方图
        plt.figure(figsize=(10, 6))
        sns.histplot(data=df, x=col)
        plt.title(f'{col}分布直方图')
        plt.tight_layout()
        
        chart_path = f'charts/{col}_hist.png'
        plt.savefig(f'data/{chart_path}')
        plt.close()
        result["charts"].append(chart_path)
        
        # 箱线图
        plt.figure(figsize=(10, 6))
        sns.boxplot(x=df[col])
        plt.title(f'{col}箱线图')
        plt.tight_layout()
        
        chart_path = f'charts/{col}_box.png'
        plt.savefig(f'data/{chart_path}')
        plt.close()
        result["charts"].append(chart_path)
    except Exception as e:
        print(f"生成{col}图表失败: {str(e)}")

# 保存结果
with open('data/result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    
print("分析完成，结果已保存到result.json")

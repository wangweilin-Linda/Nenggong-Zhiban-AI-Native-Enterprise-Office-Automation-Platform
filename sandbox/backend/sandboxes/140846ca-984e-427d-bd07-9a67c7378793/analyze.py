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
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from os import path

# 检查文件是否存在
if not path.exists('data/input.csv'):
    print("文件不存在，请检查路径")
else:
    # 读取数据
    df = pd.read_csv('data/input.csv')

    # 打印所有列名供用户选择
    print(df.columns)

    # 假设用户选择了以下列名
    selected_columns = ['地区', '销售额', '利润', '成本']

    # 确保所选列存在于数据集中
    if all(col in df.columns for col in selected_columns):
        result = {}

        # 数据分析部分
        sales_profit_ratio = (df['利润'] / df['销售额']).mean()
        cost_sales_ratio = (df['成本'] / df['销售额']).mean()
        regions = df['地区'].unique()

        # 结果汇总
        result['message'] = f"平均销售利润率：{sales_profit_ratio:.2f}, 平均成本率：{cost_sales_ratio:.2f}"
        for region in regions:
            region_data = df[df['地区'] == region]
            sales_region_mean = region_data['销售额'].mean()
            profit_region_mean = region_data['利润'].mean()
            cost_region_mean = region_data['成本'].mean()
            result[f'{region}的销售、利润和成本平均值'] = {
                '销售额': sales_region_mean,
                '利润': profit_region_mean,
                '成本': cost_region_mean
            }

        # 可视化部分（如果需要）
        plt.figure(figsize=(10, 6))
        sns.barplot(x=regions, y=[sales_profit_ratio] * len(regions), color='skyblue', label='销售利润率')
        sns.barplot(x=regions, y=[cost_sales_ratio] * len(regions), color='lightgreen', label='成本率')
        plt.xlabel('地区')
        plt.ylabel('比率')
        plt.title('各地区的销售利润率和成本率')
        plt.legend()
        plt.savefig('data/charts/sales_profit_cost_ratios.png')

        # 保存结果到json文件
        import json
        with open('data/result.json', 'w') as f:
            json.dump(result, f)
    else:
        print("所选列不存在于数据集中，请检查列名")

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

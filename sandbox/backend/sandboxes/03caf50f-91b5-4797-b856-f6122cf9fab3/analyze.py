
import pandas as pd
import numpy as np
import json
import os

# 读取CSV文件
try:
    df = pd.read_csv('data/input.csv')
    print(f"成功读取CSV文件，共{len(df)}行，{len(df.columns)}列")
    print(f"列名: {', '.join(df.columns)}")
except Exception as e:
    print(f"读取CSV文件失败: {str(e)}")
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump({"error": f"读取CSV文件失败: {str(e)}", "message": "无法读取数据文件"}, f, ensure_ascii=False)
    exit(1)

# 用户需求: "分析这个csv文件并生成图表"
result = {
    "数据预览": df.head(5).to_dict(orient='records'),
    "列统计": {},
    "message": "已分析您的数据"
}

# 对相关列进行简单统计
requested_columns = [col.strip() for col in "地区,销售额,利润,成本".split(',') if col.strip()]
analyzed_columns = []

for col in requested_columns:
    if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
        result["列统计"][col] = {
            "总和": float(df[col].sum()),
            "平均值": float(df[col].mean()),
            "最大值": float(df[col].max()),
            "最小值": float(df[col].min())
        }
        analyzed_columns.append(col)
        result["message"] += f"，{col}总计: {float(df[col].sum()):.2f}"

# 保存结果
with open('data/result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"分析完成，已分析{len(analyzed_columns)}个列")


import pandas as pd
import numpy as np
import json
import os
from scipy import stats

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

# 基础统计分析
result = {
    "row_count": len(df),
    "column_count": len(df.columns),
    "columns": df.columns.tolist(),
    "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
    "categorical_columns": df.select_dtypes(include=['object']).columns.tolist(),
    "summary": {},
    "visualization_data": {}
}

# 计算数值列的统计信息
for col in result["numeric_columns"]:
    data = df[col].dropna()
    
    # 基础统计信息
    basic_stats = {
        "mean": float(data.mean()),
        "median": float(data.median()),
        "std": float(data.std()),
        "min": float(data.min()),
        "max": float(data.max()),
        "q1": float(data.quantile(0.25)),
        "q3": float(data.quantile(0.75)),
        "iqr": float(data.quantile(0.75) - data.quantile(0.25)),
        "count": int(data.count()),
        "missing": int(df[col].isna().sum())
    }
    
    # 添加更多高级统计信息
    try:
        basic_stats["skewness"] = float(data.skew())
        basic_stats["kurtosis"] = float(data.kurtosis())
        # 检查是否为正态分布
        if len(data) > 8:
            shapiro_test = stats.shapiro(data.sample(min(len(data), 5000)))
            basic_stats["normality_test"] = {
                "test": "shapiro",
                "statistic": float(shapiro_test[0]),
                "p_value": float(shapiro_test[1]),
                "is_normal": shapiro_test[1] > 0.05
            }
    except:
        # 如果高级统计计算失败，忽略错误继续
        pass
    
    result["summary"][col] = basic_stats
    
    # 为前端可视化准备数据
    try:
        # 直方图数据
        hist_data = np.histogram(data, bins=min(30, len(data)//10 + 5))
        result["visualization_data"][col] = {
            "histogram": {
                "bins": hist_data[1].tolist(),
                "frequencies": hist_data[0].tolist(),
            },
            "boxplot": {
                "min": float(data.min()),
                "q1": float(data.quantile(0.25)),
                "median": float(data.median()),
                "q3": float(data.quantile(0.75)),
                "max": float(data.max()),
                "outliers": data[(data < data.quantile(0.25) - 1.5 * (data.quantile(0.75) - data.quantile(0.25))) | 
                                (data > data.quantile(0.75) + 1.5 * (data.quantile(0.75) - data.quantile(0.25)))].tolist()
            },
            "scatter": {
                "values": data.tolist()
            },
            "trend": {
                "values": sorted(data.tolist())
            },
            "descriptions": {
                "histogram": f"平均值: {basic_stats['mean']:.2f}, 中位数: {basic_stats['median']:.2f}, 标准差: {basic_stats['std']:.2f}",
                "boxplot": f"Q1: {basic_stats['q1']:.2f}, 中位数: {basic_stats['median']:.2f}, Q3: {basic_stats['q3']:.2f}, IQR: {basic_stats['iqr']:.2f}",
                "scatter": f"数据范围: {basic_stats['min']:.2f} 到 {basic_stats['max']:.2f}, 变异系数: {basic_stats['std']/basic_stats['mean']:.2f}",
                "trend": f"最小值: {basic_stats['min']:.2f}, 最大值: {basic_stats['max']:.2f}, 变化率: {(basic_stats['max']-basic_stats['min'])/basic_stats['mean']:.2f}",
                "summary": f"{col}的数据分布呈现{'正偏' if basic_stats.get('skewness', 0) > 0 else '负偏' if basic_stats.get('skewness', 0) < 0 else '对称'}特性，均值为{basic_stats['mean']:.2f}，中位数为{basic_stats['median']:.2f}，{'可能遵循正态分布' if basic_stats.get('normality_test', {}).get('is_normal', False) else '不遵循正态分布'}。"
            }
        }
    except Exception as e:
        print(f"为{col}生成可视化数据时出错: {str(e)}")

# 添加相关性分析
if len(result["numeric_columns"]) > 1:
    try:
        corr_matrix = df[result["numeric_columns"]].corr()
        
        # 相关性矩阵
        corr_data = {
            "columns": result["numeric_columns"],
            "matrix": corr_matrix.to_dict('list'),
            "strong_correlations": []
        }
        
        # 提取强相关对
        for i in range(len(result["numeric_columns"])):
            for j in range(i + 1, len(result["numeric_columns"])):
                col1 = result["numeric_columns"][i]
                col2 = result["numeric_columns"][j]
                corr = corr_matrix.iloc[i, j]
                if abs(corr) >= 0.7:  # 强相关阈值
                    corr_data["strong_correlations"].append({
                        "var1": col1,
                        "var2": col2,
                        "correlation": float(corr),
                        "description": f"{col1}和{col2}之间存在{'强正相关' if corr > 0.7 else '强负相关' if corr < -0.7 else '中等相关'} (r={corr:.2f})"
                    })
        
        result["correlations"] = corr_data
    except Exception as e:
        print(f"计算相关性时出错: {str(e)}")

# 保存结果
with open('data/result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    
print("分析完成，结果已保存到result.json")

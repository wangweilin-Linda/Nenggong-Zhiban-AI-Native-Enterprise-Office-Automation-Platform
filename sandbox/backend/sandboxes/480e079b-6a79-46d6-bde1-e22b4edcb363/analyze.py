import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.gridspec as gridspec

# 设置绘图风格，避免字体问题
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

# 禁用中文字体以避免冲突
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

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

# 创建结果字典
result = {
    "basic_info": {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns)
    },
    "data_preview": df.head(5).to_dict(orient='records'),
    "statistics": {},
    "missing_values": {},
    "correlations": {},
    "charts": [],
    "summary": "以下是数据分析的主要发现:"
}

# 基本统计分析
try:
    # 数值列统计
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    result["statistics"]["numeric"] = {}
    
    for col in numeric_cols:
        result["statistics"]["numeric"][col] = {
            "min": float(df[col].min()),
            "max": float(df[col].max()),
            "mean": float(df[col].mean()),
            "median": float(df[col].median()),
            "std": float(df[col].std())
        }
    
    # 分类列统计
    categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()
    result["statistics"]["categorical"] = {}
    
    for col in categorical_cols:
        value_counts = df[col].value_counts().head(10).to_dict()
        result["statistics"]["categorical"][col] = {
            "unique_count": df[col].nunique(),
            "top_values": value_counts
        }
        
    summary_points = []
    
    # 添加数值列的主要发现
    for col in numeric_cols:
        stats = result["statistics"]["numeric"][col]
        summary_points.append(f"- {col}的平均值为{stats['mean']:.2f}，最大值为{stats['max']:.2f}，最小值为{stats['min']:.2f}")
    
    # 添加分类列的主要发现
    for col in categorical_cols:
        if result["statistics"]["categorical"][col]["unique_count"] > 0:
            top_category = max(result["statistics"]["categorical"][col]["top_values"].items(), key=lambda x: x[1])
            summary_points.append(f"- {col}中出现最多的是'{top_category[0]}'，共出现{top_category[1]}次")

    # 更新摘要
    result["summary"] = "以下是数据分析的主要发现:\n" + "\n".join(summary_points)
        
except Exception as e:
    print(f"统计分析出错: {str(e)}")
    result["statistics"]["error"] = str(e)

# 缺失值分析
try:
    missing_values = df.isnull().sum().to_dict()
    missing_percent = (df.isnull().mean() * 100).to_dict()
    
    result["missing_values"] = {
        "counts": missing_values,
        "percent": {k: float(v) for k, v in missing_percent.items()}
    }
    
    # 如果有缺失值，添加到摘要
    missing_cols = [col for col, count in missing_values.items() if count > 0]
    if missing_cols:
        missing_summary = "- 发现缺失值的列: " + ", ".join([f"{col} ({missing_values[col]}个)" for col in missing_cols])
        result["summary"] += "\n" + missing_summary
    else:
        result["summary"] += "\n- 数据中没有缺失值"
        
except Exception as e:
    print(f"缺失值分析出错: {str(e)}")
    result["missing_values"]["error"] = str(e)

# 数据相关性分析
try:
    if len(numeric_cols) > 1:
        corr_matrix = df[numeric_cols].corr().round(2).to_dict(orient='records')
        result["correlations"] = corr_matrix
        
        # 找到高相关性
        high_correlations = []
        for i, col1 in enumerate(numeric_cols):
            for j, col2 in enumerate(numeric_cols):
                if i < j:  # 只看下三角矩阵部分，避免重复
                    corr_value = df[col1].corr(df[col2])
                    if abs(corr_value) > 0.5:  # 相关系数绝对值大于0.5视为较强相关
                        high_correlations.append({
                            "col1": col1,
                            "col2": col2,
                            "correlation": round(float(corr_value), 2)
                        })
        
        # 按相关系数绝对值排序
        high_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        
        # 将高相关性添加到结果和摘要
        if high_correlations:
            result["high_correlations"] = high_correlations
            
            # 添加前三个最强相关到摘要
            corr_summary = []
            for i, corr in enumerate(high_correlations[:3]):
                corr_type = "正相关" if corr["correlation"] > 0 else "负相关"
                corr_summary.append(f"- {corr['col1']}和{corr['col2']}存在{corr_type}，相关系数为{corr['correlation']}")
            
            if corr_summary:
                result["summary"] += "\n" + "\n".join(corr_summary)
        
        # 相关性热图
        plt.figure(figsize=(10, 8))
        sns.heatmap(df[numeric_cols].corr(), annot=True, cmap='coolwarm', fmt=".2f")
        plt.title('Correlation Heatmap')
        plt.tight_layout()
        plt.savefig(f"{charts_dir}/correlation_heatmap.png")
        plt.close()
        
        result["charts"].append({
            "title": "Correlation Heatmap",
            "type": "heatmap",
            "filename": "correlation_heatmap.png"
        })
except Exception as e:
    print(f"相关性分析出错: {str(e)}")
    result["correlations"] = {"error": str(e)}

# 绘制数值列分布图
try:
    for i, col in enumerate(numeric_cols[:4]):  # 最多绘制前4个数值列
        plt.figure(figsize=(10, 6))
        sns.histplot(df[col], kde=True)
        plt.title(f'Distribution of {col}')
        plt.tight_layout()
        plt.savefig(f"{charts_dir}/dist_{col.lower().replace(' ', '_')}.png")
        plt.close()
        
        result["charts"].append({
            "title": f"Distribution of {col}",
            "type": "histogram",
            "filename": f"dist_{col.lower().replace(' ', '_')}.png"
        })
except Exception as e:
    print(f"分布图生成出错: {str(e)}")

# 查找用户关心的特定分析
try:
    # 如果有地区或省份列和数值列，绘制条形图
    region_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['地区', '省份', '城市', 'region', 'province', 'city', 'area'])]
    
    if region_cols and numeric_cols:
        region_col = region_cols[0]
        value_col = numeric_cols[0]
        
        # 获取前10个地区
        top_regions = df.groupby(region_col)[value_col].sum().sort_values(ascending=False).head(10).index.tolist()
        plot_df = df[df[region_col].isin(top_regions)].groupby(region_col)[value_col].sum().reset_index()
        
        plt.figure(figsize=(12, 8))
        chart = sns.barplot(x=region_col, y=value_col, data=plot_df)
        chart.set_xticklabels(chart.get_xticklabels(), rotation=45, horizontalalignment='right')
        plt.title(f'Top 10 Regions by {value_col}')
        plt.tight_layout()
        plt.savefig(f"{charts_dir}/top_regions.png")
        plt.close()
        
        result["charts"].append({
            "title": f"Top 10 Regions by {value_col}",
            "type": "bar",
            "filename": "top_regions.png"
        })
        
        # 添加地区排名分析
        result["regional_analysis"] = {
            "top_regions": plot_df.to_dict(orient='records')
        }
        
        # 添加地区分析到摘要
        top_region = plot_df.iloc[0][region_col]
        top_value = plot_df.iloc[0][value_col]
        result["summary"] += f"\n- {top_region}在{value_col}方面表现最好，总值为{top_value:.2f}"
except Exception as e:
    print(f"地区分析出错: {str(e)}")

# 检查用户是否关心特定指标
try:
    # 利润和销售额分析
    profit_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['利润', 'profit', 'margin'])]
    sales_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['销售', '销量', 'sales', 'revenue'])]
    
    if profit_cols and sales_cols:
        profit_col = profit_cols[0]
        sales_col = sales_cols[0]
        
        # 计算利润率
        profit_rate = df[profit_col] / df[sales_col] * 100
        avg_profit_rate = profit_rate.mean()
        
        result["profit_analysis"] = {
            "total_profit": float(df[profit_col].sum()),
            "total_sales": float(df[sales_col].sum()),
            "average_profit_rate": float(avg_profit_rate)
        }
        
        # 添加到摘要
        result["summary"] += f"\n- 总利润为{result['profit_analysis']['total_profit']:.2f}，总销售额为{result['profit_analysis']['total_sales']:.2f}"
        result["summary"] += f"\n- 平均利润率为{avg_profit_rate:.2f}%"
except Exception as e:
    print(f"利润分析出错: {str(e)}")

# 保存结果到JSON文件
try:
    # 确保result变量存在
    if 'result' not in locals() and 'result' not in globals():
        result = {"error": "分析代码未定义result变量"}
    
    # 转换NumPy类型为Python原生类型
    result = convert_numpy_types(result)
    
    # 保存结果
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("分析完成，结果已保存到result.json")
except Exception as e:
    print(f"保存结果失败: {str(e)}")
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump({"error": f"保存结果失败: {str(e)}"}, f, ensure_ascii=False)

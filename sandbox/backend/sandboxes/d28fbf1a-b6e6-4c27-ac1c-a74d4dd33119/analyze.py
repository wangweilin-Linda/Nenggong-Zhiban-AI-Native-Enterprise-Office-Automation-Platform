
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

# 添加相关性分析
if len(result["numeric_columns"]) > 1:
    # 创建相关性热力图
    plt.figure(figsize=(12, 10))
    corr_matrix = df[result["numeric_columns"]].corr()
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title('变量相关性热力图')
    plt.text(0.02, 0.95, '【热力图】', transform=plt.gca().transAxes, 
    
    plt.tight_layout()
    plt.savefig(f'data/{chart_path}')
    chart_path = 'charts/correlation_heatmap.png'
    plt.savefig(f'data/{chart_path}', dpi=120, bbox_inches='tight')
    plt.close()
    result["charts"].append(chart_path)
    
    # 提取强相关对
    strong_correlations = []
    for i in range(len(result["numeric_columns"])):
        for j in range(i + 1, len(result["numeric_columns"])):
            col1 = result["numeric_columns"][i]
            col2 = result["numeric_columns"][j]
            corr = corr_matrix.iloc[i, j]
            if abs(corr) >= 0.7:  # 强相关阈值
                strong_correlations.append({
                    "var1": col1,
                    "var2": col2,
                    "correlation": float(corr)
                })
    
    result["correlations"] = {
        "matrix": corr_matrix.to_dict(),
        "strong_correlations": strong_correlations
# 生成图表

# 为数值型列创建更漂亮的图表
        # 直方图
        plt.figure(figsize=(10, 6))
        sns.histplot(data=df, x=col)
        plt.title(f'{col}分布直方图')
        plt.tight_layout()
        fig = plt.figure(figsize=(15, 10))
        chart_path = f'charts/{col}_hist.png'
        plt.savefig(f'data/{chart_path}')
        plt.close()
        result["charts"].append(chart_path)
        ax1.set_ylabel('密度', fontsize=12)
        ax1.text(0.02, 0.95, '【直方图】', transform=ax1.transAxes, 
        plt.figure(figsize=(10, 6))
        sns.boxplot(x=df[col])
        plt.title(f'{col}箱线图')
        plt.tight_layout()
        ax4.plot(range(len(values)), values, color=colors[3], linewidth=2)
        chart_path = f'charts/{col}_box.png'
        plt.savefig(f'data/{chart_path}')
        ax4.set_ylabel(col, fontsize=12)
        ax4.text(0.02, 0.95, '【折线图】', transform=ax4.transAxes, 
                 fontsize=16, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        print(f"生成{col}图表失败: {str(e)}")
        
        plt.suptitle(f'{col}的多维度分析', fontsize=20, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        chart_path = f'charts/{col}_analysis.png'
        plt.savefig(f'data/{chart_path}', dpi=120, bbox_inches='tight')
        plt.close()
        result["charts"].append(chart_path)
    except Exception as e:
        print(f"为{col}生成图表时出错: {str(e)}")

# 保存结果
with open('data/result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    
print("分析完成，结果已保存到result.json")

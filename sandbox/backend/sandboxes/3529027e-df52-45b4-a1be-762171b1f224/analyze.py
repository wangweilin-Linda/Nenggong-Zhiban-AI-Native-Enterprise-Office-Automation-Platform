
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.gridspec as gridspec

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 设置更好看的图表样式
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
    plt.figure(figsize=(14, 10))
    corr_matrix = df[result["numeric_columns"]].corr()

    # 使用漂亮的热力图样式
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    cmap = sns.diverging_palette(230, 20, as_cmap=True)

    sns.heatmap(corr_matrix, mask=mask, cmap=cmap, vmax=1, vmin=-1, center=0,
                annot=True, fmt=".2f", square=True, linewidths=.5, cbar_kws={"shrink": .8})

    plt.title('变量相关性热力图', fontsize=20, fontweight='bold', pad=20)
    plt.text(0.02, 0.95, '【热力图】', transform=plt.gca().transAxes, 
             fontsize=16, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
    plt.tight_layout()

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
    }

# 为数值型列创建更漂亮的图表
for col in result["numeric_columns"]:
    try:
        # 创建子图网格
        fig = plt.figure(figsize=(15, 10))
        gs = gridspec.GridSpec(2, 2, figure=fig)
        
        # 直方图 + KDE
        ax1 = fig.add_subplot(gs[0, 0])
        sns.histplot(df[col], kde=True, color=colors[0], ax=ax1, stat='density')
        ax1.set_title(f'{col}的分布', fontsize=14, fontweight='bold')
        ax1.set_xlabel(col, fontsize=12)
        ax1.set_ylabel('密度', fontsize=12)
        ax1.text(0.02, 0.95, '【直方图】', transform=ax1.transAxes, 
                 fontsize=16, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # 箱线图
        ax2 = fig.add_subplot(gs[0, 1])
        sns.boxplot(y=df[col], color=colors[1], ax=ax2)
        ax2.set_title(f'{col}的箱线图', fontsize=14, fontweight='bold')
        ax2.set_ylabel(col, fontsize=12)
        ax2.text(0.02, 0.95, '【箱线图】', transform=ax2.transAxes, 
                 fontsize=16, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        # 如果数据量不太大，绘制散点图
        if len(df) <= 1000:
            ax3 = fig.add_subplot(gs[1, 0])
            ax3.scatter(range(len(df)), df[col], alpha=0.6, color=colors[2])
            ax3.set_title(f'{col}的散点分布', fontsize=14, fontweight='bold')
            ax3.set_xlabel('数据点', fontsize=12)
            ax3.set_ylabel(col, fontsize=12)
            ax3.text(0.02, 0.95, '【散点图】', transform=ax3.transAxes, 
                     fontsize=16, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
            ax3.grid(True, linestyle='--', alpha=0.7)
        
        # 时间序列/趋势图
        ax4 = fig.add_subplot(gs[1, 1])
        values = df[col].sort_values()
        ax4.plot(range(len(values)), values, color=colors[3], linewidth=2)
        ax4.set_title(f'{col}的排序值分布', fontsize=14, fontweight='bold')
        ax4.set_xlabel('排序后的索引', fontsize=12)
        ax4.set_ylabel(col, fontsize=12)
        ax4.text(0.02, 0.95, '【折线图】', transform=ax4.transAxes, 
                 fontsize=16, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        ax4.grid(True, linestyle='--', alpha=0.7)
        
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

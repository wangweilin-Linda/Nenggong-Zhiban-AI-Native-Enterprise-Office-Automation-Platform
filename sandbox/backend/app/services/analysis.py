import pandas as pd
import numpy as np
from typing import Dict, Any
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import io
import base64

def create_chart(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """为数值列创建图表"""
    plt.figure(figsize=(10, 6))
    
    if df[column].dtype in ['int64', 'float64']:
        # 数值型数据：创建直方图和密度图
        sns.histplot(data=df, x=column, kde=True)
        plt.title(f'{column} 分布')
        plt.xlabel(column)
        plt.ylabel('频数')
    else:
        # 分类数据：创建条形图
        value_counts = df[column].value_counts()
        sns.barplot(x=value_counts.index, y=value_counts.values)
        plt.title(f'{column} 分布')
        plt.xticks(rotation=45)
        plt.xlabel(column)
        plt.ylabel('频数')

    # 将图表转换为base64字符串
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    return {
        'title': f'{column} 分布图',
        'options': {
            'title': {
                'text': f'{column} 分布'
            },
            'graphic': {
                'type': 'image',
                'style': {
                    'image': f'data:image/png;base64,{base64.b64encode(image_png).decode()}'
                }
            }
        }
    }

def analyze_csv_data(df: pd.DataFrame) -> Dict[str, Any]:
    """分析CSV数据并返回结果"""
    # 基本信息
    row_count = len(df)
    column_count = len(df.columns)
    
    # 统计摘要
    summary = {}
    for column in df.columns:
        if df[column].dtype in ['int64', 'float64']:
            stats = df[column].describe()
            summary[column] = {
                '平均值': round(stats['mean'], 2),
                '中位数': round(stats['50%'], 2),
                '标准差': round(stats['std'], 2),
                '最小值': round(stats['min'], 2),
                '最大值': round(stats['max'], 2)
            }
        else:
            value_counts = df[column].value_counts()
            summary[column] = {
                '唯一值数量': len(value_counts),
                '最常见值': value_counts.index[0],
                '最常见值频数': int(value_counts.values[0])
            }
    
    # 缺失值统计
    missing_values = df.isnull().sum().to_dict()
    
    # 为每个数值列创建图表
    charts = []
    for column in df.columns:
        if df[column].dtype in ['int64', 'float64'] or (df[column].dtype == 'object' and df[column].nunique() <= 10):
            charts.append(create_chart(df, column))
    
    return {
        'row_count': row_count,
        'column_count': column_count,
        'summary': summary,
        'missing_values': missing_values,
        'charts': charts
    }

def analyze_data():
    """数据分析入口函数"""
    try:
        # 读取CSV文件
        df = pd.read_csv('/data/input.csv')
        
        # 设置matplotlib中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表目录
        charts_dir = '/data/charts'
        os.makedirs(charts_dir, exist_ok=True)
        
        results = analyze_csv_data(df)
        
        # 生成图表
        charts = results['charts']
        
        # 保存结果
        with open('/data/result.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"分析失败: {str(e)}")
        return False

if __name__ == '__main__':
    analyze_data()
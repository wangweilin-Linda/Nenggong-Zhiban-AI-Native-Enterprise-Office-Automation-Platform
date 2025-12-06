import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from typing import Dict, List
import pandas as pd

class Visualizer:
    def __init__(self):
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
    def create_chart(self, df: pd.DataFrame, chart_type: str, 
                    columns: List[str], group_by: str = None) -> str:
        """生成图表并返回base64编码的图像"""
        plt.figure(figsize=(10, 6))
        
        if chart_type == 'bar':
            self._create_bar_chart(df, columns, group_by)
        elif chart_type == 'line':
            self._create_line_chart(df, columns, group_by)
        elif chart_type == 'pie':
            self._create_pie_chart(df, columns[0], group_by)
        elif chart_type == 'scatter':
            self._create_scatter_chart(df, columns[0], columns[1])
            
        # 转换图表为base64字符串
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300)
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return base64.b64encode(image_png).decode()
        
    def _create_bar_chart(self, df: pd.DataFrame, columns: List[str], group_by: str):
        if group_by:
            df_grouped = df.groupby(group_by)[columns].sum()
            df_grouped.plot(kind='bar')
            plt.title(f'{group_by}分组柱状图')
        else:
            df[columns].plot(kind='bar')
            plt.title('数据柱状图')
        plt.xlabel(group_by if group_by else '指标')
        plt.ylabel('数值')
        plt.xticks(rotation=45)
        
    def _create_line_chart(self, df: pd.DataFrame, columns: List[str], group_by: str):
        if group_by:
            df_grouped = df.groupby(group_by)[columns].sum()
            df_grouped.plot(kind='line', marker='o')
            plt.title(f'{group_by}趋势图')
        else:
            df[columns].plot(kind='line', marker='o')
            plt.title('数据趋势图')
        plt.xlabel(group_by if group_by else '时间')
        plt.ylabel('数值')
        plt.grid(True)
        
    def _create_pie_chart(self, df: pd.DataFrame, column: str, group_by: str):
        if group_by:
            data = df.groupby(group_by)[column].sum()
        else:
            data = df[column]
        plt.pie(data, labels=data.index, autopct='%1.1f%%')
        plt.title(f'{column}占比图')
        
    def _create_scatter_chart(self, df: pd.DataFrame, x_col: str, y_col: str):
        plt.scatter(df[x_col], df[y_col])
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.title(f'{x_col}与{y_col}散点图')
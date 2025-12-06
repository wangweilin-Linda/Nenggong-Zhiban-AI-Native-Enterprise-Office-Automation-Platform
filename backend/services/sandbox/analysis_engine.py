import json
from typing import Dict, Any, List
from loguru import logger # type: ignore
import pandas as pd
import numpy as np

class AnalysisEngine:
    def __init__(self):
        # 预定义分析模板
        self.analysis_templates = {
            "correlation": self._analyze_correlation,
            "outliers": self._analyze_outliers,
            "distribution": self._analyze_distribution,
            "summary": self._analyze_summary,
            "trend": self._analyze_trend
        }
        
        # 关键词映射到分析类型
        self.keyword_mapping = {
            "相关性": "correlation",
            "关联": "correlation",
            "异常值": "outliers",
            "异常": "outliers",
            "分布": "distribution",
            "统计": "summary",
            "趋势": "trend"
        }
    
    def parse_prompt(self, prompt: str) -> List[str]:
        """解析用户输入的提示，返回需要执行的分析类型列表"""
        analysis_types = []
        for keyword, analysis_type in self.keyword_mapping.items():
            if keyword in prompt:
                analysis_types.append(analysis_type)
        
        # 如果没有匹配到任何分析类型，默认执行基础统计分析
        return analysis_types if analysis_types else ["summary"]
    
    def analyze(self, df: pd.DataFrame, prompt: str) -> Dict[str, Any]:
        """根据提示执行相应的分析"""
        try:
            analysis_types = self.parse_prompt(prompt)
            results = {}
            
            for analysis_type in analysis_types:
                if analysis_type in self.analysis_templates:
                    results[analysis_type] = self.analysis_templates[analysis_type](df)
            
            return results
        except Exception as e:
            logger.error(f"分析过程出错: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数值列之间的相关性"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return {"message": "没有足够的数值列进行相关性分析"}
        
        corr_matrix = df[numeric_cols].corr().round(3)
        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "strong_correlations": self._get_strong_correlations(corr_matrix)
        }
    
    def _analyze_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测数值列的异常值"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outliers = {}
        
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers[col] = {
                "count": len(df[(df[col] < lower_bound) | (df[col] > upper_bound)]),
                "lower_bound": lower_bound,
                "upper_bound": upper_bound
            }
        
        return outliers
    
    def _analyze_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数值列的分布情况"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        distributions = {}
        
        for col in numeric_cols:
            distributions[col] = {
                "mean": df[col].mean(),
                "median": df[col].median(),
                "std": df[col].std(),
                "skew": df[col].skew(),
                "kurtosis": df[col].kurtosis()
            }
        
        return distributions
    
    def _analyze_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """生成基础统计摘要"""
        return {
            "basic_info": {
                "row_count": len(df),
                "column_count": len(df.columns),
                "missing_values": df.isnull().sum().to_dict()
            },
            "numerical_summary": df.describe().to_dict()
        }
    
    def _analyze_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数值列的趋势"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        trends = {}
        
        for col in numeric_cols:
            trends[col] = {
                "trend": "increasing" if df[col].diff().mean() > 0 else "decreasing",
                "volatility": df[col].std() / df[col].mean() if df[col].mean() != 0 else 0
            }
        
        return trends
    
    def _get_strong_correlations(self, corr_matrix: pd.DataFrame) -> List[Dict[str, Any]]:
        """提取强相关性对"""
        strong_correlations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                correlation = corr_matrix.iloc[i, j]
                if abs(correlation) >= 0.7:  # 强相关阈值
                    strong_correlations.append({
                        "var1": corr_matrix.columns[i],
                        "var2": corr_matrix.columns[j],
                        "correlation": correlation
                    })
        return strong_correlations
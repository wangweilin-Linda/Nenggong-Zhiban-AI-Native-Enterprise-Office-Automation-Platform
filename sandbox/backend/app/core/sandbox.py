import docker # type: ignore
import uuid
from loguru import logger # type: ignore
import os
import json
import shutil
import platform
import subprocess
import sys
import base64
import time
import numpy as np

class SandboxManager:
    def __init__(self):
        try:
            # 创建基础沙盒目录
            self.sandbox_base = os.path.abspath("sandboxes")
            os.makedirs(self.sandbox_base, exist_ok=True)
            logger.info(f"沙盒基础目录: {self.sandbox_base}")
        except Exception as e:
            logger.error(f"初始化沙盒管理器失败: {str(e)}")
            raise

    async def create_sandbox(self, file_data: bytes) -> str:
        sandbox_id = str(uuid.uuid4())
        try:
            # 创建沙盒目录
            sandbox_dir = os.path.join(self.sandbox_base, sandbox_id)
            data_dir = os.path.join(sandbox_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            # 保存CSV文件
            file_path = os.path.join(data_dir, "input.csv")
            with open(file_path, "wb") as f:
                f.write(file_data)
            
            logger.info(f"创建沙盒: {sandbox_id}")
            return sandbox_id
        except Exception as e:
            logger.error(f"创建沙盒失败: {str(e)}")
            if os.path.exists(sandbox_dir):
                shutil.rmtree(sandbox_dir)
            raise

    async def run_analysis(self, sandbox_id: str, custom_code: str = None) -> bool:
        try:
            # 获取沙盒目录
            sandbox_dir = os.path.join(self.sandbox_base, sandbox_id)
            data_dir = os.path.join(sandbox_dir, "data")
            
            # 确保目录存在并设置权限
            os.makedirs(data_dir, exist_ok=True)
            os.chmod(data_dir, 0o777)
            
            # 确保结果文件可写
            result_file = os.path.join(data_dir, "result.json")
            if os.path.exists(result_file):
                os.chmod(result_file, 0o666)
            
            # 创建分析脚本
            analyze_script = os.path.join(sandbox_dir, "analyze.py")
            
            # 根据是否提供自定义代码，决定使用哪种分析脚本
            if custom_code:
                logger.info(f"使用自定义分析代码")
                with open(analyze_script, "w", encoding="utf-8") as f:
                    f.write(custom_code)
            else:
                # 使用默认分析脚本 - 现在只计算数据，不生成图表
                logger.info(f"使用默认分析脚本")
                with open(analyze_script, "w", encoding="utf-8") as f:
                    f.write("""
import pandas as pd
import numpy as np
import json
import os

# 尝试导入scipy，但不要因此失败
has_scipy = False
try:
    from scipy import stats
    has_scipy = True
    print("成功导入scipy库，可以进行高级统计分析")
except ImportError:
    print("警告: 未安装scipy库，部分高级统计功能将不可用")

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
    try:
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
        
        # 添加更多高级统计信息(如果scipy可用)
        if has_scipy:
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
            except Exception as e:
                print(f"计算列 {col} 的高级统计信息时出错: {str(e)}")
        
        result["summary"][col] = basic_stats
        
        # 为前端可视化准备数据
        try:
            # 直方图数据
            hist_data = np.histogram(data, bins=min(30, len(data)//10 + 5))
            
            # 安全计算比率，避免除零错误
            def safe_ratio(a, b, default=0):
                return a/b if b != 0 else default
            
            # 准备文字描述
            descriptions = {
                "histogram": f"平均值: {basic_stats['mean']:.2f}, 中位数: {basic_stats['median']:.2f}, 标准差: {basic_stats['std']:.2f}",
                "boxplot": f"Q1: {basic_stats['q1']:.2f}, 中位数: {basic_stats['median']:.2f}, Q3: {basic_stats['q3']:.2f}, IQR: {basic_stats['iqr']:.2f}",
                "scatter": f"数据范围: {basic_stats['min']:.2f} 到 {basic_stats['max']:.2f}, 变异系数: {safe_ratio(basic_stats['std'], basic_stats['mean']):.2f}",
                "trend": f"最小值: {basic_stats['min']:.2f}, 最大值: {basic_stats['max']:.2f}, 变化率: {safe_ratio(basic_stats['max']-basic_stats['min'], basic_stats['mean']):.2f}",
            }
            
            # 添加汇总描述
            if has_scipy and "skewness" in basic_stats:
                skew_desc = "正偏" if basic_stats.get('skewness', 0) > 0 else "负偏" if basic_stats.get('skewness', 0) < 0 else "对称"
                is_normal = "可能遵循正态分布" if basic_stats.get('normality_test', {}).get('is_normal', False) else "不遵循正态分布"
                descriptions["summary"] = f"{col}的数据分布呈现{skew_desc}特性，均值为{basic_stats['mean']:.2f}，中位数为{basic_stats['median']:.2f}，{is_normal}。"
            else:
                descriptions["summary"] = f"{col}的平均值为{basic_stats['mean']:.2f}，中位数为{basic_stats['median']:.2f}，数据分布在{basic_stats['min']:.2f}到{basic_stats['max']:.2f}之间。"
            
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
                "descriptions": descriptions
            }
        except Exception as e:
            print(f"为列 {col} 生成可视化数据时出错: {str(e)}")
    except Exception as e:
        print(f"处理列 {col} 时出错: {str(e)}")

# 添加相关性分析
if len(result["numeric_columns"]) > 1:
    try:
        # 去除缺失值进行相关性计算
        corr_df = df[result["numeric_columns"]].dropna()
        if len(corr_df) > 0:
            corr_matrix = corr_df.corr()
            
            # 相关性矩阵
            corr_data = {
                "columns": result["numeric_columns"],
                "matrix": {}
            }
            
            # 转换为前端易用的格式
            for col in result["numeric_columns"]:
                corr_data["matrix"][col] = {}
                for other_col in result["numeric_columns"]:
                    try:
                        corr_data["matrix"][col][other_col] = float(corr_matrix.loc[col, other_col])
                    except:
                        corr_data["matrix"][col][other_col] = None
            
            # 提取强相关对
            strong_correlations = []
            for i in range(len(result["numeric_columns"])):
                for j in range(i + 1, len(result["numeric_columns"])):
                    try:
                        col1 = result["numeric_columns"][i]
                        col2 = result["numeric_columns"][j]
                        corr = corr_matrix.loc[col1, col2]
                        if abs(corr) >= 0.7:  # 强相关阈值
                            corr_type = "强正相关" if corr > 0.7 else "强负相关" if corr < -0.7 else "中等相关"
                            strong_correlations.append({
                                "var1": col1,
                                "var2": col2,
                                "correlation": float(corr),
                                "description": f"{col1}和{col2}之间存在{corr_type} (r={corr:.2f})"
                            })
                    except Exception as e:
                        print(f"处理相关性对({col1},{col2})时出错: {str(e)}")
            
            corr_data["strong_correlations"] = strong_correlations
            result["correlations"] = corr_data
    except Exception as e:
        print(f"计算相关性时出错: {str(e)}")
        # 错误时添加空的相关性数据
        result["correlations"] = {
            "columns": result["numeric_columns"],
            "matrix": {},
            "strong_correlations": []
        }

# 保存结果
with open('data/result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    
print("分析完成，结果已保存到result.json")
""")
            
            # 直接在当前进程中执行分析
            current_dir = os.getcwd()
            os.chdir(sandbox_dir)
            
            # 执行命令
            logger.info(f"开始执行分析: {sandbox_id}")
            result = subprocess.run([sys.executable, analyze_script], 
                                   capture_output=True, 
                                   text=True)
            success = result.returncode == 0
            
            # 记录输出
            with open(os.path.join(data_dir, "analysis_log.txt"), "w", encoding="utf-8") as f:
                f.write("===== 标准输出 =====\n")
                f.write(result.stdout)
                f.write("\n\n===== 标准错误 =====\n")
                f.write(result.stderr)
            
            # 切回原目录
            os.chdir(current_dir)
            
            if success:
                logger.info(f"分析完成: {sandbox_id}")
            else:
                logger.error(f"分析失败: {sandbox_id}, 错误: {result.stderr}")
                
            return success
        except Exception as e:
            logger.error(f"运行分析失败: {str(e)}")
            return False

    async def cleanup_sandbox(self, sandbox_id: str):
        try:
            # 清理沙盒目录
            sandbox_dir = os.path.join(self.sandbox_base, sandbox_id)
            if os.path.exists(sandbox_dir):
                logger.info(f"清理沙盒: {sandbox_id}")
                shutil.rmtree(sandbox_dir)
        except Exception as e:
            logger.error(f"清理沙盒失败: {str(e)}")

    async def get_analysis_result(self, sandbox_id: str):
        try:
            sandbox_dir = os.path.join(self.sandbox_base, sandbox_id)
            data_dir = os.path.join(sandbox_dir, "data")
            result_file = os.path.join(data_dir, "result.json")
            
            if not os.path.exists(result_file):
                logger.error(f"结果文件不存在: {result_file}")
                return None
                
            with open(result_file, "r", encoding="utf-8") as f:
                result = json.load(f)
        
            return result
        except Exception as e:
            logger.error(f"获取分析结果失败: {str(e)}")

    async def cleanup_old_sandboxes(self):
        """清理超过24小时的沙盒"""
        try:
            current_time = time.time()
            for sandbox_id in os.listdir(self.sandbox_base):
                sandbox_dir = os.path.join(self.sandbox_base, sandbox_id)
                if os.path.isdir(sandbox_dir):
                    created_time = os.path.getctime(sandbox_dir)
                    if current_time - created_time > 24 * 3600:  # 24小时
                        await self.cleanup_sandbox(sandbox_id)
        except Exception as e:
            logger.error(f"清理旧沙盒失败: {str(e)}")

    async def get_result(self, task_id: str):
        """获取分析结果"""
        try:
            sandbox_dir = os.path.join(self.sandbox_base, task_id)
            if not os.path.exists(sandbox_dir):
                logger.warning(f"沙盒目录不存在: {sandbox_dir}")
                raise ValueError("任务不存在或已过期")
                
            data_dir = os.path.join(sandbox_dir, "data")
            if not os.path.exists(data_dir):
                logger.warning(f"数据目录不存在: {data_dir}")
                return None
                
            # 检查分析状态
            status_file = os.path.join(data_dir, "status.json")
            if os.path.exists(status_file):
                with open(status_file, "r", encoding="utf-8") as f:
                    status = json.load(f)
                    if status.get("status") == "failed":
                        raise ValueError(status.get("error", "分析任务失败"))
            
            result_file = os.path.join(data_dir, "result.json")
            if not os.path.exists(result_file):
                logger.info(f"结果文件尚未生成: {result_file}")
                return None
                
            return await self.get_analysis_result(task_id)
        except ValueError as e:
            logger.warning(f"获取结果失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"处理结果异常: {str(e)}")
            return None
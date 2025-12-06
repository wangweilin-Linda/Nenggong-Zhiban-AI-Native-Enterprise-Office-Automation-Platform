from fastapi import HTTPException
from typing import Dict
import pandas as pd
import io

def validate_excel_file(file_data: bytes) -> pd.DataFrame:
    """验证Excel文件并返回DataFrame"""
    try:
        df = pd.read_excel(io.BytesIO(file_data))
        if df.empty:
            raise HTTPException(status_code=400, detail="Excel文件为空")
        return df
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无效的Excel文件: {str(e)}")

def validate_analysis_params(params: Dict, df: pd.DataFrame) -> Dict:
    """验证分析参数"""
    if not params.get("xField") or not params.get("yField"):
        raise HTTPException(status_code=400, detail="缺少必要的分析参数: xField, yField")
    
    if params["xField"] not in df.columns or params["yField"] not in df.columns:
        raise HTTPException(status_code=400, detail="指定的字段不存在于数据中")
    
    return params
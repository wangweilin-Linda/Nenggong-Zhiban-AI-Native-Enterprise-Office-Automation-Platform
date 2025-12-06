from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
from ...services.analysis import analyze_csv_data
import io

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="只支持CSV文件")
    
    try:
        # 读取上传的文件内容
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # 分析数据
        results = analyze_csv_data(df)
        
        return JSONResponse(content=results)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}") 
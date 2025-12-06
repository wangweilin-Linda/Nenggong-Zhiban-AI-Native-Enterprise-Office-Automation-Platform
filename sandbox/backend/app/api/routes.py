from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from ..core.analysis import AnalysisManager
from typing import Dict, Any
import io

router = APIRouter()
analysis_manager = AnalysisManager()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        # 读取上传的文件内容
        file_data = await file.read()
        
        # 创建分析任务
        task = await analysis_manager.create_task(
            name=file.filename,
            file_data=file_data,
            parameters={}
        )
        
        return {
            "task_id": task.task_id,
            "status": task.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/{task_id}")
async def analyze_file(task_id: str) -> Dict[str, Any]:
    try:
        # 在沙盒中运行分析
        success = await analysis_manager.run_analysis(task_id)
        if not success:
            raise HTTPException(status_code=500, detail="分析任务启动失败")
        
        return {
            "task_id": task_id,
            "status": "processing"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{task_id}")
async def get_result(task_id: str) -> Dict[str, Any]:
    try:
        return await analysis_manager.get_result(task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
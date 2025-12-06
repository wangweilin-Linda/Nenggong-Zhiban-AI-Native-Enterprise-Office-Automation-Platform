from fastapi import APIRouter, UploadFile, File, HTTPException
from loguru import logger
from typing import Dict, Any, Optional
import os
import json
import uuid
from ....core.exceptions import FileProcessError, AnalysisError, ValidationError
from ....services.analysis import analyze_data

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, str]:
    """上传文件接口
    
    Args:
        file: 上传的文件
        
    Returns:
        包含task_id的字典
    """
    try:
        # 验证文件类型
        if not file.filename.endswith('.csv'):
            raise ValidationError("只支持CSV文件格式")
            
        # 验证文件大小
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB
            raise ValidationError("文件大小不能超过10MB")
            
        # 生成任务ID并保存文件
        task_id = str(uuid.uuid4())
        file_path = f"uploads/{task_id}.csv"
        os.makedirs("uploads", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)
            
        return {"task_id": task_id}
        
    except ValidationError as e:
        logger.warning(f"文件验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{task_id}/analyze")
async def analyze_task(task_id: str) -> Dict[str, Any]:
    """启动分析任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        分析任务状态
    """
    try:
        file_path = f"uploads/{task_id}.csv"
        if not os.path.exists(file_path):
            raise ValidationError(f"任务{task_id}不存在")
            
        # 读取文件内容
        with open(file_path, "rb") as f:
            content = f.read()
            
        # 执行分析
        result = await analyze_data(content)
        
        # 保存分析结果
        os.makedirs("results", exist_ok=True)
        result_path = f"results/{task_id}.json"
        with open(result_path, "w") as f:
            json.dump(result, f)
            
        return {"status": "success", "task_id": task_id}
        
    except ValidationError as e:
        logger.warning(f"任务验证失败: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"分析任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{task_id}")
async def get_result(task_id: str) -> Dict[str, Any]:
    """获取分析结果
    
    Args:
        task_id: 任务ID
        
    Returns:
        分析结果
    """
    try:
        result_path = f"results/{task_id}.json"
        if not os.path.exists(result_path):
            return {"status": "processing"}
            
        with open(result_path, "r") as f:
            result = json.load(f)
            
        return result
        
    except Exception as e:
        logger.error(f"获取分析结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
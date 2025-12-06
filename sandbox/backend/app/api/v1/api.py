from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from loguru import logger
import os
from typing import Dict, Any, Optional
from ...core.config import settings
from ...core.sandbox import SandboxManager
from pydantic import BaseModel

# 创建 API 路由器
api_router = APIRouter()

# 创建沙盒管理器实例
analysis_manager = SandboxManager()

# 定义任务模型
class Task(BaseModel):
    task_id: str
    status: str = "pending"
    error: Optional[str] = None

# 定义代码模型，用于接收外部生成的代码
class CodeRequest(BaseModel):
    code: Optional[str] = None

@api_router.post("/analysis/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件接口"""
    try:
        # 验证文件类型
        if not file.filename.endswith('.csv'):
            raise ValueError("只支持CSV文件格式")
            
        content = await file.read()
        # 直接使用 create_sandbox 方法创建沙盒
        sandbox_id = await analysis_manager.create_sandbox(content)
        return {"task_id": sandbox_id}
    except ValueError as e:
        logger.warning(f"文件验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 其他路由保持不变
@api_router.post("/analysis/{task_id}/analyze")  # 修改这里
async def start_analysis(task_id: str, code_request: CodeRequest = None):
    """启动分析任务"""
    try:
        # 检查是否提供了自定义代码
        custom_code = None
        if code_request and code_request.code:
            logger.info(f"收到自定义分析代码，长度: {len(code_request.code)}字符")
            custom_code = code_request.code
        
        # 使用提供的代码或默认代码运行分析
        success = await analysis_manager.run_analysis(task_id, custom_code)
        if not success:
            raise HTTPException(status_code=500, detail="分析任务启动失败")
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/result/{task_id}")  # 修改这里
async def get_analysis_result(task_id: str):
    """获取分析结果"""
    try:
        # 先检查任务ID是否存在
        sandbox_dir = os.path.join(settings.SANDBOX_BASE, task_id)
        if not os.path.exists(sandbox_dir):
            # 增加更详细的日志
            logger.warning(f"任务不存在: {task_id}, 目录: {sandbox_dir}")
            # 检查沙盒基础目录是否存在
            if not os.path.exists(settings.SANDBOX_BASE):
                logger.error(f"沙盒基础目录不存在: {settings.SANDBOX_BASE}")
                
            # 列出沙盒目录中的所有任务
            if os.path.exists(settings.SANDBOX_BASE):
                tasks = os.listdir(settings.SANDBOX_BASE)
                logger.info(f"现有任务列表: {tasks}")
                
            return JSONResponse(
                status_code=404,
                content={"error": "任务不存在或已过期"}
            )
            
        result = await analysis_manager.get_result(task_id)
        if result is None:
            # 任务存在但还在处理中
            return JSONResponse(
                status_code=202,
                content={"status": "processing"}
            )
        return result
    except ValueError as e:
        logger.warning(f"获取结果值错误: {str(e)}")
        return JSONResponse(
            status_code=404,
            content={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"获取分析结果失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "获取分析结果失败"}
        )
        
@api_router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        # 检查任务ID是否存在
        sandbox_dir = os.path.join(settings.SANDBOX_BASE, task_id)
        if not os.path.exists(sandbox_dir):
            logger.warning(f"任务不存在: {task_id}")
            return JSONResponse(
                status_code=404,
                content={"error": "任务不存在或已过期"}
            )
            
        # 检查分析状态
        data_dir = os.path.join(sandbox_dir, "data")
        result_file = os.path.join(data_dir, "result.json")
        
        # 如果结果文件存在，表示分析完成
        if os.path.exists(result_file):
            return {"task_id": task_id, "status": "completed"}
            
        # 检查是否有错误日志
        log_file = os.path.join(data_dir, "analysis_log.txt")
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.read()
                if "错误" in log_content or "Error" in log_content:
                    return {"task_id": task_id, "status": "failed", "error": "分析过程中出现错误"}
        
        # 默认为处理中
        return {"task_id": task_id, "status": "processing"}
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"获取任务状态失败: {str(e)}"}
        )
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form, Body
from fastapi.responses import JSONResponse
from loguru import logger # type: ignore
import os
from typing import Dict, Any, Optional, List
from services.sandbox.sandbox_client import SandboxClient
from services.sandbox.code_generator import generate_python_code, process_chat_message
from pydantic import BaseModel
import traceback

# 创建 API 路由器
router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

# 创建沙盒客户端实例
sandbox_client = SandboxClient()

# 定义任务模型
class Task(BaseModel):
    task_id: str
    status: str = "pending"
    error: Optional[str] = None

# 定义分析参数模型
class AnalysisParams(BaseModel):
    options: Dict[str, Any] = {}
    prompt: Optional[str] = None  # 添加提示词字段

# 定义聊天请求模型
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None
    has_file: bool = False

# 定义聊天响应模型
class ChatResponse(BaseModel):
    response: str
    analysis_ready: bool = False
    final_prompt: Optional[str] = None

@router.post("/chat")
async def process_chat(request: ChatRequest):
    """处理聊天消息并返回回复"""
    try:
        logger.info(f"接收到聊天请求: {request.message}")
        
        # 处理聊天消息
        response, analysis_ready, final_prompt = await process_chat_message(
            request.message, 
            request.history or [], 
            request.has_file
        )
        
        # 确保response是字符串类型
        if response is not None:
            response = str(response)
        else:
            response = "抱歉，无法生成响应"
        
        # 添加日志记录返回的响应内容
        logger.info(f"返回给前端的响应: {response[:100]}...")
        
        # 使用ChatResponse模型封装返回数据
        return ChatResponse(
            response=response,
            analysis_ready=analysis_ready,
            final_prompt=final_prompt
        )
    except Exception as e:
        logger.error(f"处理聊天消息失败: {str(e)}")
        logger.error(traceback.format_exc())
        # 返回友好的错误信息，不抛出异常
        return ChatResponse(
            response="非常抱歉，处理您的请求时出现了错误。请稍后再试。",
            analysis_ready=False,
            final_prompt=None
        )

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件接口"""
    try:
        # 验证文件类型
        if not file.filename.endswith('.csv'):
            raise ValueError("只支持CSV文件格式")
            
        content = await file.read()
        # 上传文件到沙盒服务
        result = await sandbox_client.upload_file(content)
        logger.info(f"成功上传文件到沙盒服务，任务ID: {result.get('task_id')}")
        return result
    except ValueError as e:
        logger.warning(f"文件验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{task_id}/analyze")
async def start_analysis(task_id: str, params: AnalysisParams = Body(default=None)):
    """启动分析任务"""
    try:
        # 更详细的日志记录
        logger.info(f"接收到分析请求，任务ID: {task_id}")
        logger.info(f"请求参数: {params}")
        
        # 如果没有提供分析参数，使用默认参数
        options = params.options if params else {}
        prompt = params.prompt if params and params.prompt else None
        
        logger.info(f"启动任务 {task_id} 的分析，参数: {options}")
        if prompt:
            logger.info(f"提示词: {prompt}")
            
            # 使用LLM生成Python代码
            try:
                logger.info("开始调用代码生成服务...")
                generated_code = await generate_python_code(prompt)
                if generated_code:
                    logger.info(f"成功生成分析代码，长度: {len(generated_code)}")
                    # 输出生成代码的前200个字符，用于调试
                    logger.info(f"代码片段: {generated_code[:200]}...")
                    
                    # 调用沙盒服务启动分析，并传递生成的代码
                    logger.info("发送生成的代码到沙盒服务...")
                    result = await sandbox_client.start_analysis(task_id, generated_code)
                    logger.info("沙盒服务启动分析成功")
                else:
                    logger.warning("代码生成结果为空，回退到默认分析脚本")
                    result = await sandbox_client.start_analysis(task_id)
            except Exception as code_error:
                logger.error(f"代码生成失败: {str(code_error)}")
                logger.error(traceback.format_exc())
                # 如果代码生成失败，使用默认分析脚本
                logger.info("由于代码生成失败，回退到默认分析脚本")
                result = await sandbox_client.start_analysis(task_id)
        else:
            # 如果没有提供提示词，使用默认分析脚本
            logger.info("未提供提示词，使用默认分析脚本")
            result = await sandbox_client.start_analysis(task_id)
            
        return result
    except ValueError as e:
        logger.warning(f"启动分析任务失败: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"启动分析任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{task_id}")
async def get_analysis_result(task_id: str):
    """获取分析结果"""
    try:
        logger.info(f"获取任务 {task_id} 的分析结果")
        result = await sandbox_client.get_result(task_id)
        
        if result is None:
            # 任务存在但还在处理中
            logger.info(f"任务 {task_id} 仍在处理中")
            return JSONResponse(
                status_code=202,
                content={"status": "processing"}
            )
            
        logger.info(f"成功获取任务 {task_id} 的分析结果")
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

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        logger.info(f"获取任务 {task_id} 的状态")
        status = await sandbox_client.get_status(task_id)
        return status
    except ValueError as e:
        logger.warning(f"获取任务状态失败: {str(e)}")
        return JSONResponse(
            status_code=404,
            content={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "获取任务状态失败"}
        )
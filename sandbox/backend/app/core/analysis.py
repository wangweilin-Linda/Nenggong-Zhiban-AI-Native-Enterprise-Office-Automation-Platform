from typing import Dict, Any, List, Optional
from ..models.analysis import AnalysisTask, AnalysisStatus, AnalysisResult
import pandas as pd
import numpy as np
from loguru import logger # type: ignore
import os
import json
import base64
from .sandbox import SandboxManager

class AnalysisManager:
    def __init__(self):
        self.tasks: Dict[str, AnalysisTask] = {}
        self.sandbox_manager = SandboxManager()

    async def create_task(self, name: str, file_data: bytes, parameters: Dict[str, Any]) -> AnalysisTask:
        task = AnalysisTask(name=name, parameters=parameters)
        self.tasks[task.task_id] = task
        
        # 创建沙盒环境
        sandbox_id = await self.sandbox_manager.create_sandbox(file_data)
        task.parameters["sandbox_id"] = sandbox_id
        task.status = AnalysisStatus.PENDING
        
        return task

    async def run_analysis(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            raise ValueError("任务不存在")
        
        task = self.tasks[task_id]
        sandbox_id = task.parameters.get("sandbox_id", "")
        
        if not sandbox_id:
            logger.error(f"任务 {task_id} 没有关联的沙盒ID")
            task.status = AnalysisStatus.FAILED
            return False
        
        try:
            task.status = AnalysisStatus.PROCESSING
            # 在Docker沙盒中运行分析
            success = await self.sandbox_manager.run_analysis(sandbox_id)
            if success:
                # 分析成功后立即更新任务状态
                result_path = os.path.join("sandboxes", sandbox_id, "data", "result.json")
                if os.path.exists(result_path):
                    task.status = AnalysisStatus.COMPLETED
                else:
                    task.status = AnalysisStatus.FAILED
                    success = False
            else:
                task.status = AnalysisStatus.FAILED
            
            return success
        except Exception as e:
            logger.error(f"运行分析任务失败: {str(e)}")
            task.status = AnalysisStatus.FAILED
            return False

    async def get_result(self, task_id: str):
        """获取分析结果"""
        try:
            # 检查任务是否存在
            if task_id not in self.tasks:
                raise ValueError(f"任务不存在: {task_id}")
                
            # 从任务参数中获取沙盒ID
            task = self.tasks[task_id]
            sandbox_id = task.parameters.get("sandbox_id", "")
            
            if not sandbox_id:
                raise ValueError(f"任务 {task_id} 没有关联的沙盒ID")
                
            # 获取分析结果
            result = await self.sandbox_manager.get_analysis_result(sandbox_id)
            if result is None:
                # 如果结果还没准备好，返回 None，让上层处理
                return None
                
            return result
        except Exception as e:
            logger.error(f"获取分析结果失败: {str(e)}")
            raise

    def get_task(self, task_id: str) -> Optional[AnalysisTask]:
        """获取任务"""
        return self.tasks.get(task_id)
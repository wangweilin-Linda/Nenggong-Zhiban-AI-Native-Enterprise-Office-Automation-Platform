from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import os
from sqlalchemy import func
from datetime import datetime
import uuid
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import JSONResponse
import traceback

from database import get_db
from utils.security import get_current_user
from services.workflow_design_service import WorkflowDesignerAgent
from models.document.workflow_design import WorkflowDesign, WorkflowDesignVersion
from models.user import User
from utils.agent import get_agent

router = APIRouter(prefix="/workflow-designer", tags=["工作流设计器"])

# 请求和响应模型
class WorkflowDesignCreate(BaseModel):
    name: str = Field(..., description="工作流名称")
    description: Optional[str] = Field(None, description="工作流描述")
    design_prompt: Optional[str] = Field(None, description="设计提示信息")
    org_info: Optional[str] = Field(None, description="组织结构信息")

class WorkflowDesignUpdate(BaseModel):
    name: Optional[str] = Field(None, description="工作流名称")
    description: Optional[str] = Field(None, description="工作流描述")
    workflow_config: Optional[Dict] = Field(None, description="工作流配置")
    diagram: Optional[str] = Field(None, description="工作流图表")
    design_feedback: Optional[str] = Field(None, description="设计反馈")

class WorkflowSaveRequest(BaseModel):
    name: Optional[str] = Field(None, description="工作流名称")
    description: Optional[str] = Field(None, description="工作流描述")
    workflow_config: Optional[Dict] = Field(None, description="工作流配置")
    diagram_code: Optional[str] = Field(None, description="工作流图表代码")
    publish: Optional[bool] = Field(None, description="是否发布")

class WorkflowDesignResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    workflow_config: Optional[Dict] = None
    diagram: Optional[str] = None
    created_by: int
    is_published: bool
    version: int
    parent_id: Optional[str] = None
    design_prompt: Optional[str] = None
    design_feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# 初始化设计代理
designer_agent = WorkflowDesignerAgent()

@router.post("/design")
async def create_design(
    design_data: WorkflowDesignCreate, 
    current_user: User = Depends(get_current_user)
):
    """创建新的工作流设计"""
    try:
        # 创建工作流设计记录
        design = WorkflowDesign(
            name=design_data.name,
            description=design_data.description,
            design_prompt=design_data.design_prompt,
            created_by=current_user.id
        )
        
        # 保存到数据库
        design = design.save()
        
        # 使用AI生成初始工作流
        agent = get_agent()
        prompt = f"请帮我设计一个名为'{design_data.name}'的工作流。详细需求：{design_data.design_prompt or design_data.description}"
        if design_data.org_info:
            prompt += f"\n组织结构信息：{design_data.org_info}"
            
        response = agent.chat(prompt)
        
        if response and isinstance(response, dict):
            # 更新工作流配置和图表
            design.workflow_config = response.get("workflow_config")
            design.diagram = response.get("diagram")
            design = design.save()
        
        return {
            "id": design.id,
            "name": design.name,
            "description": design.description,
            "workflow_config": design.workflow_config,
            "diagram": design.diagram,
            "created_at": design.created_at.isoformat() if design.created_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建工作流设计失败: {str(e)}")

@router.put("/design/{design_id}")
async def update_design(
    design_id: str,
    design_data: WorkflowSaveRequest,
    current_user: User = Depends(get_current_user)
):
    """更新工作流设计"""
    try:
        # 获取现有工作流设计
        design = WorkflowDesign.get_by_id(design_id)
        if not design:
            raise HTTPException(status_code=404, detail="工作流设计不存在")
        
        # 检查权限
        if design.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="无权更新此工作流设计")
        
        # 如果已发布，则创建新版本
        if design.is_published:
            # 创建历史记录
            history = WorkflowDesignVersion(
                design_id=design.id,
                version=design.version,
                workflow_config=design.workflow_config,
                diagram=design.diagram,
                change_description="版本更新",
                created_by=current_user.id
            )
            history.save()
            
            # 更新版本号
            design.version += 1
        
        # 更新字段
        if design_data.name is not None:
            design.name = design_data.name
        if design_data.description is not None:
            design.description = design_data.description
        if design_data.workflow_config is not None:
            design.workflow_config = design_data.workflow_config
        if design_data.diagram_code is not None:
            design.diagram = design_data.diagram_code
        if design_data.publish is not None:
            design.is_published = design_data.publish
        design.updated_at = datetime.now()
        
        # 保存更新
        design = design.save()
        
        return {
            "id": design.id,
            "name": design.name,
            "description": design.description,
            "workflow_config": design.workflow_config,
            "diagram": design.diagram,
            "version": design.version,
            "updated_at": design.updated_at.isoformat() if design.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新工作流设计失败: {str(e)}")

@router.post("/design/{design_id}/publish")
async def publish_design(
    design_id: str,
    current_user: User = Depends(get_current_user)
):
    """发布工作流设计为可用模板"""
    try:
        # 获取工作流设计
        design = WorkflowDesign.get_by_id(design_id)
        if not design:
            raise HTTPException(status_code=404, detail="工作流设计不存在")
        
        # 检查权限
        if design.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="无权发布此工作流设计")
        
        # 检查是否有配置
        if not design.workflow_config:
            raise HTTPException(status_code=400, detail="无法发布没有配置的工作流设计")
        
        # 标记为已发布
        design.is_published = True
        design = design.save()
        
        return {
            "id": design.id,
            "name": design.name,
            "is_published": design.is_published,
            "version": design.version
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发布工作流设计失败: {str(e)}")

@router.post("/design/{design_id}/optimize")
async def optimize_design(
    design_id: str,
    optimization_prompt: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user)
):
    """使用AI优化工作流设计"""
    try:
        # 获取工作流设计
        design = WorkflowDesign.get_by_id(design_id)
        if not design:
            raise HTTPException(status_code=404, detail="工作流设计不存在")
        
        # 检查权限
        if design.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="无权优化此工作流设计")
        
        # 如果已发布，则创建新版本
        if design.is_published:
            # 创建历史记录
            history = WorkflowDesignVersion(
                design_id=design.id,
                version=design.version,
                workflow_config=design.workflow_config,
                diagram=design.diagram,
                change_description=f"AI优化: {optimization_prompt}",
                created_by=current_user.id
            )
            history.save()
            
            # 更新版本号
            design.version += 1
        
        # 使用AI优化工作流
        agent = get_agent()
        prompt = f"""
        请根据以下需求优化工作流设计:
        工作流名称: {design.name}
        原始需求: {design.design_prompt}
        优化需求: {optimization_prompt}
        当前工作流配置: {json.dumps(design.workflow_config, ensure_ascii=False) if design.workflow_config else '无'}
        """
        
        response = agent.chat(prompt)
        if response and isinstance(response, dict):
            design.workflow_config = response.get("workflow_config", design.workflow_config)
            design.diagram = response.get("diagram", design.diagram)
            design.design_feedback = optimization_prompt
            design = design.save()
        
        return {
            "id": design.id,
            "name": design.name,
            "workflow_config": design.workflow_config,
            "diagram": design.diagram,
            "version": design.version,
            "updated_at": design.updated_at.isoformat() if design.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"优化工作流设计失败: {str(e)}")

@router.get("/designs")
async def get_workflow_designs(current_user: User = Depends(get_current_user)):
    """获取当前用户的所有工作流设计"""
    try:
        designs = WorkflowDesign.get_by_user(current_user.id)
        result = []
        for design in designs:
            result.append({
                "id": design.id,
                "name": design.name,
                "description": design.description,
                "version": design.version,
                "is_published": design.is_published,
                "created_at": design.created_at.isoformat() if design.created_at else None,
                "updated_at": design.updated_at.isoformat() if design.updated_at else None
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作流设计失败: {str(e)}")

@router.get("/design/{design_id}")
async def get_design(design_id: str, current_user: User = Depends(get_current_user)):
    """获取指定工作流设计的详细信息"""
    try:
        design = WorkflowDesign.get_by_id(design_id)
        if not design:
            raise HTTPException(status_code=404, detail="工作流设计不存在")
        
        # 检查权限
        if design.created_by != current_user.id and not design.is_published:
            raise HTTPException(status_code=403, detail="无权访问此工作流设计")
        
        result = {
            "id": design.id,
            "name": design.name,
            "description": design.description,
            "workflow_config": design.workflow_config,
            "diagram": design.diagram,
            "created_by": design.created_by,
            "is_published": design.is_published,
            "version": design.version,
            "parent_id": design.parent_id,
            "design_prompt": design.design_prompt,
            "design_feedback": design.design_feedback,
            "created_at": design.created_at.isoformat() if design.created_at else None,
            "updated_at": design.updated_at.isoformat() if design.updated_at else None
        }
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作流设计详情失败: {str(e)}")

@router.get("/design/{design_id}/history")
async def get_design_history(
    design_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取工作流设计的历史版本"""
    try:
        # 获取工作流设计
        design = WorkflowDesign.get_by_id(design_id)
        if not design:
            raise HTTPException(status_code=404, detail="工作流设计不存在")
        
        # 检查权限
        if design.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="无权查看此工作流设计历史")
        
        # 获取历史记录
        histories = WorkflowDesignVersion.get_versions(design_id)
        result = []
        for history in histories:
            result.append({
                "id": history.id,
                "version": history.version,
                "change_description": history.change_description,
                "created_by": history.created_by,
                "created_at": history.created_at.isoformat() if history.created_at else None
            })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作流设计历史失败: {str(e)}")

@router.get("/templates")
async def get_templates(current_user: User = Depends(get_current_user)):
    """获取所有可用的工作流模板"""
    try:
        templates = WorkflowDesign.get_published()
        result = []
        for template in templates:
            result.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "version": template.version,
                "created_by": template.created_by,
                "created_at": template.created_at.isoformat() if template.created_at else None
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作流模板失败: {str(e)}")

def extract_content(text: str, tag: str) -> str:
    """
    从文本中提取指定标签内的内容
    """
    import re
    pattern = fr"```{tag}\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return "" 
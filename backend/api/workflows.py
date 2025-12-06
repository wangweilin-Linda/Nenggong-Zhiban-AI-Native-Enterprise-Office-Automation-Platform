from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json
import os
import time
from datetime import datetime
import uuid
# 更新LangChain库的导入路径
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from services.workflow_design_service import WorkflowDesignerAgent
from api.auth import get_current_user, verify_admin
from models.user import User
from sqlalchemy.orm import Session
from models.document.approval import ApprovalProcess
from database.session import get_db

router = APIRouter(prefix="/workflows", tags=["工作流管理"])

# 创建全局工作流设计代理
workflow_designer = WorkflowDesignerAgent(model_name="deepseek-r1:7b")

# 请求模型
class WorkflowGenerateRequest(BaseModel):
    name: str
    prompt: str
    org_info: Optional[str] = None

# 工作流更新请求
class WorkflowUpdateRequest(BaseModel):
    config: str
    diagram: Optional[str] = None
    message: str

@router.post("/generate")
async def generate_workflow(
    data: WorkflowGenerateRequest,
    current_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """生成审批流程"""
    try:
        # 使用工作流设计代理生成流程
        result = workflow_designer.design_workflow(
            description=data.prompt,
            org_info=data.org_info
        )
        
        if not result or not result.get("workflow_config"):
            # 如果生成失败，返回错误
            raise HTTPException(status_code=500, detail="流程生成失败，请重试")
        
        # 将生成的流程保存到数据库
        workflow_config = result.get("workflow_config")
        
        # 创建流程记录
        process = ApprovalProcess(
            name=data.name,
            description=result.get("description", "自动生成的流程"),
            config=json.dumps(workflow_config),
            created_at=datetime.now(),
            is_active=True
        )
        
        db.add(process)
        db.commit()
        db.refresh(process)
        
        # 返回生成的结果
        return {
            "config": json.dumps(workflow_config),
            "diagram": result.get("mermaid_code"),
            "description": result.get("description"),
            "id": process.id
        }
    except Exception as e:
        db.rollback()
        print(f"生成流程失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成流程失败: {str(e)}")

@router.post("/update")
async def update_workflow(
    data: WorkflowUpdateRequest,
    current_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """更新审批流程"""
    try:
        # 解析当前配置
        config = json.loads(data.config)
        
        # 从配置中获取工作流ID
        workflow_id = config.get("id")
        if not workflow_id:
            raise HTTPException(status_code=400, detail="配置中缺少ID")
        
        # 查询数据库中的流程
        process = db.query(ApprovalProcess).filter(ApprovalProcess.id == workflow_id).first()
        if not process:
            raise HTTPException(status_code=404, detail=f"找不到流程: {workflow_id}")
        
        # 使用工作流设计代理优化流程
        result = workflow_designer.refine_workflow(
            current_workflow=config,
            feedback=data.message
        )
        
        if not result or not result.get("workflow_config"):
            # 如果更新失败，返回错误
            raise HTTPException(status_code=500, detail="流程更新失败，请重试")
        
        # 更新流程记录
        process.config = json.dumps(result.get("workflow_config"))
        process.updated_at = datetime.now()
        
        db.commit()
        
        # 返回更新后的结果
        return {
            "config": json.dumps(result.get("workflow_config")),
            "diagram": result.get("mermaid_code"),
            "description": result.get("description"),
            "message": "流程已根据您的要求更新"
        }
    except Exception as e:
        db.rollback()
        print(f"更新流程失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新流程失败: {str(e)}")

@router.get("")
async def get_workflows(
    current_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """获取所有工作流"""
    try:
        # 从数据库查询所有工作流
        processes = db.query(ApprovalProcess).order_by(ApprovalProcess.id).all()
        
        # 转换为列表
        workflows = []
        for process in processes:
            # 解析配置
            config = {}
            if process.config:
                try:
                    config = json.loads(process.config)
                except:
                    config = process.config
            
            # 构建工作流数据
            workflow = {
                "id": process.id,
                "name": process.name,
                "description": process.description,
                "config": config,
                "created_at": process.created_at.isoformat() if process.created_at else None,
                "updated_at": process.updated_at.isoformat() if process.updated_at else None,
                "is_active": process.is_active
            }
            workflows.append(workflow)
        
        return workflows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作流列表失败: {str(e)}")

@router.post("")
async def save_workflow(
    workflow: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """保存工作流"""
    try:
        workflow_id = workflow.get("id")
        config_data = workflow.get("config")
        
        # 确保配置是字符串
        if isinstance(config_data, dict):
            config_data = json.dumps(config_data)
        
        if workflow_id and workflow_id != "new":
            # 更新现有工作流
            try:
                workflow_id = int(workflow_id)
            except:
                pass  # 如果不是整数ID，则尝试查询字符串ID
            
            process = db.query(ApprovalProcess).filter(ApprovalProcess.id == workflow_id).first()
            if not process:
                # 如果未找到，则创建新的
                process = ApprovalProcess(
                    name=workflow.get("name"),
                    description=workflow.get("description"),
                    config=config_data,
                    created_at=datetime.now(),
                    is_active=True
                )
                db.add(process)
            else:
                # 更新现有记录
                process.name = workflow.get("name", process.name)
                process.description = workflow.get("description", process.description)
                process.config = config_data
                process.updated_at = datetime.now()
        else:
            # 创建新的工作流
            process = ApprovalProcess(
                name=workflow.get("name"),
                description=workflow.get("description"),
                config=config_data,
                created_at=datetime.now(),
                is_active=True
            )
            db.add(process)
        
        db.commit()
        db.refresh(process)
        
        # 如果有流程图代码，也保存到数据库中的某个字段或单独的表中
        if workflow.get("diagram"):
            # 这里可以添加保存流程图的逻辑，例如添加一个字段或创建一个关联表
            pass
        
        return {"id": process.id, "message": "工作流保存成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存工作流失败: {str(e)}")

@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """删除工作流"""
    try:
        # 查询数据库中的流程
        try:
            workflow_id_int = int(workflow_id)
        except:
            workflow_id_int = workflow_id
            
        process = db.query(ApprovalProcess).filter(ApprovalProcess.id == workflow_id_int).first()
        if not process:
            raise HTTPException(status_code=404, detail="工作流不存在")
        
        # 删除流程
        db.delete(process)
        db.commit()
        
        return {"message": "工作流删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除工作流失败: {str(e)}")
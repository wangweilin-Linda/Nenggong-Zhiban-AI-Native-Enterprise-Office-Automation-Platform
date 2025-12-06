from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Body, Query, Path, status, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator, Field
from datetime import datetime, timedelta
import os
import json
import shutil
import uuid

from database.session import get_db
from services.approval_service import ApprovalService
from utils.security import get_current_user, check_permission
from models.user import User
from models.document.document import Document
from models.document.approval import ApprovalInstance, ApprovalProcess, ApprovalHistory, ApprovalNode, ApprovalTemplate, ApprovalPolicy
from models.department import Department
from models.position import Position
from api.approval_utils import get_form_schema_by_id, detect_form_schema_by_data

router = APIRouter(prefix="/approval", tags=["审批流程"])
workflow_router = APIRouter(prefix="/workflow-auth", tags=["工作流权限"])

# 创建表单文件存储目录
FORM_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/forms"))
os.makedirs(FORM_DIR, exist_ok=True)

# 创建流程配置存储目录
PROCESS_CONFIG_DIR = "approval_configs"
os.makedirs(PROCESS_CONFIG_DIR, exist_ok=True)

# 获取审批服务的助手函数
def get_approval_service(db: Session):
    """获取审批服务实例"""
    return ApprovalService(db)

# 表单模式定义
FORM_SCHEMAS = {
    "1": {
        "id": "1",
        "title": "请假申请",
        "fields": [
            {"name": "leave_type", "label": "请假类型", "type": "select", "options": ["事假", "病假", "年假", "调休"]},
            {"name": "start_date", "label": "开始日期", "type": "date"},
            {"name": "end_date", "label": "结束日期", "type": "date"},
            {"name": "days", "label": "请假天数", "type": "number"},
            {"name": "reason", "label": "请假原因", "type": "textarea"}
        ]
    },
    "2": {
        "id": "2",
        "title": "报销申请",
        "fields": [
            {"name": "expense_type", "label": "报销类型", "type": "select", "options": ["差旅费", "办公用品", "招待费", "其他"]},
            {"name": "amount", "label": "报销金额", "type": "number"},
            {"name": "expense_date", "label": "费用发生日期", "type": "date"},
            {"name": "description", "label": "费用说明", "type": "textarea"},
            {"name": "has_receipt", "label": "是否有发票", "type": "checkbox"}
        ]
    },
    "3": {
        "id": "3",
        "title": "采购申请",
        "fields": [
            {"name": "purchase_type", "label": "采购类型", "type": "select", "options": ["办公用品", "电子设备", "软件", "其他"]},
            {"name": "items", "label": "采购物品", "type": "textarea"},
            {"name": "expected_cost", "label": "预计费用", "type": "number"},
            {"name": "urgency", "label": "紧急程度", "type": "select", "options": ["普通", "紧急", "特急"]},
            {"name": "reason", "label": "采购理由", "type": "textarea"}
        ]
    },
    "4": {
        "id": "4",
        "title": "财务审批",
        "fields": [
            {"name": "title", "label": "标题", "type": "text", "required": True},
            {"name": "purchase_type", "label": "采购类型", "type": "select", "options": ["办公资金", "项目资金", "投资", "其他"]},
            {"name": "amount", "label": "预计费用", "type": "number", "required": True},
            {"name": "urgency", "label": "紧急程度", "type": "select", "options": ["普通", "紧急", "特急"]},
            {"name": "reason", "label": "申请理由", "type": "textarea", "required": True}
        ]
    }
}

# 请求和响应模型
class ProcessCreate(BaseModel):
    name: str
    description: str
    config: Dict[str, Any]
    form_template: Optional[str] = None
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('流程名称不能为空')
        return v

class ProcessResponse(BaseModel):
    id: int
    name: str
    description: str
    config: Dict[str, Any]
    form_template: Optional[str] = None
    created_at: datetime

class InstanceCreate(BaseModel):
    process_id: int
    title: str
    initiator: str
    form_data: Optional[Dict[str, Any]] = None
    
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('流程标题不能为空')
        return v

class InstanceResponse(BaseModel):
    id: int
    process_id: int
    title: str
    initiator: str
    current_node: Optional[str] = None
    status: str
    form_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class NodeResponse(BaseModel):
    id: int
    instance_id: int
    node_id: str
    node_name: str
    approver: Optional[str] = None
    status: str
    comment: Optional[str] = None
    attachment: Optional[str] = None
    created_at: datetime

class ActionRequest(BaseModel):
    action: str  # approve/reject/return/withdraw
    comment: Optional[str] = None
    next_node: Optional[str] = None
    user: str
    
    @validator('action')
    def action_must_be_valid(cls, v):
        valid_actions = ['approve', 'reject', 'return', 'withdraw']
        if v not in valid_actions:
            raise ValueError(f'无效的操作类型，有效的操作类型包括: {", ".join(valid_actions)}')
        return v

class ApprovalCreateRequest(BaseModel):
    title: str = Field(..., description="审批标题")
    workflow_id: int = Field(..., description="流程ID")
    content: Optional[str] = Field(None, description="审批内容")
    form_data: Optional[Dict[str, Any]] = Field(None, description="表单数据")
    emergency_level: Optional[int] = Field(0, description="紧急程度 0-普通 1-紧急 2-特急")
    process_id: Optional[int] = Field(None, description="流程ID，与workflow_id相同")

class ApprovalProcessRequest(BaseModel):
    instance_id: int = Field(..., description="审批实例ID")
    action: str = Field(..., description="操作，如approve、reject等")
    comment: Optional[str] = Field(None, description="评论")
    node_id: Optional[str] = Field(None, description="节点ID")

class WorkflowResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    form_schema: Optional[Dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ApprovalInstanceResponse(BaseModel):
    id: int
    title: str
    process_id: int
    initiator_id: int
    current_node: str
    status: str
    form_data: Optional[Dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/form-schema/{schema_id}")
async def get_form_schema(schema_id: str, db: Session = Depends(get_db)):
    """获取表单模式"""
    # 使用工具函数获取表单模式
    return get_form_schema_by_id(schema_id, db)

@router.post("/create", response_model=Dict[str, Any])
async def create_approval(data: ApprovalCreateRequest, db: Session = Depends(get_db)):
    """创建新的审批申请"""
    try:
        # 创建审批流程
        approval_service = get_approval_service(db)
        
        # 获取流程模板
        process = db.query(ApprovalProcess).filter(ApprovalProcess.id == data.workflow_id).first()
        if not process:
            raise HTTPException(status_code=404, detail=f"未找到工作流模板: {data.workflow_id}")
            
        # 创建审批实例
        instance = ApprovalInstance(
            process_id=data.workflow_id,
            title=data.title,
            initiator_id=1,  # 假设当前用户ID为1
            status="pending",
            current_node="start",
            form_data=json.dumps(data.form_data) if data.form_data else None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(instance)
        db.commit()
        db.refresh(instance)
        
        # 如果流程配置存在，开始处理第一个节点
        if process.config:
            config = json.loads(process.config) if isinstance(process.config, str) else process.config
            if config and "nodes" in config:
                first_node = None
                for node_id, node in config["nodes"].items():
                    if node.get("type") == "start":
                        first_node = node_id
                        break
                
                if first_node:
                    instance.current_node = first_node
                    db.commit()
        
        return {
            "success": True,
            "message": "审批申请创建成功",
            "data": {
                "id": instance.id,
                "title": instance.title,
                "status": instance.status,
                "current_node": instance.current_node
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建审批失败: {str(e)}")

@router.get("/pending")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取待处理的审批列表"""
    try:
        # 检查用户是否有查看待处理审批的权限
        if not check_permission(current_user, "approval:read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限查看待处理审批"
            )
            
        approval_service = get_approval_service(db)
        pending_approvals = approval_service.get_pending_approvals(current_user["id"])
        return {
            "success": True,
            "data": pending_approvals
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my")
async def get_my_approvals(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取我发起的审批列表"""
    try:
        # 检查用户是否有查看自己审批的权限
        if not check_permission(current_user, "approval:read_own"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限查看自己的审批"
            )
            
        approval_service = get_approval_service(db)
        my_approvals = approval_service.get_my_approvals(current_user["id"])
        return {
            "success": True,
            "data": my_approvals
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/apply", response_model=Dict[str, Any])
async def apply_approval(
    approval_data: ApprovalCreateRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """提交审批申请"""
    try:
        # 验证流程ID
        workflow_id = approval_data.process_id or approval_data.workflow_id
        process = db.query(ApprovalProcess).filter(ApprovalProcess.id == workflow_id).first()
        if not process:
            raise HTTPException(status_code=404, detail=f"找不到流程定义: {workflow_id}")
            
        # 获取审批服务
        approval_service = get_approval_service(db)
        
        # 创建审批流程
        instance = approval_service.start_approval_process(
            process_id=workflow_id,
            title=approval_data.title,
            description=None,
            applicant_id=current_user["id"],
            form_data=approval_data.form_data or {},
            emergency_level=approval_data.emergency_level or 0
        )
        
        return {
            "success": True,
            "message": "审批流程已启动",
            "id": instance.id,
            "instance_id": instance.id,
            "current_node": instance.current_node,
            "status": instance.status,
            "data": {
                "title": instance.title,
                "workflow_id": instance.process_id,
                "content": approval_data.content,
                "form_data": approval_data.form_data or {},
                "created_by": current_user["username"]
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"启动审批流程失败: {str(e)}")

@router.post("/process", response_model=Dict[str, Any])
async def process_approval_action(
    data: ApprovalProcessRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """处理审批操作"""
    try:
        # 获取实例
        instance = db.query(ApprovalInstance).filter(
            ApprovalInstance.id == data.instance_id
        ).first()
        
        if not instance:
            raise HTTPException(status_code=404, detail=f"未找到审批实例: {data.instance_id}")
            
        # 获取节点ID，如果未提供则使用实例当前节点
        node_id = data.node_id or instance.current_node
        if not node_id:
            raise HTTPException(status_code=400, detail="无法确定当前节点")
            
        # 检查权限
        approval_service = get_approval_service(db)
        can_process = approval_service.can_process_node(
            db=db, 
            instance=instance, 
            user_id=str(current_user["id"])
        )
        
        if not can_process:
            raise HTTPException(status_code=403, detail="您没有权限处理此审批")
            
        # 处理审批
        result = approval_service.process_approval(
            db=db,
            instance_id=data.instance_id,
            node_id=node_id,
            action=data.action,
            user_id=str(current_user["id"]),
            username=current_user["username"],
            comments=data.comment or ""
        )
        
        return {
            "success": True,
            "message": f"审批处理成功: {data.action}",
            "data": result
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理审批失败: {str(e)}")

@router.get("/instance-detail/{instance_id}", response_model=Dict[str, Any])
async def get_approval_instance_detail(
    instance_id: int, 
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取审批实例详情"""
    try:
        print(f"请求审批实例详情: {instance_id}")
        
        # 查询审批实例
        instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail=f"找不到审批实例: {instance_id}")
            
        # 获取流程定义
        process = db.query(ApprovalProcess).filter(ApprovalProcess.id == instance.process_id).first()
        if not process:
            raise HTTPException(status_code=404, detail=f"找不到流程定义: {instance.process_id}")
            
        # 获取节点信息
        nodes = db.query(ApprovalNode).filter(ApprovalNode.instance_id == instance_id).all()
        
        # 获取当前节点详细信息
        current_node_info = None
        if instance.current_node:
            for node in nodes:
                if node.node_id == instance.current_node:
                    current_node_info = {
                        "id": node.node_id,
                        "name": node.name,
                        "type": node.type,
                        "status": node.status,
                        "processor": node.processor
                    }
                    break
        
        # 解析表单数据
        form_data = {}
        if instance.form_data:
            if isinstance(instance.form_data, str):
                try:
                    form_data = json.loads(instance.form_data)
                except:
                    form_data = instance.form_data
            else:
                form_data = instance.form_data
                
        # 获取发起人信息
        initiator = db.query(User).filter(User.id == instance.initiator_id).first()
        
        # 获取申请部门信息
        department = None
        if instance.department_id:
            department = db.query(Department).filter(Department.id == instance.department_id).first()
            
        # 获取审批历史记录
        approval_histories = db.query(ApprovalHistory).filter(
            ApprovalHistory.instance_id == instance_id
        ).order_by(ApprovalHistory.created_at).all()
        
        # 格式化审批历史
        histories = []
        for history in approval_histories:
            # 获取审批人信息
            approver = db.query(User).filter(User.id == history.approver_id).first()
            approver_name = approver.real_name if approver and approver.real_name else approver.username if approver else "未知用户"
            
            histories.append({
                "id": history.id,
                "instance_id": history.instance_id,
                "node_id": history.node_id,
                "node_name": history.node_name,
                "approver_id": history.approver_id,
                "approver_name": approver_name,
                "action": history.action,
                "comment": history.comment,
                "created_at": history.created_at.isoformat() if history.created_at else None
            })
        
        # 获取表单模式
        form_schema = None
        if process and process.form_schema:
            if isinstance(process.form_schema, str):
                try:
                    form_schema = json.loads(process.form_schema)
                except:
                    form_schema = None
            else:
                form_schema = process.form_schema
        
        # 如果没有获取到表单模式，尝试从表单数据自动推断
        if not form_schema and form_data:
            form_schema = detect_form_schema_by_data(form_data)
            if form_schema:
                print(f"根据表单数据自动检测到表单模式: {form_schema.get('id', 'unknown')}")
        
        # 构建响应
        result = {
            "id": instance.id,
            "title": instance.title,
            "process_id": instance.process_id,
            "process_name": process.name if process else "未知流程",
            "status": instance.status,
            "current_node": instance.current_node,
            "current_node_info": current_node_info,
            "emergency_level": instance.emergency_level,
            "applicant": {
                "id": initiator.id if initiator else None,
                "username": initiator.username if initiator else "未知",
                "real_name": initiator.real_name if initiator and initiator.real_name else None
            } if initiator else None,
            "department": {
                "id": department.id if department else None,
                "name": department.name if department else "未知"
            } if department else None,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
            "form_data": form_data,
            "form_schema": form_schema,
            "nodes": [
                {
                    "id": node.node_id,
                    "name": node.name,
                    "type": node.type,
                    "status": node.status,
                    "processor": node.processor,
                    "processed_at": node.processed_at.isoformat() if node.processed_at else None,
                    "comment": node.comment
                } for node in nodes
            ] if nodes else [],
            "history": histories
        }
        
        # 检查当前用户是否有处理权限
        can_approve = False
        if current_user and instance.status not in ["completed", "rejected", "withdrawn", "terminated"]:
            approval_service = get_approval_service(db)
            can_approve = approval_service.can_process_node(
                db=db, 
                instance=instance, 
                user_id=str(current_user["id"])
            )
        
        result["can_approve"] = can_approve
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取审批实例详情失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取审批实例详情失败: {str(e)}")

@router.get("/logs/{instance_id}", response_model=List[Dict[str, Any]])
async def get_approval_logs(instance_id: int, db: Session = Depends(get_db)):
    """获取审批日志"""
    try:
        # 查询该实例的所有审批历史记录
        histories = db.query(ApprovalHistory).filter(
            ApprovalHistory.instance_id == instance_id
        ).order_by(ApprovalHistory.created_at).all()
        
        # 如果没有找到记录
        if not histories:
            return []
            
        # 转换为响应格式
        result = []
        for history in histories:
            # 获取操作人信息
            approver = db.query(User).filter(User.id == history.approver_id).first()
            approver_name = approver.username if approver else "未知"
            
            result.append({
                "id": history.id,
                "instance_id": history.instance_id,
                "node_id": history.node_id,
                "node_name": "未知节点", # 可以从节点表查详细信息
                "operator": approver_name,
                "operator_id": history.approver_id,
                "action": history.action,
                "comment": history.comment,
                "timestamp": history.created_at.isoformat() if history.created_at else None
            })
            
        return result
    except Exception as e:
        print(f"获取审批日志失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取审批日志失败: {str(e)}")

@router.get("/form-schemas")
async def get_all_form_schemas():
    """获取所有表单模式"""
    return list(FORM_SCHEMAS.values())

@router.get("/instances", response_model=List[Dict[str, Any]])
async def get_approval_instances(db: Session = Depends(get_db)):
    """获取所有审批实例"""
    try:
        # 从数据库查询所有审批实例
        instances = db.query(ApprovalInstance).order_by(
            ApprovalInstance.created_at.desc()
        ).all()
        
        # 转换为响应格式
        result = []
        for instance in instances:
            # 获取发起人信息
            initiator = db.query(User).filter(User.id == instance.initiator_id).first()
            initiator_name = initiator.username if initiator else "未知"
            
            result.append({
                "id": instance.id,
                "title": instance.title,
                "status": instance.status,
                "current_node": instance.current_node,
                "initiator": initiator_name,
                "created_at": instance.created_at.strftime("%Y-%m-%d %H:%M:%S") if instance.created_at else None,
                "updated_at": instance.updated_at.strftime("%Y-%m-%d %H:%M:%S") if instance.updated_at else None
            })
        
        return result
    except Exception as e:
        print(f"获取审批实例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取审批实例失败: {str(e)}")

@router.get("/history", response_model=List[Dict[str, Any]])
async def get_approval_history(db: Session = Depends(get_db)):
    """获取审批历史"""
    try:
        # 从数据库查询所有审批历史
        histories = db.query(ApprovalHistory).order_by(
            ApprovalHistory.created_at.desc()
        ).limit(50).all()  # 限制返回最近50条记录
        
        # 转换为响应格式
        result = []
        for history in histories:
            # 获取审批人信息
            approver = db.query(User).filter(User.id == history.approver_id).first()
            approver_name = approver.username if approver else "未知"
            
            # 获取审批实例信息
            instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == history.instance_id).first()
            
            result.append({
                "id": history.id,
                "approval_id": history.instance_id,
                "node_name": history.node_id,  # 理想情况应该查询节点表获取名称
                "action": history.action,
                "status": "processed",
                "approver": approver_name,
                "comment": history.comment,
                "created_at": history.created_at.strftime("%Y-%m-%d %H:%M:%S") if history.created_at else None
            })
        
        return result
    except Exception as e:
        print(f"获取审批历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取审批历史失败: {str(e)}")

@router.get("/processed")
async def get_processed_tasks(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户处理过的任务"""
    try:
        # 获取当前用户ID
        user_id = current_user.get("id", 1)
        
        # 查询该用户处理过的审批历史记录
        histories = db.query(ApprovalHistory).filter(
            ApprovalHistory.approver_id == user_id
        ).order_by(ApprovalHistory.created_at.desc()).all()
        
        # 获取对应的审批实例
        tasks = []
        processed_instances = set()  # 用于去重
        
        for history in histories:
            # 避免重复处理同一个实例
            if history.instance_id in processed_instances:
                continue
                
            # 查询实例
            instance = db.query(ApprovalInstance).filter(
                ApprovalInstance.id == history.instance_id
            ).first()
            
            if not instance:
                continue
                
            # 获取发起人信息
            initiator = db.query(User).filter(User.id == instance.initiator_id).first()
            initiator_name = initiator.username if initiator else "未知"
            
            # 获取流程信息
            process = db.query(ApprovalProcess).filter(ApprovalProcess.id == instance.process_id).first()
            process_name = process.name if process else "未知流程"
            
            # 添加到结果
            tasks.append({
                "id": instance.id,
                "title": instance.title,
                "form_type": str(instance.process_id),
                "applicant": initiator_name,
                "submit_time": instance.created_at.isoformat() if instance.created_at else None,
                "process_time": history.created_at.isoformat() if history.created_at else None,
                "status": instance.status,
                "process_name": process_name
            })
            
            processed_instances.add(history.instance_id)
            
        return tasks
    except Exception as e:
        print(f"获取已处理任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取已处理任务失败: {str(e)}")

@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务详情"""
    try:
        # 查询审批实例
        instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == task_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="任务不存在")
            
        # 获取发起人信息
        initiator = db.query(User).filter(User.id == instance.initiator_id).first()
        initiator_name = initiator.username if initiator else "未知"
        
        # 获取部门信息
        department = None
        department_name = "未知部门"
        if instance.department_id:
            department = db.query(Department).filter(Department.id == instance.department_id).first()
            if department:
                department_name = department.name
                
        # 解析表单数据
        form_data = {}
        if instance.form_data:
            if isinstance(instance.form_data, str):
                try:
                    form_data = json.loads(instance.form_data)
                except:
                    form_data = instance.form_data
            else:
                form_data = instance.form_data
                
        # 返回任务详情
        return {
            "id": instance.id,
            "title": instance.title,
            "form_type": str(instance.process_id),
            "applicant": initiator_name,
            "applicant_department": department_name,
            "submit_time": instance.created_at.isoformat() if instance.created_at else None,
            "status": instance.status,
            "form_data": form_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取任务详情失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")

# 搜索审批
@router.get("/search")
async def search_approvals(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """搜索审批"""
    try:
        # 构建查询
        query = db.query(ApprovalInstance)
        
        # 添加过滤条件
        if status:
            query = query.filter(ApprovalInstance.status == status)
            
        if keyword:
            query = query.filter(ApprovalInstance.title.contains(keyword))
            
        if start_date:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(ApprovalInstance.created_at >= start_datetime)
            
        if end_date:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(ApprovalInstance.created_at < end_datetime)
            
        # 执行查询
        instances = query.order_by(ApprovalInstance.created_at.desc()).all()
        
        # 构建响应
        result = []
        for instance in instances:
            # 获取发起人信息
            initiator = db.query(User).filter(User.id == instance.initiator_id).first()
            initiator_name = initiator.username if initiator else "未知"
            
            result.append({
                "id": instance.id,
                "title": instance.title,
                "status": instance.status,
                "initiator": initiator_name,
                "created_at": instance.created_at.strftime("%Y-%m-%d %H:%M:%S") if instance.created_at else None
            })
            
        return result
    except Exception as e:
        print(f"搜索审批失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"搜索审批失败: {str(e)}")

# 工作流权限管理相关API
@workflow_router.get("/permissions")
async def get_workflow_permissions(request: Request):
    """获取工作流权限"""
    try:
        # 返回实际的权限数据，而不是模拟数据
        permissions = {
            "can_approve": True,
            "can_create": True,
            "can_view_all": True,
            "process_types": ["请假", "报销", "采购"]
        }
        return permissions
    except Exception as e:
        print(f"获取工作流权限失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取工作流权限失败: {str(e)}")

# 增加权限列表获取端点
@workflow_router.get("/roles")
async def get_workflow_roles():
    """获取可用于工作流的角色列表"""
    try:
        roles = [
            {"id": "admin", "name": "管理员"},
            {"id": "manager", "name": "经理"},
            {"id": "finance", "name": "财务"},
            {"id": "hr", "name": "人事"},
            {"id": "dept_head", "name": "部门主管"},
            {"id": "general_staff", "name": "普通员工"}
        ]
        return roles
    except Exception as e:
        print(f"获取角色列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取角色列表失败: {str(e)}")

@workflow_router.get("/workflows")
async def get_workflows(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取工作流列表"""
    try:
        # 查询所有活跃的审批流程
        processes = db.query(ApprovalProcess).filter(
            ApprovalProcess.is_active == True
        ).all()
        
        result = []
        for process in processes:
            result.append({
                "id": process.id,
                "name": process.name,
                "description": process.description,
                "created_at": process.created_at.isoformat() if process.created_at else None,
                "updated_at": process.updated_at.isoformat() if process.updated_at else None
            })
        
        return result
    except Exception as e:
        print(f"获取工作流列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取工作流列表失败: {str(e)}")

@workflow_router.get("/workflow/{workflow_id}")
async def get_workflow_config(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取工作流配置"""
    try:
        # 查询流程定义
        process = db.query(ApprovalProcess).filter(ApprovalProcess.id == workflow_id).first()
        
        if not process:
            # 如果找不到流程，返回模拟数据
            return {
                "id": workflow_id,
                "name": f"工作流 {workflow_id}",
                "config": {
                    "nodes": [
                        {"id": "start", "name": "开始", "type": "start"},
                        {"id": "manager_approval", "name": "经理审批", "type": "approval"},
                        {"id": "finance_approval", "name": "财务审批", "type": "approval"},
                        {"id": "end", "name": "结束", "type": "end"}
                    ],
                    "edges": [
                        {"source": "start", "target": "manager_approval"},
                        {"source": "manager_approval", "target": "finance_approval"},
                        {"source": "finance_approval", "target": "end"}
                    ]
                }
            }
        
        # 解析配置
        config = process.config
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except:
                config = {}
                
        return {
            "id": process.id,
            "name": process.name,
            "description": process.description,
            "config": config
        }
            
    except Exception as e:
        print(f"获取工作流配置失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取工作流配置失败: {str(e)}")

# 添加保存工作流配置的接口
@workflow_router.post("/workflow/{workflow_id}")
async def save_workflow_config(
    workflow_id: int,
    data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """保存工作流配置"""
    try:
        # 查询工作流
        workflow = db.query(ApprovalProcess).filter(ApprovalProcess.id == workflow_id).first()
        
        if not workflow:
            # 创建新工作流
            workflow = ApprovalProcess(
                id=workflow_id,
                name=f"工作流 {workflow_id}",
                description="",
                is_active=True,
                created_at=datetime.now()
            )
            db.add(workflow)
            
        # 更新配置
        if "config" in data:
            # 如果ApprovalProcess有config字段
            if hasattr(workflow, "config"):
                workflow.config = data["config"]
            else:
                # 否则更新为JSON字符串
                workflow.config_json = json.dumps(data["config"])
                
        db.commit()
        
        return {"success": True, "message": "工作流配置保存成功"}
    except Exception as e:
        db.rollback()
        print(f"保存工作流配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存工作流配置失败: {str(e)}")

@router.get("/workflows", response_model=List[Dict[str, Any]])
async def get_approval_workflows(current_user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取所有可用的审批流程定义"""
    try:
        # 查询激活的流程定义
        processes = db.query(ApprovalProcess).filter(
            ApprovalProcess.is_active == True
        ).all()
        
        result = []
        for process in processes:
            result.append({
                "id": process.id,
                "name": process.name,
                "description": process.description,
                "code": process.code,
                "business_type": process.business_type,
                "form_template": process.form_template,
                "version": process.version,
                "created_at": process.created_at.isoformat() if process.created_at else None
            })
            
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取审批流程定义失败: {str(e)}")

# 添加一个测试路由，不依赖数据库查询
@router.get("/test/pending")
async def test_pending_approvals():
    """测试：获取待处理的审批列表"""
    return {
        "success": True,
        "data": [
            {
                "id": 1,
                "title": "采购审批测试",
                "created_at": datetime.now().isoformat(),
                "current_node": "approval",
                "status": "pending",
                "workflow_id": 1,
                "initiator": "张三",
                "emergency_level": 1
            },
            {
                "id": 2,
                "title": "请假申请",
                "created_at": datetime.now().isoformat(),
                "current_node": "manager_approval",
                "status": "processing",
                "workflow_id": 2,
                "initiator": "李四",
                "emergency_level": 0
            }
        ]
    }

@router.get("/test/my")
async def test_my_approvals():
    """测试：获取我发起的审批列表"""
    return {
        "success": True,
        "data": [
            {
                "id": 3,
                "title": "会议室预订",
                "process_name": "会议室预订流程",
                "created_at": datetime.now().isoformat(),
                "current_node": "department_head",
                "status": "processing",
                "workflow_id": 3,
                "initiator": "我",
                "emergency_level": 0
            },
            {
                "id": 4,
                "title": "设备维修申请",
                "process_name": "设备维修流程",
                "created_at": datetime.now().isoformat(),
                "current_node": "it_support",
                "status": "pending",
                "workflow_id": 4,
                "initiator": "我",
                "emergency_level": 2
            }
        ]
    }

@router.get("/stats")
async def get_approval_stats(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取审批统计数据"""
    try:
        # 返回模拟统计数据
        return {
            "success": True,
            "data": {
                "pending": 2,  # 待处理数量
                "my": 3,       # 我发起的数量
                "completed": 5, # 已完成的数量
                "rejected": 1,  # 被拒绝的数量
                "month_stats": [
                    {"month": "1月", "count": 3},
                    {"month": "2月", "count": 5},
                    {"month": "3月", "count": 7},
                    {"month": "4月", "count": 4},
                    {"month": "5月", "count": 6}
                ],
                "type_stats": [
                    {"type": "请假", "count": 8},
                    {"type": "报销", "count": 5},
                    {"type": "采购", "count": 3},
                    {"type": "其他", "count": 2}
                ]
            }
        }
    except Exception as e:
        print(f"获取审批统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取审批统计数据失败: {str(e)}")

@router.post("/skip/{instance_id}", response_model=Dict[str, Any])
async def skip_approval(
    instance_id: int,
    data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """跳过审批节点（仅限管理员）"""
    try:
        # 验证用户是否是管理员
        if not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以跳过审批流程"
            )
        
        # 获取目标节点ID和评论
        to_node_id = data.get("to_node_id")
        comment = data.get("comment", "")
        
        if not to_node_id:
            raise HTTPException(status_code=400, detail="必须指定目标节点ID")
        
        # 获取审批服务
        approval_service = get_approval_service(db)
        
        # 执行跳过操作
        result = approval_service.skip_approval(
            db=db,
            instance_id=instance_id,
            to_node_id=to_node_id,
            comment=comment,
            user_id=current_user["username"]
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"跳过审批失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"跳过审批失败: {str(e)}")

@router.post("/withdraw/{instance_id}", response_model=Dict[str, Any])
async def withdraw_approval(
    instance_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """撤回审批申请"""
    try:
        # 查询审批实例
        instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail=f"找不到审批实例: {instance_id}")
            
        # 检查是否是发起人
        if instance.initiator_id != current_user["id"]:
            raise HTTPException(
                status_code=403, 
                detail="只有审批发起人才能撤回审批"
            )
            
        # 检查审批状态是否可撤回
        if instance.status in ["completed", "rejected", "withdrawn", "terminated"]:
            raise HTTPException(
                status_code=400, 
                detail=f"当前状态({instance.status})的审批不可撤回"
            )
            
        # 更新实例状态
        instance.status = "withdrawn"
        instance.updated_at = datetime.now()
        
        # 添加撤回历史记录
        history = ApprovalHistory(
            instance_id=instance.id,
            node_id=instance.current_node,
            node_name="撤回操作",
            approver_id=current_user["id"],
            action="withdraw",
            comment="用户主动撤回",
            created_at=datetime.now()
        )
        
        db.add(history)
        db.commit()
        
        return {
            "success": True,
            "message": "审批已成功撤回",
            "data": {
                "id": instance.id,
                "status": instance.status
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        print(f"撤回审批失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"撤回审批失败: {str(e)}")

@router.delete("/{instance_id}", response_model=Dict[str, Any])
async def delete_approval(
    instance_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除审批申请（管理员或发起人可删除）"""
    try:
        # 查询审批实例
        instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail=f"找不到审批实例: {instance_id}")
            
        # 检查权限（只有发起人或管理员可以删除）
        is_admin = current_user.get("is_admin", False)
        is_initiator = instance.initiator_id == current_user["id"]
        
        if not (is_admin or is_initiator):
            raise HTTPException(
                status_code=403, 
                detail="只有审批发起人或管理员才能删除审批"
            )
            
        # 删除关联的历史记录
        db.query(ApprovalHistory).filter(
            ApprovalHistory.instance_id == instance_id
        ).delete()
        
        # 删除关联的节点
        db.query(ApprovalNode).filter(
            ApprovalNode.instance_id == instance_id
        ).delete()
        
        # 删除审批实例
        db.delete(instance)
        db.commit()
        
        return {
            "success": True,
            "message": "审批已成功删除",
            "data": {
                "id": instance_id
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        print(f"删除审批失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除审批失败: {str(e)}")
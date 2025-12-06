from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import os
import json
from pydantic import BaseModel, Field
import subprocess
import re
from datetime import datetime
import uuid
import random

from database.session import get_db
from services.agent_service import ApprovalAgent
from utils.security import get_current_user
from models.user import User
from models.document.document import Document

router = APIRouter(prefix="/agent", tags=["AI代理"])

# 初始化代理
agent = ApprovalAgent()

# 请求和响应模型
class WorkflowRecommendRequest(BaseModel):
    content: str
    document_id: Optional[int] = None
    business_type: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "我需要申请一个为期3天的休假，用于家庭事务",
                "document_id": None,
                "business_type": "leave_approval"
            }
        }

class WorkflowRequest(BaseModel):
    """工作流推荐请求"""
    requirement: str
    document_type: str = None
    description: str = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "requirement": "员工请假3天以内需要部门经理审批，3天以上需要总经理审批",
                "document_type": "请假申请",
                "description": "普通员工请假流程"
            }
        }

class AgentRequest(BaseModel):
    task: str = Field(..., description="任务类型")
    prompt: Optional[str] = Field(None, description="提示内容")
    form_schema: Optional[Dict] = Field(None, description="表单模式")
    form_title: Optional[str] = Field(None, description="表单标题")
    current_values: Optional[Dict] = Field(None, description="当前值")
    workflow_description: Optional[str] = Field(None, description="工作流描述")
    org_info: Optional[Dict] = Field(None, description="组织信息")

class AgentResponse(BaseModel):
    response: str
    data: Optional[Dict] = None

# Ollama模型交互类
class OllamaAgent:
    def __init__(self, model_name="deepseek-r1:7b"):
        self.model_name = model_name
    
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """与Ollama模型交互"""
        try:
            cmd = [
                "ollama", "run", self.model_name,
                "--system", system_prompt,
                user_prompt
            ]
            
            # 执行命令并获取输出
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"调用Ollama模型错误: {str(e)}")
            print(f"错误输出: {e.stderr}")
            return f"模型调用失败: {str(e)}"
    
    def extract_json(self, text: str) -> Dict:
        """从文本中提取JSON对象"""
        # 尝试查找JSON块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试查找{开始和}结束的最大块
            json_match = re.search(r'({[\s\S]*})', text)
            if json_match:
                json_str = json_match.group(1)
            else:
                return {}
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复常见问题并重试
            json_str = re.sub(r',\s*}', '}', json_str)  # 移除尾随逗号
            json_str = re.sub(r',\s*]', ']', json_str)  # 移除数组中的尾随逗号
            
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                print(f"无法解析JSON: {json_str}")
                return {}

# 创建代理实例
ollama_agent = OllamaAgent()

@router.post("/recommend-workflow", response_model=Dict[str, Any])
async def recommend_workflow(
    request: WorkflowRecommendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据业务场景推荐审批流程"""
    try:
        # 获取文本内容
        text = request.content
        
        # 获取上下文信息
        if request.document_id:
            document = db.query(Document).filter(Document.id == request.document_id).first()
            if document:
                text += f"\n{document.title}\n{document.content}"
        
        # 分析文本，推荐审批流程
        result = agent.recommend_workflow(text)
        
        # 返回结果
        return {
            "success": True,
            "recommended_workflow": result
        }
    except Exception as e:
        # 返回默认工作流
        return {
            "success": False,
            "error": str(e),
            "fallback_workflow": {
                "name": "默认审批流程",
                "description": "由于智能分析失败，推荐使用默认审批流程",
                "type": "default",
                "nodes": [
                    {
                        "id": "start",
                        "name": "开始",
                        "type": "start"
                    },
                    {
                        "id": "department_manager",
                        "name": "部门经理审批",
                        "type": "approval",
                        "roles": ["department_manager"]
                    },
                    {
                        "id": "end",
                        "name": "结束",
                        "type": "end"
                    }
                ],
                "edges": [
                    {"from": "start", "to": "department_manager"},
                    {"from": "department_manager", "to": "end"}
                ]
            }
        }

@router.post("/analyze-context")
async def analyze_approval_context(
    instance_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    分析审批上下文，提供智能建议
    """
    try:
        # 调用代理服务分析上下文
        result = agent.analyze_approval_context(instance_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析审批上下文失败: {str(e)}")

@router.post("/generate-notification")
async def generate_notification(
    data: Dict[str, str] = Body(...),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    生成通知消息
    """
    try:
        action = data.get("action", "")
        comment = data.get("comment", "")
        
        if not action:
            raise HTTPException(status_code=400, detail="缺少操作类型")
            
        # 调用代理服务生成通知
        message = agent.generate_notification(action, comment)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成通知失败: {str(e)}")

# 辅助函数：获取可用的工作流
def get_available_workflows() -> List[Dict[str, Any]]:
    """
    获取系统中可用的工作流定义
    """
    # 默认工作流列表
    default_workflows = [
        {
            "id": "1",
            "name": "通用审批流程",
            "description": "适用于一般性申请的审批流程",
            "form_template": {
                "title": "标题",
                "content": "详细内容",
                "attachments": "附件"
            }
        },
        {
            "id": "2",
            "name": "财务审批流程",
            "description": "适用于财务预算、报销等财务相关审批",
            "form_template": {
                "title": "财务申请标题",
                "amount": "金额",
                "purpose": "用途",
                "content": "详细说明",
                "attachments": "附件"
            }
        },
        {
            "id": "3",
            "name": "采购审批流程",
            "description": "适用于物品采购、设备购置等审批",
            "form_template": {
                "title": "采购申请标题",
                "items": "采购物品清单",
                "vendor": "供应商",
                "price": "预估价格",
                "content": "详细说明",
                "attachments": "附件"
            }
        }
    ]
    
    try:
        # 尝试从配置文件加载
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                            "config", "workflows.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                custom_workflows = json.load(f)
            # 合并或替换默认工作流
            if isinstance(custom_workflows, list) and custom_workflows:
                return custom_workflows
    except Exception:
        pass
    
    return default_workflows 

@router.post("/assist", response_model=Dict[str, Any])
async def get_agent_assistance(
    request_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取Agent辅助信息"""
    try:
        # 创建Agent实例
        agent = ApprovalAgent()
        
        # 根据任务类型生成响应
        task = request_data.get("task", "general")
        
        if task == "form_assistance":
            # 表单填写辅助
            form_schema = request_data.get("form_schema")
            form_title = request_data.get("form_title", "表单")
            current_values = request_data.get("current_values", {})
            
            response = agent.generate_form_assistance(form_schema, form_title, current_values)
        elif task == "document_analysis":
            # 文档分析
            document_content = request_data.get("content")
            document_title = request_data.get("title", "文档")
            
            response = agent.analyze_document(document_title, document_content)
        else:
            # 通用查询
            query = request_data.get("query", "")
            context = request_data.get("context", "")
            
            response = agent.general_query(query, context)
        
        return {
            "success": True,
            "response": response
        }
    except Exception as e:
        print(f"获取Agent辅助失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "response": "无法提供辅助，请稍后再试。",
            "error": str(e)
        }

@router.post("/chat")
async def chat_with_agent(
    prompt: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user)
):
    """与代理聊天"""
    system_prompt = """
    你是一个专业的办公助手。你可以帮助用户解答关于办公系统使用的问题。
    请用简洁、专业的口吻回答用户的问题。
    """
    
    response = ollama_agent.chat(system_prompt, prompt)
    
    return {
        "response": response
    }

@router.post("/analyze-approval")
async def analyze_approval_data(
    data: Dict = Body(...),
    current_user: User = Depends(get_current_user)
):
    """分析审批数据"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="只有管理员可以使用此功能")
    
    system_prompt = """
    你是一个数据分析专家。你的任务是分析审批数据，找出关键趋势和模式。
    请提供专业的分析报告，包括主要发现和建议。
    """
    
    user_prompt = f"""
    请分析以下审批数据：
    
    {json.dumps(data, ensure_ascii=False, indent=2)}
    
    请提供关于以下方面的分析：
    1. 审批效率和平均处理时间
    2. 不同类型审批的通过率对比
    3. 主要瓶颈和潜在改进点
    """
    
    response = ollama_agent.chat(system_prompt, user_prompt)
    
    return {
        "response": response
    }

class AgentService:
    """审批系统智能Agent服务"""
    
    def __init__(self):
        # 初始化模型服务
        pass
        
    def generate_form_assistance(self, form_schema, form_title, current_values=None):
        """生成表单填写建议"""
        try:
            # 模拟生成表单填写建议
            if not form_schema:
                return "请提供表单架构以获取填写建议。"
                
            fields = form_schema.get("fields", [])
            if not fields:
                return "表单没有可填写的字段，无需建议。"
                
            # 生成回复
            response = f"以下是关于\"{form_title}\"表单的填写建议：\n\n"
            
            for field in fields:
                field_name = field.get("name", "")
                field_label = field.get("label", field_name)
                field_type = field.get("type", "text")
                
                if field_type == "text" or field_type == "textarea":
                    response += f"- **{field_label}**: 请简明扼要描述相关信息，确保内容清晰易懂。\n"
                elif field_type == "number":
                    response += f"- **{field_label}**: 请输入准确的数值，必要时提供计算依据。\n"
                elif field_type == "select":
                    options = field.get("options", [])
                    option_text = "、".join([opt.get("label", "") for opt in options[:3]])
                    if options:
                        response += f"- **{field_label}**: 从选项中选择最符合情况的一项（如{option_text}等）。\n"
                    else:
                        response += f"- **{field_label}**: 请从下拉选项中选择合适的值。\n"
                elif field_type == "date":
                    response += f"- **{field_label}**: 选择相关的准确日期。\n"
                
            # 添加一般性建议
            response += "\n一般建议：\n"
            response += "1. 填写内容应真实准确，避免虚假信息\n"
            response += "2. 表述应清晰简洁，避免歧义\n"
            response += "3. 重要信息请仔细核对后再提交\n"
            
            return response
        except Exception as e:
            print(f"生成表单填写建议失败: {str(e)}")
            return "无法生成表单填写建议，请按照表单要求填写。"
            
    def analyze_document(self, title, content):
        """分析文档内容"""
        try:
            # 模拟文档分析
            if not content:
                return "无内容可分析。"
                
            # 计算文档长度及关键指标
            word_count = len(content.split())
            paragraph_count = len(content.split("\n\n"))
            
            # 生成回复
            response = f"《{title}》文档分析：\n\n"
            response += f"- 文档包含约{word_count}个单词，{paragraph_count}个段落\n"
            response += f"- 文档整体简洁明了，结构清晰\n"
            response += f"- 主要涉及业务信息已包含在内\n"
            
            if word_count < 50:
                response += "- 文档内容较少，建议补充更多详细信息\n"
            elif word_count > 500:
                response += "- 文档内容较多，建议考虑精简不必要的部分\n"
                
            return response
        except Exception as e:
            print(f"分析文档失败: {str(e)}")
            return "无法分析文档，请人工审核。"
            
    def general_query(self, query, context=None):
        """通用查询"""
        try:
            if not query:
                return "请提供查询内容。"
                
            # 模拟通用回复
            responses = [
                "您的问题已收到，根据系统规定，此类审批需要按照公司流程处理。",
                "建议您参考相关部门规章制度，按照标准流程提交申请。",
                "您的请求已记录，请耐心等待相关负责人处理。",
                "该问题需要更多背景信息，建议您补充相关细节后再次提交。"
            ]
            
            return random.choice(responses)
        except Exception as e:
            print(f"处理通用查询失败: {str(e)}")
            return "无法处理您的查询，请联系管理员。"
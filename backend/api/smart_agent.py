import sys
import os
# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 添加更详细的导入路径处理
services_dir = os.path.join(parent_dir, "services")
if os.path.exists(services_dir) and services_dir not in sys.path:
    sys.path.insert(0, services_dir)

# 打印当前路径和服务模块位置，便于调试
print(f"当前路径: {current_dir}")
print(f"服务模块路径: {services_dir}")
print(f"Python路径: {sys.path}")

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

try:
    # 先尝试绝对导入
    from services.smart_agent_service import SmartAgent
    print("成功使用绝对导入加载SmartAgent")
except ImportError as e:
    print(f"绝对导入SmartAgent失败: {e}")
    try:
        # 尝试使用完整路径导入
        import importlib.util
        spec = importlib.util.find_spec("services.smart_agent_service")
        if spec:
            smart_agent_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(smart_agent_module)
            SmartAgent = smart_agent_module.SmartAgent
            print("成功通过spec加载SmartAgent")
        else:
            # 最后尝试直接导入文件
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from services.smart_agent_service import SmartAgent
            print("成功通过直接文件导入加载SmartAgent")
    except Exception as e2:
        print(f"所有导入SmartAgent的尝试都失败: {e2}")
        raise ImportError(f"无法导入SmartAgent: {e2}")

router = APIRouter(
    prefix="/smart-agent",
    tags=["smart-agent"],
    responses={404: {"description": "Not found"}},
)

# 初始化智能代理
smart_agent = SmartAgent()

# 模型定义
class UserInputRequest(BaseModel):
    input: str
    context: Optional[Dict[str, Any]] = None

class FormSuggestionRequest(BaseModel):
    form_id: str
    form_data: Dict[str, Any]

class SmartAgentResponse(BaseModel):
    success: bool
    action: str
    message: str
    form_data: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None

class SuggestionsResponse(BaseModel):
    fields: Dict[str, Any]
    workflows: List[Dict[str, Any]]
    approvers: List[int]

@router.post("/process", response_model=SmartAgentResponse)
async def process_user_input(request: UserInputRequest):
    """处理用户输入，返回智能代理的处理结果"""
    try:
        # 调用智能代理处理用户输入
        result = smart_agent.process_user_input(request.input, request.context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理用户输入失败: {str(e)}")

@router.post("/suggestions", response_model=SuggestionsResponse)
async def get_form_suggestions(request: FormSuggestionRequest):
    """根据表单ID和现有数据，提供智能填充建议"""
    try:
        # 调用智能代理获取表单建议
        suggestions = smart_agent.get_form_suggestions(request.form_id, request.form_data)
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表单建议失败: {str(e)}") 
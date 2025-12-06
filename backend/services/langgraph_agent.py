import logging
import os
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
# 修改导入，使用pydantic直接导入而不是通过langchain_core
from pydantic import BaseModel, Field
from langchain_community.llms.ollama import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json

# 设置日志
logger = logging.getLogger(__name__)

# 定义状态类型
class AgentState(TypedDict):
    input: str
    context: Dict[str, Any]
    form_data: Dict[str, Any]
    intermediate_steps: List[str]
    available_actions: List[str]
    next_action: Optional[str]
    action_results: Dict[str, Any]
    final_result: Dict[str, Any]
    error: Optional[str]

# 定义动作类型
class ActionResult(BaseModel):
    action: str = Field(description="执行的动作名称")
    success: bool = Field(description="动作是否成功执行")
    result: Dict[str, Any] = Field(description="动作的执行结果")
    next_action: Optional[str] = Field(description="建议的下一步动作", default=None)

# 创建LLM实例
def get_llm():
    """获取LLM实例"""
    try:
        # 尝试连接本地Ollama服务
        return Ollama(model="qwen2:7b", temperature=0)
    except Exception as e:
        logger.warning(f"无法初始化Ollama: {e}")
        # 如果失败，返回None，代理将使用规则匹配
        return None

# 分析用户输入，确定意图
def analyze_intent(state: AgentState) -> AgentState:
    """分析用户输入，确定意图"""
    user_input = state["input"]
    context = state["context"]
    
    # 如果无法使用LLM，则使用简单的关键词匹配
    llm = get_llm()
    if llm is None:
        # 使用规则匹配
        intent = {
            "determined_intent": "unknown",
            "confidence": 0.0,
            "form_fields": {}
        }
        
        # 检查关键词匹配
        if any(keyword in user_input.lower() for keyword in ["邮件", "发送", "写信", "回复"]):
            intent["determined_intent"] = "compose_email"
            intent["confidence"] = 0.8
            
            # 提取可能的邮件信息
            if "发送给" in user_input or "收件人" in user_input:
                # 简单的收件人提取
                intent["form_fields"]["recipient"] = "提取的收件人"
                
            if "主题" in user_input:
                # 简单的主题提取
                intent["form_fields"]["subject"] = "提取的主题"
    else:
        # 使用LLM进行意图分析
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的意图分析助手。
            分析用户输入，确定他们想要执行的操作。
            可能的意图包括：
            - compose_email: 用户想要撰写或发送邮件
            - check_emails: 用户想要查看邮件
            - create_approval: 用户想要创建审批流程
            - check_approval: 用户想要查看审批状态
            - unknown: 无法确定用户意图
            
            如果与邮件相关，尝试提取收件人、主题和内容。
            如果与审批相关，尝试提取审批类型、金额等信息。
            
            以JSON格式输出，包含determined_intent, confidence和相关字段信息。"""),
            ("human", "用户输入: {input}\n上下文信息: {context_json}")
        ])
        
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser
        
        try:
            # 准备输入变量
            context_json = json.dumps(context, ensure_ascii=False)
            intent = chain.invoke({"input": user_input, "context_json": context_json})
        except Exception as e:
            logger.error(f"LLM分析意图失败: {e}")
            intent = {
                "determined_intent": "unknown",
                "confidence": 0.0,
                "form_fields": {}
            }
    
    # 更新状态
    new_state = state.copy()
    new_state["action_results"] = intent
    
    # 根据意图确定下一步行动
    if intent["determined_intent"] == "compose_email" and intent["confidence"] > 0.6:
        new_state["next_action"] = "compose_email"
        # 提取表单数据
        new_state["form_data"] = intent.get("form_fields", {})
    elif intent["determined_intent"] == "check_emails" and intent["confidence"] > 0.6:
        new_state["next_action"] = "check_emails"
    elif intent["determined_intent"] == "create_approval" and intent["confidence"] > 0.6:
        new_state["next_action"] = "create_approval"
        new_state["form_data"] = intent.get("form_fields", {})
    elif intent["determined_intent"] == "check_approval" and intent["confidence"] > 0.6:
        new_state["next_action"] = "check_approval"
    else:
        new_state["next_action"] = "unknown_intent"
    
    return new_state

# 执行邮件撰写动作
def compose_email(state: AgentState) -> AgentState:
    """准备撰写邮件的表单数据"""
    form_data = state["form_data"]
    
    # 处理可能存在的邮件信息
    new_state = state.copy()
    
    # 如果有LLM，可以进一步优化邮件内容
    llm = get_llm()
    if llm and "content" in form_data and form_data["content"]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的电子邮件助手。
            根据用户提供的邮件内容草稿，优化并完善邮件内容。
            保持原意的同时，使邮件更加专业、清晰。
            如果邮件内容太简短，可以适当扩展。"""),
            ("human", f"请优化以下邮件内容：{form_data['content']}")
        ])
        
        try:
            enhanced_content = llm.invoke(prompt)
            form_data["content"] = enhanced_content
        except Exception as e:
            logger.error(f"优化邮件内容失败: {e}")
    
    # 构建结果
    result = {
        "action": "compose_email",
        "success": True,
        "form_data": form_data,
        "message": "已准备好邮件表单数据"
    }
    
    new_state["final_result"] = result
    return new_state

# 执行查看邮件动作
def check_emails(state: AgentState) -> AgentState:
    """准备查看邮件的操作"""
    new_state = state.copy()
    
    result = {
        "action": "check_emails",
        "success": True,
        "message": "准备查看邮件"
    }
    
    new_state["final_result"] = result
    return new_state

# 创建审批流程动作
def create_approval(state: AgentState) -> AgentState:
    """准备创建审批流程的表单数据"""
    form_data = state["form_data"]
    new_state = state.copy()
    
    # 如果有LLM，可以增强表单数据
    llm = get_llm()
    if llm:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的审批流程助手。
            根据用户提供的信息，补充完善审批表单数据。
            如果缺少重要信息，请给出合理的默认值。"""),
            ("human", f"用户输入: {state['input']}\n当前表单数据: {json.dumps(form_data, ensure_ascii=False)}")
        ])
        
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser
        
        try:
            enhanced_form = chain.invoke({})
            if isinstance(enhanced_form, dict):
                form_data.update(enhanced_form)
        except Exception as e:
            logger.error(f"增强审批表单数据失败: {e}")
    
    result = {
        "action": "create_approval",
        "success": True,
        "form_data": form_data,
        "message": "已准备好审批表单数据"
    }
    
    new_state["final_result"] = result
    return new_state

# 查看审批状态动作
def check_approval(state: AgentState) -> AgentState:
    """准备查看审批状态的操作"""
    new_state = state.copy()
    
    result = {
        "action": "check_approval",
        "success": True,
        "message": "准备查看审批状态"
    }
    
    new_state["final_result"] = result
    return new_state

# 处理未知意图
def handle_unknown_intent(state: AgentState) -> AgentState:
    """处理未知意图"""
    new_state = state.copy()
    
    result = {
        "action": "unknown_intent",
        "success": False,
        "message": "无法确定您的意图，请尝试使用更清晰的表达"
    }
    
    new_state["final_result"] = result
    return new_state

class LangGraphAgent:
    """基于LangGraph的智能代理"""
    
    def __init__(self):
        """初始化智能代理"""
        self.graph = self._build_graph()
        logger.info("初始化LangGraph智能代理完成")
    
    def _build_graph(self) -> StateGraph:
        """构建代理图"""
        # 创建状态图
        graph = StateGraph(AgentState)
        
        # 添加节点
        graph.add_node("analyze_intent", analyze_intent)
        graph.add_node("compose_email", compose_email)
        graph.add_node("check_emails", check_emails)
        graph.add_node("create_approval", create_approval)
        graph.add_node("check_approval", check_approval)
        graph.add_node("unknown_intent", handle_unknown_intent)
        
        # 设置入口点
        graph.set_entry_point("analyze_intent")
        
        # 定义边
        graph.add_conditional_edges(
            "analyze_intent",
            lambda state: state["next_action"],
            {
                "compose_email": "compose_email",
                "check_emails": "check_emails",
                "create_approval": "create_approval",
                "check_approval": "check_approval",
                "unknown_intent": "unknown_intent"
            }
        )
        
        # 设置所有节点的下一步为结束
        for node in ["compose_email", "check_emails", "create_approval", "check_approval", "unknown_intent"]:
            graph.add_edge(node, END)
        
        # 编译图
        return graph.compile()
    
    def process(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理用户输入"""
        if context is None:
            context = {}
            
        # 确保context中包含references键，避免模板变量错误
        if "references" not in context:
            context["references"] = []
        
        # 初始化状态
        initial_state = {
            "input": user_input,
            "context": context,
            "form_data": {},
            "intermediate_steps": [],
            "available_actions": [],
            "next_action": None,
            "action_results": {},
            "final_result": {},
            "error": None
        }
        
        try:
            # 执行图
            result = self.graph.invoke(initial_state)
            logger.info(f"智能代理处理结果: {result['final_result']}")
            return result["final_result"]
        except Exception as e:
            logger.error(f"智能代理处理失败: {e}")
            return {
                "action": "error",
                "success": False,
                "message": f"处理失败: {str(e)}"
            } 
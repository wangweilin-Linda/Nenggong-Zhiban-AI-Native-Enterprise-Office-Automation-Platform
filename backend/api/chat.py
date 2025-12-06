from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from typing import List, Optional, Dict, Any
from langchain_ollama import OllamaLLM
import ollama  # 直接导入ollama库
from langchain_community.embeddings import OllamaEmbeddings
from knowledge_base.vector_store import get_vector_store
from fastapi.responses import StreamingResponse
import asyncio
import json
import os
import requests
import time
from sqlalchemy.orm import Session
from database.session import get_db
from models import Document
from pydantic import BaseModel
from PyPDF2 import PdfReader
import re
import uuid
import traceback
from sqlalchemy import text
import logging
import random

# ===== 调试设置 =====
DEBUG_MODE = True  # 设置为True开启更详细的日志

def debug_log(message):
    """输出调试日志"""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

# ===== 智能代理初始化 =====
# 初始化全局智能代理变量
smart_agent = None

try:
    from backend.services.smart_agent_service import SmartAgent
    smart_agent = SmartAgent()
    print(f"=== 全局智能代理已成功初始化，ID={id(smart_agent)} ===")
    SMART_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"智能代理服务导入失败: {e}")
    SMART_AGENT_AVAILABLE = False
    print("智能代理不可用，将使用普通聊天模式")

# 全局LLM客户端
global_llm = None

# 初始化LLM
def initialize_llm():
    global global_llm
    try:
        # 检查Ollama服务是否在运行
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                # 获取可用模型列表
                models_data = response.json()
                models = [tag["name"] for tag in models_data.get("models", [])]
                
                # 检查是否有DeepSeek模型
                deepseek_model = None
                for model in models:
                    if "deepseek" in model.lower():
                        deepseek_model = model
                        break
                
                # 如果没有找到DeepSeek，寻找任何可用模型
                if not deepseek_model and models:
                    deepseek_model = models[0]
                
                # 默认回退到deepseek-r1:7b
                model_name = deepseek_model or "deepseek-r1:7b"
                print(f"使用模型: {model_name}")
                
                # 初始化LLM客户端
                global_llm = OllamaLLM(
                    model=model_name, 
                    base_url="http://localhost:11434",
                    temperature=0.7,
                    timeout=60
                )
                
                # 测试LLM是否正常
                test_response = global_llm.invoke("你好")
                print(f"LLM测试响应: {test_response[:20]}...")
        except Exception as e:
            print(f"连接Ollama API失败: {str(e)}")
            # 尝试使用ollama库直接连接
            try:
                models = ollama.list()
                global_llm = OllamaLLM(
                    model="deepseek-r1:7b",
                    temperature=0.7,
                    timeout=60
                )
            except Exception as e2:
                print(f"使用ollama库连接失败: {str(e2)}")
    except Exception as e:
        print(f"初始化LLM失败: {str(e)}")
        global_llm = None

router = APIRouter()

# 调用初始化
initialize_llm()

class ReferenceItem(BaseModel):
    id: Optional[int] = None
    path: Optional[str] = None
    source: str

class AttachmentItem(BaseModel):
    name: str
    path: str
    type: Optional[str] = "file"  # 可以是 "file" 或 "image"

class ChatRequest(BaseModel):
    query: str
    references: Optional[List[ReferenceItem]] = None
    attachments: Optional[List[AttachmentItem]] = None
    isEmailRequest: Optional[bool] = False

class ChatResponse(BaseModel):
    answer: str
    citations: List[dict]
    followupQuestions: List[str]

# 初始化AI模型和检索链
vector_store = None

@router.on_event("startup")
async def startup():
    try:
        global vector_store
        # 获取向量存储
        vector_store = get_vector_store()
    except Exception as e:
        print(f"警告: 向量存储初始化失败，知识库搜索功能可能不可用: {str(e)}")

# 辅助函数: 根据ID获取文档内容
def get_document_by_id(doc_id):
    try:
        # 检查参数有效性
        if not doc_id:
            print(f"警告: 收到无效的文档ID: {doc_id}")
            return None
            
        # 转换ID为整数
        try:
            doc_id = int(doc_id)
        except (ValueError, TypeError):
            print(f"警告: 无法将文档ID转换为整数: {doc_id}")
            return None
            
        print(f"尝试获取文档ID={doc_id}的内容")
        # 获取数据库连接
        db = next(get_db())
        
        # 使用原始SQL查询获取文档，避免任何ORM关系问题
        query = text("SELECT id, title, content FROM documents WHERE id = :doc_id")
        result = db.execute(query, {"doc_id": doc_id})
        doc_row = result.fetchone()
        
        if doc_row:
            doc_dict = dict(zip(["id", "title", "content"], doc_row))
            print(f"成功获取文档: {doc_dict['title']}")
            return {
                "title": doc_dict['title'],
                "content": doc_dict['content'][:1000] if doc_dict['content'] else "",  # 限制长度并处理空内容
                "source": f"文档: {doc_dict['title']} (ID: {doc_dict['id']})"
            }
        else:
            print(f"未找到ID={doc_id}的文档")
            return None
    except Exception as e:
        print(f"获取文档内容失败, ID={doc_id}: {str(e)}")
        import traceback
        traceback.print_exc()
    return None

async def read_file_content(file_path):
    """读取文件内容"""
    try:
        print(f"尝试读取文件内容: {file_path}")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}，尝试查找完整路径")
            # 尝试查找文件的完整路径
            base_name = os.path.basename(file_path)
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
            
            # 先处理特殊情况：如果路径包含文件夹前缀，直接获取正确路径
            if file_path.startswith("knowledge/") or file_path.startswith("personal/") or file_path.startswith("images/"):
                folder, filename = file_path.split("/", 1)
                possible_path = os.path.join(data_dir, folder, filename)
                if os.path.exists(possible_path):
                    file_path = possible_path
                    print(f"通过前缀匹配找到文件: {file_path}")
            else:
                # 检查可能的位置
                possible_locations = [
                    os.path.join(data_dir, "personal", base_name),
                    os.path.join(data_dir, "knowledge", base_name),
                    os.path.join(data_dir, "documents", base_name),
                    os.path.join(data_dir, "images", base_name)
                ]
                
                for possible_path in possible_locations:
                    print(f"检查可能的路径: {possible_path}")
                    if os.path.exists(possible_path):
                        file_path = possible_path
                        print(f"找到文件: {file_path}")
                        break
            
            # 如果仍然找不到文件，尝试查找匹配的文件
            if not os.path.exists(file_path):
                print(f"尝试使用模糊匹配查找文件")
                for directory in ["personal", "knowledge", "documents", "images"]:
                    dir_path = os.path.join(data_dir, directory)
                    if os.path.exists(dir_path):
                        for filename in os.listdir(dir_path):
                            # 检查文件名中是否包含部分路径标识符
                            if base_name in filename:
                                file_path = os.path.join(dir_path, filename)
                                print(f"通过模糊匹配找到文件: {file_path}")
                                break
            
            if not os.path.exists(file_path):
                print(f"无法找到文件: {os.path.basename(file_path)}")
                return f"文件不存在: {os.path.basename(file_path)}"
        
        print(f"准备读取文件内容: {file_path}")
        # 根据文件类型处理
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.pdf']:
            content = ""
            try:
                # 改进PDF处理逻辑
                with open(file_path, 'rb') as file:
                    reader = PdfReader(file)
                    # 添加错误处理和详细日志
                    print(f"PDF文件 {file_path} 包含 {len(reader.pages)} 页")
                    for i, page in enumerate(reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                content += page_text + "\n"
                            else:
                                print(f"警告: PDF第{i+1}页无法提取文本")
                        except Exception as page_error:
                            print(f"提取PDF第{i+1}页文本失败: {str(page_error)}")
                
                if not content.strip():
                    print(f"警告: PDF文件 {file_path} 未提取到文本内容")
                    return "PDF文件未包含可提取的文本内容"
                    
                return content
            except Exception as e:
                print(f"读取PDF文件失败 {file_path}: {e}")
                traceback.print_exc()  # 打印详细错误跟踪
                return f"无法读取PDF文件: {os.path.basename(file_path)}"
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            # 对于图片文件，返回一个描述
            print(f"识别为图片文件: {file_path}")
            return f"[图片文件: {os.path.basename(file_path)}]"
        else:
            # 对于文本文件，尝试读取内容
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    print(f"成功读取文本文件: {file_path}, 长度: {len(content)}")
                    return content
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，可能是二进制文件，尝试以二进制方式读取
                print(f"文件无法以UTF-8解码: {file_path}")
                return f"[二进制文件: {os.path.basename(file_path)}]"
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        traceback.print_exc()  # 打印详细错误跟踪
        return f"无法读取文件: {os.path.basename(file_path)}"

# ===== 智能代理处理函数 =====
async def process_with_smart_agent(query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    尝试使用智能代理处理用户请求，识别意图并提供操作建议
    """
    print("\n" + "="*50)
    print(f"【智能代理】开始处理用户输入: {query}")
    
    # 直接处理特定指令，不使用智能代理
    lower_query = query.lower()
    
    # ===== 邮件指令直接匹配 =====
    # 更宽松的条件以确保匹配成功
    if ((any(word in lower_query for word in ["写", "发", "创建", "撰写", "编写"]) and 
         any(word in lower_query for word in ["邮件", "信", "邮箱", "电子邮件"])) or
        "发邮件" in lower_query or "写邮件" in lower_query or "写信" in lower_query):
        print("【智能代理】✓ 直接匹配到邮件指令! (使用模糊匹配)")
        
        # 提取收件人信息
        recipient = ""
        recipient_match = re.search(r'给(.+?)(?:发|写|，|,|。|$)', lower_query)
        if recipient_match:
            recipient = recipient_match.group(1).strip()
            print(f"【智能代理】提取到收件人: {recipient}")
        
        # 提取请假信息（如果存在）
        subject = ""
        content = ""
        if "请假" in lower_query:
            days = "1"  # 默认请假1天
            days_match = re.search(r'(\d+)\s*[天日]', lower_query)
            if days_match:
                days = days_match.group(1)
                print(f"【智能代理】提取到请假天数: {days}天")
            
            subject = f"请假申请 - {days}天"
            content = f"""尊敬的{recipient or '老师'}：

我因个人原因需要请假{days}天，望批准。

此致
敬礼"""
            print(f"【智能代理】已生成请假邮件内容")
        
        email_result = {
            "detected_intent": True,
            "action": "compose_email",
            "confidence": 1.0,
            "message": "准备撰写邮件",
            "form_data": {
                "recipient": recipient,
                "subject": subject,
                "content": content
            },
            "suggestions": [
                {
                    "type": "compose_email",
                    "title": "撰写邮件",
                    "form_data": {
                        "recipient": recipient,
                        "subject": subject,
                        "content": content
                    }
                }
            ]
        }
        
        print(f"【智能代理】返回邮件操作结果: confidence=1.0, recipient={recipient}")
        print("="*50 + "\n")
        return email_result
    
    # ===== 动词优先匹配逻辑 =====
    # 首先检查是否包含创建/设计类动词
    creation_verbs = ["创建", "设计", "新建", "制作", "添加", "新增"]
    action_verbs = ["发起", "申请", "提交"]
    
    has_creation_verb = any(verb in lower_query for verb in creation_verbs)
    has_action_verb = any(verb in lower_query for verb in action_verbs)
    
    print(f"【智能代理】动词分析: 创建类动词={has_creation_verb}, 动作类动词={has_action_verb}")
    
    # ===== 工作流创建优先匹配 (动词优先) =====
    if has_creation_verb and ("工作流" in lower_query or "流程" in lower_query or 
                             ("审批" in lower_query and ("设计" in lower_query or "创建" in lower_query))):
        print("【智能代理】✓ 动词优先匹配到工作流创建指令!")
        
        # 提取工作流名称
        name = "新建工作流"
        # 匹配 "设计/创建 + [名称] + 审批/工作流/流程"
        name_patterns = [
            r'(?:创建|设计|新建|制作)\s*([^，。,\.;；]*?)\s*(?:审批|工作流|流程)',
            r'(?:创建|设计|新建|制作)\s*一个\s*([^，。,\.;；]*?)\s*(?:审批|工作流|流程)'
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, lower_query)
            if name_match and name_match.group(1).strip():
                extracted_name = name_match.group(1).strip()
                if extracted_name and extracted_name not in ["一个", "个", "新的"]:
                    name = extracted_name
                    if len(name) > 15:  # 如果名称太长，截断
                        name = name[:15]
                    # 确保名称以"流程"结尾
                    if not (name.endswith('流程') or name.endswith('审批')):
                        name = name + "审批流程"
                    print(f"【智能代理】提取到工作流名称: {name}")
                    break
        
        workflow_result = {
            "detected_intent": True,
            "action": "create_workflow",
            "confidence": 1.0,
            "message": "准备创建工作流",
            "form_data": {
                "name": name,
                "description": "根据AI助手提示自动创建的工作流",
                "prompt": lower_query
            },
            "suggestions": [
                {
                    "type": "create_workflow",
                    "title": "设计流程",
                    "form_data": {
                        "name": name,
                        "description": "根据AI助手提示自动创建的工作流",
                        "prompt": lower_query
                    }
                }
            ]
        }
        
        print(f"【智能代理】返回工作流创建操作结果: confidence=1.0, name={name}")
        print("="*50 + "\n")
        return workflow_result
    
    # ===== 审批发起匹配 (仅在明确动作动词或无创建动词时) =====
    if ((has_action_verb or not has_creation_verb) and 
        (any(x in lower_query for x in ["审批", "申请", "请假", "报销", "采购", "休假"]))):
        print("【智能代理】✓ 匹配到审批发起指令!")
        
        process_type = "请假"  # 默认请假类型
        if "报销" in lower_query:
            process_type = "报销"
            print("【智能代理】审批类型: 报销")
        elif "采购" in lower_query:
            process_type = "采购"
            print("【智能代理】审批类型: 采购")
        else:
            print("【智能代理】审批类型: 请假")
        
        # 提取天数/金额信息
        form_data = {"process_type": process_type}
        days_match = re.search(r'(\d+)\s*[天日]', lower_query)
        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:元|万元|¥|RMB|CNY)', lower_query)
        
        if days_match:
            days = int(days_match.group(1))
            form_data["days"] = days
            form_data["reason"] = "个人原因"
            print(f"【智能代理】提取到请假天数: {days}天")
        
        if amount_match:
            amount = float(amount_match.group(1))
            form_data["amount"] = amount
            print(f"【智能代理】提取到金额: {amount}元")
        
        approval_result = {
            "detected_intent": True,
            "action": "create_approval",
            "confidence": 1.0,
            "message": "准备创建审批流程",
            "form_data": form_data,
            "suggestions": [
                {
                    "type": "create_approval",
                    "title": "创建审批",
                    "form_data": form_data
                }
            ]
        }
        
        print(f"【智能代理】返回审批操作结果: confidence=1.0, type={process_type}")
        print("="*50 + "\n")
        return approval_result
    
    # ===== 用户创建匹配 (动词优先) =====
    if has_creation_verb and ("用户" in lower_query or "账号" in lower_query or "账户" in lower_query):
        print("【智能代理】✓ 动词优先匹配到用户创建指令!")
        print(f"【智能代理】输入: '{lower_query}'")
        
        # 提取用户名、角色等信息
        name_match = re.search(r'(?:用户名|姓名)[是为：:]*\s*[""「」《》\s]*([^，。,\.;；""「」《》]*)', lower_query)
        role_match = re.search(r'(?:角色|权限)[是为：:]*\s*[""「」《》\s]*([^，。,\.;；""「」《》]*)', lower_query)
        
        form_data = {}
        if name_match:
            form_data["username"] = name_match.group(1).strip()
            print(f"【智能代理】提取到用户名: {form_data['username']}")
        else:
            # 生成随机用户名
            form_data["username"] = f"user_{random.randint(1000, 9999)}"
            print(f"【智能代理】生成随机用户名: {form_data['username']}")
            
        # 生成随机密码
        form_data["password"] = f"pwd_{random.randint(1000, 9999)}"
        print(f"【智能代理】生成随机密码: {form_data['password']}")
            
        if role_match:
            form_data["role"] = role_match.group(1).strip()
            print(f"【智能代理】提取到角色: {form_data['role']}")
            
        # 检查是否包含"普通用户"关键词
        if "普通" in lower_query and "用户" in lower_query:
            form_data["role"] = "普通用户"
            print("【智能代理】检测到'普通用户'关键词，设置角色为普通用户")
        
        user_result = {
            "detected_intent": True,
            "action": "create_user",
            "confidence": 1.0,
            "message": "准备创建用户",
            "form_data": form_data,
            "suggestions": [
                {
                    "type": "create_user",
                    "title": "创建用户",
                    "form_data": form_data
                }
            ]
        }
        
        print(f"【智能代理】返回创建用户操作结果: confidence=1.0")
        print("="*50 + "\n")
        return user_result
    

    
    # ===== 实在不行才使用智能代理 =====
    print("【智能代理】直接匹配失败，尝试使用智能代理服务...")
    
    global smart_agent
    
    # 检查全局智能代理是否可用
    if not smart_agent:
        print("【智能代理】全局智能代理不可用，尝试重新初始化...")
        try:
            from backend.services.smart_agent_service import SmartAgent
            smart_agent = SmartAgent()
            print(f"【智能代理】智能代理重新初始化成功，ID={id(smart_agent)}")
        except Exception as e:
            print(f"【智能代理】重新初始化失败: {e}")
            print("="*50 + "\n")
            return None
    
    try:
        # 使用智能代理处理
        print(f"【智能代理】使用智能代理处理输入: {query}")
        agent_result = smart_agent.process_user_input(query, context or {})
        print(f"【智能代理】获得处理结果: {agent_result}")
        
        # 检查处理结果
        if agent_result and agent_result.get("success", False):
            action = agent_result.get("action", "unknown")
            confidence = agent_result.get("confidence", 0)
            
            print(f"【智能代理】智能代理处理结果: 动作={action}, 置信度={confidence}")
            
            # 包装返回结果
            result = {
                    "detected_intent": True,
                    "action": action,
                    "confidence": confidence,
                    "message": agent_result.get("message", ""),
                "form_data": agent_result.get("form_data", {})
            }
            
            # 添加suggestions字段
            if action != "unknown":
                result["suggestions"] = [
                        {
                            "type": action,
                        "title": f"创建{action.split('_')[-1] if '_' in action else action}",
                            "form_data": agent_result.get("form_data", {})
                        }
                    ]
            
            print(f"【智能代理】返回智能代理处理结果: action={action}, confidence={confidence}")
            print("="*50 + "\n")
            return result
        else:
            print("【智能代理】智能代理处理失败或未识别意图")
    except Exception as e:
        print(f"【智能代理】处理异常: {e}")
        traceback.print_exc()
    
    print("【智能代理】所有处理方法都失败")
    print("="*50 + "\n")
    return None

# 修改generate_response函数，添加智能代理集成
async def generate_response(prompt, original_query=None, context=None):
    """生成AI响应，可能包含智能代理的操作建议"""
    try:
        # 如果有原始查询，先尝试使用智能代理处理
        agent_result = None
        if original_query:
            print(f"尝试使用智能代理处理用户输入: {original_query}")
            agent_result = await process_with_smart_agent(original_query, context)
            if agent_result:
                print(f"智能代理处理成功: {agent_result}")
                # 如果智能代理识别到了项目功能，返回针对性的回复
                return generate_targeted_response(agent_result, original_query)
        
        # 使用全局LLM客户端
        global global_llm
        if global_llm is None:
            print("LLM未初始化，尝试重新初始化...")
            initialize_llm()
            
        if global_llm is None:
            print("LLM初始化失败，无法处理请求")
            return "抱歉，AI助手暂时无法处理您的请求，LLM服务不可用。请检查Ollama服务是否正在运行。"
            
        # 为DeepSeek模型添加系统提示词，提高生成质量
        formatted_prompt = f"""
系统：你是一个智能、专业、富有帮助的人工智能助手。你的任务是为用户提供准确、有用的信息。
请以简洁清晰的方式回答问题，尽量避免冗长和重复。
回答时使用中文，使用客观、专业的语气。

{prompt}
"""
            
        # 使用Ollama LLM
        try:
            print(f"发送到LLM的提示词长度: {len(formatted_prompt)}")
            response = global_llm.invoke(formatted_prompt)
            
            # 确保返回的是字符串
            if not isinstance(response, str):
                response = str(response)
            
            print(f"LLM响应长度: {len(response)}")
            return response
        except Exception as llm_error:
            print(f"LLM调用失败: {str(llm_error)}")
            # 尝试重新初始化
            initialize_llm()
            if global_llm is not None:
                try:
                    response = global_llm.invoke(formatted_prompt)
                    return str(response)
                except Exception as retry_error:
                    print(f"LLM重试调用失败: {str(retry_error)}")
            return "抱歉，AI助手暂时无法处理您的请求。LLM服务出现了问题，请稍后再试。"
    except Exception as e:
        print(f"生成响应失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return "抱歉，AI助手暂时无法处理您的请求。出现了一些技术问题，请稍后再试。"

def generate_targeted_response(agent_result, original_query):
    """根据智能代理结果生成针对性的回复"""
    try:
        action_type = agent_result.get("action", "")
        form_data = agent_result.get("form_data", {})
        confidence = agent_result.get("confidence", 0)
        
        print(f"生成针对性回复: 动作={action_type}, 置信度={confidence}")
        
        if action_type == "create_approval":
            process_type = form_data.get("process_type", "")
            days = form_data.get("days", 0)
            reason = form_data.get("reason", "")
            amount = form_data.get("amount", 0)
            
            if process_type == "请假":
                return f"我识别出您想申请{days}天的请假。通过智能分析您的描述，我已为您准备了完整的请假申请表单，请假理由设置为：{reason}。系统自动填充了申请日期、请假天数、联系方式等必要信息，确保申请流程的完整性和规范性。您只需点击下方按钮即可快速提交申请，无需手动填写繁琐的表单字段，让请假申请变得更加便捷高效。"
            elif process_type == "报销":
                return f"我识别出您想申请{amount}元的费用报销。基于您提供的信息，我智能生成了完整的报销申请，报销理由设置为：{reason}。系统已预填写了报销金额、费用类型、申请日期等关键信息，并按照公司财务规范格式化了申请内容。您可以直接点击下方按钮提交申请，避免了复杂的表单填写过程，让报销流程更加智能化和便民化。"
            else:
                return f"我识别出您想提交{process_type}申请。通过智能分析您的需求，我已为您准备了完整的申请表单和相关材料。系统根据申请类型自动匹配了最适合的审批流程和表单模板，确保申请信息的准确性和完整性。所有必要的字段都已预填充完毕，您只需点击下方按钮即可快速提交申请，享受智能化的办公体验。"
        
        elif action_type == "compose_email":
            recipient = form_data.get("recipient", "")
            subject = form_data.get("subject", "")
            content = form_data.get("content", "")
            
            if recipient:
                return f"我识别出您想给{recipient}发送邮件，主题设定为：{subject}。通过智能分析您的沟通意图，我已为您生成了专业且得体的邮件内容，确保表达准确、语气恰当。邮件格式符合商务沟通标准，包含了适当的称谓、正文结构和结尾礼貌用语。您可以点击下方按钮打开邮件编辑器查看完整内容，也可以根据具体需求进行个性化调整。"
            else:
                return "我识别出您想撰写邮件。基于您的描述，我智能生成了结构清晰、表达准确的邮件内容，符合专业沟通的标准格式。邮件包含了恰当的开头、详细的正文内容和礼貌的结尾，确保沟通的有效性和专业性。您可以点击下方按钮打开邮件编辑器进行查看和编辑，根据具体情况调整内容，让邮件撰写变得更加简单高效。"
        
        elif action_type == "create_user":
            username = form_data.get("username", "")
            password = form_data.get("password", "")
            department = form_data.get("department", "")
            role = form_data.get("role", "")
            
            return f"我识别出您想创建新的用户账号。根据您的需求，我已智能配置了完整的用户信息：用户名设置为{username}，部门归属为{department}，权限角色定义为{role}。系统自动生成了符合安全标准的登录密码：{password}，并预设了相应的权限配置和访问控制。所有用户基础信息都已准备就绪，您只需点击下方按钮即可完成用户创建，新账号将立即生效并可正常使用。"
        
        elif action_type == "create_workflow":
            name = form_data.get("name", "")
            description = form_data.get("description", "")
            
            return f"我识别出您想设计名为'{name}'的工作流程。基于您的具体需求，我将为您创建智能化的业务流程，{description}。系统会根据最佳实践自动配置流程节点、审批路径和业务规则，确保流程的合理性、高效性和可操作性。您可以点击下方按钮进入可视化的工作流设计器，通过拖拽方式轻松构建符合业务需求的流程图，提升组织运营效率。"
        
        else:
            return "我通过智能分析已经理解了您的具体需求，并为您准备了相应的解决方案和操作选项。系统根据您的描述自动匹配了最适合的功能模块和处理流程，确保操作的准确性和高效性。所有相关信息都已整理完毕，您只需点击下方按钮即可快速完成相应操作，享受智能化办公带来的便捷体验。"
            
    except Exception as e:
        print(f"生成针对性回复失败: {str(e)}")
        return "我理解了您的需求，已经为您准备好相应的操作。点击下方按钮即可快速完成。"

# 处理专门的邮件生成请求
async def generate_email_response(query):
    """生成特定格式的邮件回复"""
    try:
        # 提取可能的邮件主题和收件人
        recipient = ""
        subject = ""
        
        # 尝试从查询中提取收件人
        recipient_match = re.search(r'给(.+?)(?:发|写)', query) or re.search(r'写给(.+?)的', query) or re.search(r'收件人[是为:：](.+?)[,，。\n]', query) or re.search(r'[发送给|寄给](.+?)[,，。\n]', query)
        if recipient_match:
            recipient = recipient_match.group(1).strip()
            
        # 尝试从查询中提取主题
        subject_match = re.search(r'主题[是为:：](.+?)[,，。\n]', query) or re.search(r'关于(.+?)的邮件', query) or re.search(r'邮件主题是(.+?)[,，。\n]', query)
        if subject_match:
            subject = subject_match.group(1).strip()
        
        # 尝试提取邮件目的/内容
        purpose_match = re.search(r'内容[是为:：](.+)', query) or re.search(r'邮件内容是(.+)', query) or re.search(r'目的是(.+)', query)
        purpose = ""
        if purpose_match:
            purpose = purpose_match.group(1).strip()
            
        # 构建提示词
        prompt = f"""请你帮我写一封正式的邮件，要求如下：
收件人: {recipient if recipient else "[未指定]"}
主题: {subject if subject else "[未指定]"}
邮件内容/目的: {purpose if purpose else query}

请注意以下格式要求：
1. 合理划分段落，保持清晰的邮件结构
2. 使用适当的称呼和开场白
3. 正文内容要专业、简洁明了
4. 添加恰当的结束语和署名
5. 根据邮件目的调整语气和语调

请按照以下格式返回邮件：
收件人: [收件人]
主题: [邮件主题]
内容:
[邮件正文，包括称呼、正文内容、结束语和签名]

注意：请不要在回复中包含任何思考过程或解释，直接输出最终邮件内容。不要使用<think>标签。
"""
        
        # 调用LLM生成邮件
        email_content = await generate_response(prompt)
        
        # 清理内容，移除可能的思考过程
        email_content = re.sub(r'<think>[\s\S]*?<\/think>', '', email_content)
        email_content = re.sub(r'<th\s*ink>[\s\S]*?<\/th\s*ink>', '', email_content)
        email_content = re.sub(r'【思考[:：][\s\S]*?】', '', email_content)
        email_content = re.sub(r'\[思考[:：][\s\S]*?\]', '', email_content)
        email_content = re.sub(r'（思考[:：][\s\S]*?）', '', email_content)
        email_content = re.sub(r'\(思考[:：][\s\S]*?\)', '', email_content)
        email_content = re.sub(r'接下来[我|我们|开始|将]', '', email_content)
        email_content = re.sub(r'首先[，|,]?我[需要|会|将]', '', email_content)
        # 移除AI分析/思考相关内容
        email_content = re.sub(r'AI分析[:：][\s\S]*?(?=\n\n)', '', email_content)
        email_content = re.sub(r'思路[:：][\s\S]*?(?=\n\n)', '', email_content)
        email_content = re.sub(r'让我来[:：][\s\S]*?(?=\n\n)', '', email_content)
        
        # 确保返回格式正确
        email_content = email_content.strip()
        
        # 从生成的内容中提取收件人、主题和正文
        extracted_recipient = recipient
        extracted_subject = subject
        pure_content = ""
        
        # 提取收件人
        new_recipient_match = re.search(r'收件人[:：]\s*(.+?)[\n\r]', email_content)
        if new_recipient_match and new_recipient_match.group(1).strip() not in ["[收件人]", "[未指定]", "请填写收件人"]:
            extracted_recipient = new_recipient_match.group(1).strip()
        
        # 提取主题
        new_subject_match = re.search(r'主题[:：]\s*(.+?)[\n\r]', email_content)
        if new_subject_match and new_subject_match.group(1).strip() not in ["[邮件主题]", "[未指定]", "请填写主题"]:
            extracted_subject = new_subject_match.group(1).strip()
        
        # 提取纯内容部分 - 改进这部分逻辑
        content_match = re.search(r'内容[:：][\r\n]+(.+)', email_content, re.DOTALL)
        if content_match:
            pure_content = content_match.group(1).strip()
        else:
            # 尝试查找正文部分的其他模式
            lines = email_content.split('\n')
            content_start = -1
            
            # 查找内容/正文开始的位置
            for i, line in enumerate(lines):
                if re.match(r'^主题[:：]', line) and i < len(lines) - 1:
                    content_start = i + 1
                    break
                    
            # 如果找到了主题行但没找到内容标记，假设内容从主题行后开始
            if content_start >= 0:
                pure_content = '\n'.join(lines[content_start:]).strip()
            else:
                # 如果没有找到明确的内容起始点，尝试移除收件人和主题行
                pure_content = email_content
                if new_recipient_match:
                    pure_content = pure_content.replace(new_recipient_match.group(0), '')
                if new_subject_match:
                    pure_content = pure_content.replace(new_subject_match.group(0), '')
                pure_content = re.sub(r'^内容[:：][\r\n]+', '', pure_content, flags=re.MULTILINE)
                pure_content = pure_content.strip()
        
        # 如果纯内容为空，则使用整个邮件内容
        if not pure_content:
            pure_content = email_content
            
        print(f"提取的邮件内容: {pure_content[:100]}...")
        
        # 构建格式化的完整邮件内容（包含收件人和主题行）
        formatted_email = f"收件人: {extracted_recipient if extracted_recipient else '请填写收件人'}\n"
        formatted_email += f"主题: {extracted_subject if extracted_subject else '请填写主题'}\n"
        formatted_email += f"内容:\n{pure_content}"
        
        # 返回结构化数据
        response_data = {
            "content": pure_content,
            "recipient": extracted_recipient,
            "subject": extracted_subject,
            "full_content": formatted_email
        }
        
        print(f"生成邮件成功: 收件人={extracted_recipient}, 主题={extracted_subject}")
        print(f"邮件JSON数据: {json.dumps(response_data, ensure_ascii=False)[:200]}...")
        
        # 返回结构化数据（JSON字符串）
        return json.dumps(response_data, ensure_ascii=False)
    except Exception as e:
        print(f"生成邮件失败: {e}")
        import traceback
        traceback.print_exc()
        error_response = {
            "content": f"生成邮件时出现错误: {str(e)}",
            "recipient": "",
            "subject": "",
            "full_content": f"生成邮件时出现错误: {str(e)}"
        }
        return json.dumps(error_response, ensure_ascii=False)

async def stream_response(full_response):
    """流式返回字符串响应"""
    try:
        # 每次发送一个小的字符块，模拟流式响应
        chunk_size = 10
        for i in range(0, len(full_response), chunk_size):
            chunk = full_response[i:i+chunk_size]
            yield chunk
            await asyncio.sleep(0.05)  # 模拟流式输出的延迟
    except Exception as e:
        print(f"流式生成失败: {e}")
        yield "抱歉，AI助手暂时无法处理您的请求。出现了一些问题。"

# 修改响应流函数，支持JSON格式引用信息
async def stream_response_with_references(content: str, references: List[Dict], agent_result: Dict = None):
    """将内容和引用信息包装为JSON格式，并作为SSE流返回"""
    try:
        # 将内容和引用信息包装为JSON格式
        response_data = {
            "content": content,
            "references": references,
            "has_references": len(references) > 0
        }
        
        # 如果有智能代理结果，添加到响应中
        if agent_result:
            print(f"在流响应中添加智能代理结果: {agent_result}")
            # 确保agent_result中包含form_data字段
            if "form_data" not in agent_result and "data" in agent_result:
                print("修正agent_result，将data字段复制到form_data字段")
                agent_result["form_data"] = agent_result["data"]
                
            response_data["agent_result"] = agent_result
    
        # 转换为JSON字符串
        json_str = json.dumps(response_data, ensure_ascii=False)
        
        # 分块传输，确保正确的SSE格式
        yield f"data: {json_str}\n\n"
        # 添加结束标记
        yield "data: [DONE]\n\n"
    except Exception as e:
        print(f"生成流响应时出错: {str(e)}")
        error_json = json.dumps({"error": str(e)}, ensure_ascii=False)
        yield f"data: {error_json}\n\n"
        yield "data: [DONE]\n\n"

# 添加文档搜索功能
async def search_documents(query: str, top_k: int = 5):
    """
    使用自然语言搜索相关文档
    """
    try:
        global vector_store
        results = []
        
        # 检查向量存储是否已初始化
        if vector_store is None:
            try:
                vector_store = get_vector_store()
                if vector_store is None:
                    print("警告: 向量存储未初始化，无法执行语义搜索")
                    return results
            except Exception as e:
                print(f"初始化向量存储失败: {str(e)}")
                return results
        
        # 执行向量搜索
        try:
            # 查询向量存储
            search_results = vector_store.similarity_search_with_score(query, k=top_k)
            
            # 处理搜索结果
            for doc, score in search_results:
                # 计算相关度百分比 (转换相似度分数)
                relevance = min(100, max(0, int((1.0 - score) * 100))) if score <= 2.0 else 0
                
                # 检查相关度是否太低
                if relevance < 30:  # 相关度低于30%的文档被过滤
                    continue
                    
                # 从文档中提取信息
                metadata = doc.metadata or {}
                source = metadata.get("source", "未知来源")
                
                results.append({
                    "content": doc.page_content,
                    "metadata": metadata,
                    "relevance": relevance
                })
                
                print(f"找到相关文档: {source}, 相关度: {relevance}%")
        except Exception as e:
            print(f"执行向量搜索失败: {str(e)}")
            traceback.print_exc()
        
        # 如果向量搜索没有结果，尝试关键词搜索 
        if not results:
            print("向量搜索无结果，尝试数据库关键词搜索")
            try:
                # 从查询中提取关键词
                keywords = [word for word in query.split() if len(word) > 1]
                if keywords:
                    # 在数据库中搜索，使用原始SQL查询而不是ORM
                    db = next(get_db())
                    for keyword in keywords:
                        sql_query = text("""
                            SELECT id, title, content 
                            FROM documents 
                            WHERE content LIKE :keyword OR title LIKE :keyword
                            LIMIT 3
                        """)
                        result = db.execute(sql_query, {"keyword": f"%{keyword}%"})
                        
                        for row in result:
                            doc_dict = dict(zip(["id", "title", "content"], row))
                            results.append({
                                "content": f"标题: {doc_dict['title']}\n内容: {doc_dict['content'][:500]}...",
                                "metadata": {"source": doc_dict['title'], "id": doc_dict['id']},
                                "relevance": 60  # 默认相关度
                            })
            except Exception as e:
                print(f"关键词搜索失败: {str(e)}")
                traceback.print_exc()
        
        return results
    except Exception as e:
        print(f"搜索文档时出错: {str(e)}")
        traceback.print_exc()
        return []

# 修改聊天处理函数，确保调用新的智能代理处理函数
@router.post("/chat", response_class=StreamingResponse)
async def chat(request: ChatRequest):
    """处理用户与AI的对话"""
    try:
        query = request.query.strip()
        print(f"收到聊天请求: {query}")
        
        # 创建引用文档列表
        references = []
        references_content = []
        
        # 处理文档ID引用
        if request.references:
            for ref in request.references:
                print(f"处理引用: {ref}")
                # 处理文档ID引用
                if ref.id:
                    print(f"引用文档ID: {ref.id}")
                    doc_info = get_document_by_id(ref.id)
                    if doc_info:
                        references.append(doc_info)
                        references_content.append(f"文档《{doc_info['title']}》内容: {doc_info['content']}")
                    else:
                        print(f"未能获取ID={ref.id}的文档内容")
                # 处理文档路径引用
                elif ref.path:
                    print(f"引用文档路径: {ref.path}")
                    file_content = await read_file_content(ref.path)
                    ref_title = os.path.basename(ref.path)
                    references.append({
                        "title": ref_title,
                        "content": file_content[:1000],  # 限制长度
                        "context": file_content[:100],  # 为前端显示准备的简短上下文
                        "source": f"文件: {ref_title}"
                    })
                    # 添加文件内容作为上下文
                    references_content.append(f"文件《{ref_title}》内容: {file_content}")
                else:
                    print(f"警告: 收到无效的引用: {ref}")
        
        # 处理附件
        attachments_content = []
        if request.attachments:
            for attachment in request.attachments:
                print(f"处理附件: {attachment.name}, 路径: {attachment.path}")
                file_content = await read_file_content(attachment.path)
                attachments_content.append(f"附件《{attachment.name}》内容: {file_content}")
        
        # 尝试搜索相关文档作为上下文来源
        # 当用户没有明确引用文档时，自动搜索相关文档
        if not request.references and not request.isEmailRequest:
            try:
                print("搜索相关文档...")
                search_results = await search_documents(query)
                context_docs = []
                
                # 添加搜索到的文档作为引用
                for item in search_results:
                    doc_content = item["content"]
                    doc_source = item.get("metadata", {}).get("source", "知识库")
                    
                    # 添加到引用列表
                    references.append({
                        "title": doc_source,
                        "content": doc_content[:300],  # 截断显示内容
                        "context": doc_content[:100],  # 为前端显示准备的简短上下文
                        "source": f"自动检索: {doc_source}"
                    })
                    
                    # 添加到上下文
                    context_docs.append(f"来源《{doc_source}》: {doc_content}")
                
                # 将搜索结果添加到引用内容中
                if context_docs:
                    references_content.append("\n相关文档内容:\n" + "\n---\n".join(context_docs))
                    print(f"找到 {len(context_docs)} 个相关文档")
            except Exception as e:
                print(f"搜索相关文档时出错: {str(e)}")
        
        # 尝试使用智能代理处理请求 - 这是关键点，我们需要确保使用我们修改的函数
        agent_result = None
        try:
            print("\n>>>>> 开始智能代理处理流程 <<<<<")
            context = {"references": references_content}
            agent_result = await process_with_smart_agent(query, context)
            if agent_result:
                print(f">>>>> 智能代理成功识别意图: {agent_result.get('action', 'unknown')}, 置信度: {agent_result.get('confidence', 0)} <<<<<\n")
            else:
                print(">>>>> 智能代理未识别出明确意图 <<<<<\n")
        except Exception as e:
            print(f">>>>> 智能代理处理失败: {str(e)} <<<<<\n")
            traceback.print_exc()
                
        # 构建提示词
        if request.isEmailRequest:
            prompt = f"用户请求: {query}\n\n"
            if references_content:
                prompt += "参考信息:\n" + "\n\n".join(references_content) + "\n\n"
            if attachments_content:
                prompt += "附件信息:\n" + "\n\n".join(attachments_content) + "\n\n"
            prompt += """请根据用户需求生成一封专业的商务邮件，并按以下格式输出:
收件人: [收件人邮箱或姓名]
主题: [邮件主题]
内容:
[邮件正文]"""
            
            # 1. 获取完整的邮件数据
            email_response_data = await generate_email_response(prompt)
            
            # 确保 email_response_data 是字典
            email_data_dict = {}
            if isinstance(email_response_data, str):
                try:
                    email_data_dict = json.loads(email_response_data)
                except json.JSONDecodeError:
                    print(f"错误：generate_email_response 未返回有效的JSON: {email_response_data[:100]}...")
                    email_data_dict = {"content": "邮件生成失败", "recipient": "", "subject": "错误", "full_content": "邮件生成失败"}
            elif isinstance(email_response_data, dict):
                email_data_dict = email_response_data
            else:
                 print(f"错误：generate_email_response 返回了未知类型: {type(email_response_data)}")
                 email_data_dict = {"content": "邮件生成失败", "recipient": "", "subject": "错误", "full_content": "邮件生成失败"}
            
            # 2. 使用 stream_email_json_response 处理邮件字典
            return StreamingResponse(
                stream_email_json_response(email_data_dict),
                media_type="text/event-stream"
            )
        else:
            # 常规聊天响应
            prompt = f"用户问题: {query}\n\n"
            
            # 添加引用内容和附件内容
            if references_content:
                prompt += "参考信息:\n" + "\n\n".join(references_content) + "\n\n"
            if attachments_content:
                prompt += "附件信息:\n" + "\n\n".join(attachments_content) + "\n\n"
            
            # 添加指导语
            prompt += """请根据提供的参考信息回答用户的问题。如果参考信息中包含所需答案，请基于这些信息回答。
如果参考信息不足以回答问题，请基于你自己的知识回答，但请明确说明这部分是你自己的认知。
回答应简洁、全面、准确，并直接针对用户问题。"""
            
            # 生成AI响应，传入原始查询和上下文
            response = await generate_response(prompt, original_query=query, context={"references": references_content})
            
            # 生成AI响应
            return StreamingResponse(
                stream_response_with_references(response, references, agent_result),
                media_type="text/event-stream"
            )
    except Exception as e:
        print(f"处理聊天请求失败: {str(e)}")
        import traceback
        traceback.print_exc()
        error_response = {"error": f"处理请求失败: {str(e)}"}
        return StreamingResponse(
            stream_string_response(json.dumps(error_response, ensure_ascii=False)),
            media_type="text/event-stream"
        )

# 新增：专门处理邮件JSON响应的流式生成
async def stream_email_json_response(email_data):
    """将邮件JSON数据转换为流式事件"""
    try:
        # 第一步：发送完整的JSON数据
        chunk1 = f"data: EMAIL_JSON_START\n\n"
        print(f"[stream_email_json_response] Yielding: {chunk1.strip()}")
        yield chunk1
    
        # 直接发送纯JSON字符串
        json_data = json.dumps(email_data, ensure_ascii=False)
        chunk2 = f"data: {json_data}\n\n"
        print(f"[stream_email_json_response] Yielding JSON data chunk (length: {len(chunk2)}): {chunk2.strip()[:100]}...")
        yield chunk2
    
        chunk3 = f"data: EMAIL_JSON_END\n\n"
        print(f"[stream_email_json_response] Yielding: {chunk3.strip()}")
        yield chunk3
    
        # 第二步：发送用于显示的邮件内容
        full_content = email_data.get("full_content", "")
        if full_content:
            # 每次发送少量字符
            chunk_size = 20
            for i in range(0, len(full_content), chunk_size):
                chunk_content = full_content[i:i+chunk_size]
                chunk4 = f"data: {chunk_content}\n\n"
                yield chunk4
                await asyncio.sleep(0.02)
            print(f"[stream_email_json_response] Finished yielding full_content chunks.")
        
            chunk5 = "data: [DONE]\n\n"
            print(f"[stream_email_json_response] Yielding: {chunk5.strip()}")
            yield chunk5
    except Exception as e:
        print(f"ERROR in stream_email_json_response: {e}")
        traceback.print_exc()
        # Yield an error message in SSE format if something goes wrong within the stream
        error_chunk = f"data: {json.dumps({'error': 'Error during streaming'})}\n\n"
        print(f"[stream_email_json_response] Yielding error chunk: {error_chunk.strip()}")
        yield error_chunk
        done_chunk = "data: [DONE]\n\n"
        print(f"[stream_email_json_response] Yielding DONE after error.")
        yield done_chunk

async def stream_string_response(text):
    """将字符串转换为流式响应"""
    # 检查是否为JSON字符串
    try:
        json_data = json.loads(text)
        # 如果是邮件数据，使用专门的邮件流处理
        if isinstance(json_data, dict) and "full_content" in json_data:
            async for chunk in stream_email_json_response(json_data):
                yield chunk
            return
    except:
        # 不是JSON字符串，继续正常处理
        pass
        
    # 每次发送少量字符
    chunk_size = 10
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        yield f"data: {chunk}\n\n"  # 添加前缀和换行符
        await asyncio.sleep(0.05)  # 添加一点延迟模拟流式输出
    yield "data: [DONE]\n\n"  # 同样添加前缀
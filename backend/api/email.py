import os
import sqlite3
import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Body
from pydantic import BaseModel
from langchain.chains import RetrievalQA
from langchain_ollama import OllamaLLM
import ollama  # 直接导入ollama库
from knowledge_base.vector_store import get_vector_store
from typing import List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import configparser
import requests
import time
import re
import json
import imaplib
import email
from utils.logger import colored, log_banner, log_system_event, logger

router = APIRouter()

# 定义邮件配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "email_config.json")
# 定义邮件数据库路径（使用主数据库）
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "oa.db")
print(f"邮件配置文件路径: {CONFIG_FILE}")
print(f"邮件数据库路径: {DB_PATH}")

# 从chat.py导入全局LLM和初始化函数
try:
    from backend.api.chat import global_llm, initialize_llm
    print("成功导入全局LLM实例")
except ImportError as e:
    print(f"导入全局LLM失败: {str(e)}，将设置为None")
    global_llm = None
    
    # 如果导入失败，定义本地函数
    def initialize_llm():
        global global_llm
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                available_models = [model["name"] for model in response.json()["models"]]
                print(f"可用的Ollama模型: {available_models}")
                
                # 尝试按优先级使用模型
                preferred_models = ["llama3", "deepseek-coder", "qwen", "mistral", "deepseek-r1:7b", "deepseek-r1"]
                
                selected_model = None
                for model in preferred_models:
                    # 检查是否有匹配的模型（部分匹配也可以）
                    for available in available_models:
                        if model in available:
                            selected_model = available
                            print(f"选择模型: {selected_model}")
                            break
                    if selected_model:
                        break
                
                # 如果没有匹配到任何推荐模型，使用第一个可用模型
                if not selected_model and available_models:
                    selected_model = available_models[0]
                    print(f"未找到推荐模型，使用可用模型: {selected_model}")
                
                # 如果有可用模型，初始化LLM
                if selected_model:
                    global_llm = OllamaLLM(
                        model=selected_model, 
                        base_url="http://localhost:11434",
                        temperature=0.7,
                        timeout=60
                    )
                    print(f"成功初始化LLM，使用模型: {selected_model}")
                    return True
                else:
                    print("没有可用的Ollama模型")
                    return False
            else:
                print(f"获取Ollama模型列表失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"初始化LLM失败: {str(e)}")
            return False

# 如果global_llm为None，尝试初始化
if global_llm is None:
    initialize_llm()

print("\n===== 创建email路由器 =====")

# 调试函数，打印已注册的路由
def print_routes():
    print("\n路由器中的路由:")
    for route in router.routes:
        print(f"路径: {route.path}, 方法: {route.methods}")
    print("============================\n")

class EmailGenerateRequest(BaseModel):
    subject: str
    intention: str = ""  # 可选参数，用于润色模式
    recipient: str = ""  # 可选参数，用于生成模式
    mode: str = "polish"  # 默认为润色模式，可选值为"polish"或"generate"

class EmailDraft(BaseModel):
    recipient: str
    subject: str
    content: str

class EmailSendRequest(BaseModel):
    recipient: str
    subject: str = "AI辅助生成的邮件"
    content: str

class EmailTemplate(BaseModel):
    name: str
    subject: str
    content: str

# 定义请求体模型
class EmailConfigUpdate(BaseModel):
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    sender_email: str
    # 添加接收邮件的配置字段
    receive_type: str = "imap"  # imap 或 pop3
    receive_server: str = ""
    receive_port: int = 993
    receive_secure: str = "ssl"  # ssl, starttls 或 none
    check_frequency: str = "manual"  # manual, 5, 10, 15, 30, 60 分钟

class EmailConfig(BaseModel):
    smtp_server: str = ""  # 添加默认值
    smtp_port: int = 0  # 添加默认值
    smtp_username: str = ""
    smtp_password: str = ""
    sender_email: str = ""
    receive_type: str = "imap"
    receive_server: str = ""
    receive_port: int = 993
    receive_secure: str = "ssl"
    check_frequency: str = "manual"
    smtp_ssl: bool = True
    smtp_tls: bool = False
    receiving_ssl: bool = True
    receiving_tls: bool = False
    
    # 兼容性别名，便于在代码中使用
    @property
    def username(self) -> str:
        return self.smtp_username
        
    @property
    def password(self) -> str:
        return self.smtp_password
        
    @property
    def receiving_server(self) -> str:
        return self.receive_server
        
    @property
    def receiving_port(self) -> int:
        return self.receive_port
        
    @property
    def receiving_type(self) -> str:
        return self.receive_type

# 初始化数据库
def init_db():
    """初始化数据库，创建必要的表"""
    logger.info("开始初始化邮件数据库...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查数据库文件是否存在
        if not os.path.exists(DB_PATH):
            logger.info(f"数据库文件不存在，将创建新数据库: {DB_PATH}")
        else:
            logger.info(f"使用现有数据库文件: {DB_PATH}")
        
        # 创建草稿表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT,
            subject TEXT,
            content TEXT,
            date TEXT
        )
        ''')
        
        # 创建发件箱表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT,
            subject TEXT,
            content TEXT,
            date TEXT
        )
        ''')
        
        # 创建收件箱表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS inbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            subject TEXT,
            content TEXT,
            date TEXT,
            read INTEGER DEFAULT 0
        )
        ''')
        
        # 创建邮件模板表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            subject TEXT,
            content TEXT
        )
        ''')
        
        # 检查是否有表被成功创建
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"数据库中的表: {[table[0] for table in tables]}")
        
        # 添加测试数据
        # 检查表是否为空，如果为空则添加测试数据
        cursor.execute("SELECT COUNT(*) FROM inbox")
        inbox_count = cursor.fetchone()[0]
        
        if inbox_count == 0:
            logger.info("收件箱为空，添加测试数据")
            cursor.execute('''
            INSERT INTO inbox (sender, subject, content, date, read)
            VALUES (?, ?, ?, ?, ?)
            ''', ("sender@example.com", "测试邮件", "这是一封测试邮件内容", 
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0))
            
            # 添加一封已读邮件
            cursor.execute('''
            INSERT INTO inbox (sender, subject, content, date, read)
            VALUES (?, ?, ?, ?, ?)
            ''', ("another@example.com", "已读测试邮件", "这是一封已读测试邮件", 
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1))
        else:
            logger.info(f"收件箱已有 {inbox_count} 封邮件，不添加测试数据")
        
        # 检查草稿箱
        cursor.execute("SELECT COUNT(*) FROM drafts")
        drafts_count = cursor.fetchone()[0]
        
        if drafts_count == 0:
            logger.info("草稿箱为空，添加测试数据")
            cursor.execute('''
            INSERT INTO drafts (recipient, subject, content, date)
            VALUES (?, ?, ?, ?)
            ''', ("recipient@example.com", "草稿测试", "这是一封草稿邮件", 
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        else:
            logger.info(f"草稿箱已有 {drafts_count} 封草稿，不添加测试数据")
        
        conn.commit()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"初始化数据库出错: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 获取数据库连接
def get_db():
    db_path = os.path.join(os.path.dirname(__file__), '../data/email.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 返回字典而不是元组
    return conn

# 获取邮件配置的内部函数
def get_email_config_internal():
    """获取邮件配置（内部函数）"""
    try:
        # 创建默认配置
        default_config = EmailConfig()
        
        # 检查配置文件是否存在
        if not os.path.exists(CONFIG_FILE):
            logger.warning(f"配置文件不存在: {CONFIG_FILE}")
            return default_config
        
        # 读取配置文件
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                logger.info(f"成功读取配置: {CONFIG_FILE}")
                return EmailConfig(**config_data)
        except json.JSONDecodeError:
            logger.error(f"配置文件解析失败: {CONFIG_FILE}")
            return default_config
        except Exception as e:
            logger.error(f"读取配置文件出错: {str(e)}")
            return default_config
    except Exception as e:
        logger.error(f"获取邮件配置时出错: {str(e)}")
        return default_config

@router.get("/email/config")
async def get_email_config():
    """获取邮件配置API路由"""
    log_banner("读取邮件配置", "section")
    return get_email_config_internal()

# 发送邮件的后台任务
def send_email_task(recipient: str, subject: str, content: str):
    try:
        # 获取SMTP配置
        smtp_config = get_email_config_internal()
        
        # 创建邮件对象
        message = MIMEMultipart()
        message['From'] = smtp_config.sender_email
        message['To'] = recipient
        message['Subject'] = Header(subject, 'utf-8')
        
        # 添加邮件正文
        message.attach(MIMEText(content, 'plain', 'utf-8'))
        
        # 连接SMTP服务器并发送
        port = int(smtp_config.smtp_port)
        
        import ssl
        # 创建SSL上下文
        context = ssl.create_default_context()
        # 禁用主机名验证
        context.check_hostname = False
        
        if port == 465:
            # 使用SSL连接
            server = smtplib.SMTP_SSL(
                smtp_config.smtp_server, 
                port, 
                timeout=30,
                context=context
            )
        else:
            # 使用普通连接，需要STARTTLS
            server = smtplib.SMTP(
                smtp_config.smtp_server, 
                port, 
                timeout=30
            )
            server.ehlo()  # 确保先发送 EHLO 命令
            server.starttls(context=context)  # 启用TLS加密
            server.ehlo()  # TLS 连接后再次发送 EHLO
            
        server.login(smtp_config.smtp_username, smtp_config.smtp_password)
        server.sendmail(smtp_config.sender_email, recipient, message.as_string())
        server.quit()
        
        print(f"邮件已发送到 {recipient}")
    except Exception as e:
        print(f"发送邮件失败: {str(e)}")

@router.post("/email/generate-email")
async def generate_email(request: EmailGenerateRequest):
    print(f"POST /email/generate-email API被调用 subject='{request.subject}' intention='{request.intention}' recipient='{request.recipient}' mode='{request.mode}'")
    try:
        # 获取请求中的数据
        subject = request.subject
        intention = request.intention
        recipient = request.recipient
        mode = request.mode  # generate或polish模式
        
        # 记录关键参数
        print(f"邮件生成请求: 收件人={recipient}, 主题={subject}, 模式={mode}")
        
        # 确认与AI服务连接
        global global_llm
        if global_llm is None:
            print("LLM未初始化，尝试重新初始化...")
            if not initialize_llm():
                # 如果初始化失败，提前返回默认邮件
                default_content = "尊敬的收件人：\n\n您好！\n\n这是一封自动生成的邮件。由于AI服务暂时无法连接，无法提供个性化内容。\n\n请检查您的Ollama服务是否正常运行，并确保有可用的语言模型。\n\n谢谢您的理解。\n\n此致\n敬礼\n\n[系统自动生成]"
                return {
                    "content": default_content,
                    "recipient": recipient,
                    "subject": subject,
                    "full_content": f"收件人: {recipient}\n主题: {subject}\n内容:\n{default_content}"
                }
            
        # 构建提示词
        prompt = ""
        if mode == "generate":
            prompt = f"""
            请根据以下信息生成一封正式的商务邮件:
            收件人: {recipient}
            主题: {subject}
            意图: {intention}
            
            请生成完整的邮件内容，包含合适的称呼、正文、结束语和签名。
            必须严格按照以下格式返回:
            收件人:{recipient}
            主题:{subject}
            内容:[生成的邮件正文]
            
            重要: 不要在回复中包含任何思考过程或解释，直接输出最终邮件内容。不要使用<think>标签。
            """
        else:  # polish模式
            prompt = f"""
            请润色以下邮件内容，使其更加专业和得体:
            收件人: {recipient}
            主题: {subject}
            原始内容: {intention}
            
            润色时请注意以下几点：
            1. 调整格式，使用适当的段落划分，确保层次清晰
            2. 优化语言表达，使用更加专业的商务用语
            3. 添加适当的称呼和结束语
            4. 确保邮件格式规范，包括正确的缩进和间距
            5. 根据内容调整语气和语调，使其更加得体
            
            请返回润色后的完整邮件内容，包含合适的称呼、正文、结束语和签名。
            必须严格按照以下格式返回:
            收件人:{recipient}
            主题:{subject}
            内容:[润色后的邮件正文]
            
            重要: 不要在回复中包含任何思考过程或解释，直接输出最终邮件内容。不要使用<think>标签。
            """
        
        # 调用Ollama LLM
        try:
            print(f"开始调用Ollama LLM, 使用模型: {global_llm.model}")
            full_prompt = f"""系统: 你是一位专业的邮件写作助手，擅长撰写正式商务邮件。
            
你必须严格按照以下格式返回邮件内容，不要添加任何额外的说明、思考过程或解释:

收件人: [收件人地址]
主题: [邮件主题]
内容:
[完整邮件正文，包括称呼、正文、结束语和签名]

不要在回复中包含任何<think>标签、思考过程、分析步骤或其他解释。直接输出最终邮件内容。

用户: {prompt}"""
            
            email_content = global_llm.invoke(full_prompt)
            
            print(f"邮件内容生成完成，长度: {len(email_content) if email_content else 0}")
            
            # 清理内容，移除所有可能的思考过程
            if isinstance(email_content, str):
                # 移除各种可能的思考标记
                email_content = re.sub(r'<think>[\s\S]*?<\/think>', '', email_content)
                email_content = re.sub(r'<th\s*ink>[\s\S]*?<\/th\s*ink>', '', email_content)
                email_content = re.sub(r'【思考[:：][\s\S]*?】', '', email_content)
                email_content = re.sub(r'\[思考[:：][\s\S]*?\]', '', email_content)
                email_content = re.sub(r'（思考[:：][\s\S]*?）', '', email_content)
                email_content = re.sub(r'\(思考[:：][\s\S]*?\)', '', email_content)
                email_content = re.sub(r'接下来[我|我们|开始|将]', '', email_content)
                email_content = re.sub(r'首先[，|,]?我[需要|会|将]', '', email_content)
                email_content = re.sub(r'AI分析[:：][\s\S]*?(?=\n\n)', '', email_content)
                email_content = re.sub(r'思路[:：][\s\S]*?(?=\n\n)', '', email_content)
                email_content = re.sub(r'让我来[:：][\s\S]*?(?=\n\n)', '', email_content)
                
                # 格式化处理，确保格式统一
                email_content = email_content.strip()
                
                # 提取主题和收件人
                extracted_recipient = recipient
                extracted_subject = subject
                
                # 尝试从内容中提取更好的主题和收件人
                recipient_match = re.search(r'收件人[:：]\s*(.+?)[\n\r]', email_content)
                subject_match = re.search(r'主题[:：]\s*(.+?)[\n\r]', email_content)
                
                if recipient_match and recipient_match.group(1).strip() not in ["[收件人]", "[未指定]", "请填写收件人"]:
                    extracted_recipient = recipient_match.group(1).strip()
                
                if subject_match and subject_match.group(1).strip() not in ["[邮件主题]", "[未指定]", "请填写主题"]:
                    extracted_subject = subject_match.group(1).strip()
                
                # 提取纯正文内容
                content_match = re.search(r'内容[:：][\r\n]+(.+)', email_content, re.DOTALL)
                pure_content = ""
                if content_match:
                    pure_content = content_match.group(1).strip()
                else:
                    # 如果没有明确的"内容:"标记，尝试去除收件人和主题行
                    pure_content = email_content
                    if recipient_match:
                        pure_content = pure_content.replace(recipient_match.group(0), '')
                    if subject_match:
                        pure_content = pure_content.replace(subject_match.group(0), '')
                    pure_content = re.sub(r'内容[:：][\r\n]+', '', pure_content)
                    pure_content = pure_content.strip()
                
                # 再次清理纯内容中可能存在的思考内容
                pure_content = re.sub(r'<think>[\s\S]*?<\/think>', '', pure_content)
                pure_content = re.sub(r'<th\s*ink>[\s\S]*?<\/th\s*ink>', '', pure_content)
                pure_content = re.sub(r'【思考[:：][\s\S]*?】', '', pure_content)
                pure_content = re.sub(r'\[思考[:：][\s\S]*?\]', '', pure_content)
                pure_content = re.sub(r'（思考[:：][\s\S]*?）', '', pure_content)
                pure_content = re.sub(r'\(思考[:：][\s\S]*?\)', '', pure_content)
                pure_content = re.sub(r'接下来[我|我们|开始|将]', '', pure_content)
                pure_content = re.sub(r'首先[，|,]?我[需要|会|将]', '', pure_content)
                pure_content = re.sub(r'AI分析[:：][\s\S]*?(?=\n\n)', '', pure_content)
                pure_content = re.sub(r'思路[:：][\s\S]*?(?=\n\n)', '', pure_content)
                pure_content = re.sub(r'让我来[:：][\s\S]*?(?=\n\n)', '', pure_content)
                
                # 构建格式化的完整邮件内容（包含收件人和主题行）
                formatted_email = f"收件人: {extracted_recipient}\n主题: {extracted_subject}\n内容:\n{pure_content}"
                
                # 返回结构化数据
                result = {
                    "content": pure_content,
                    "recipient": extracted_recipient,
                    "subject": extracted_subject,
                    "full_content": formatted_email
                }
                
                print(f"成功生成邮件: 收件人={extracted_recipient}, 主题={extracted_subject}")
                return result
            else:
                # 可能是其他格式，尝试提取文本内容
                try:
                    default_content = "无法生成有效的邮件内容，请稍后再试。"
                    return {
                        "content": default_content,
                        "recipient": recipient,
                        "subject": subject,
                        "full_content": f"收件人: {recipient}\n主题: {subject}\n内容:\n{default_content}"
                    }
                except:
                    default_content = "无法生成有效的邮件内容，请稍后再试。"
                    return {
                        "content": default_content,
                        "recipient": recipient,
                        "subject": subject,
                        "full_content": f"收件人: {recipient}\n主题: {subject}\n内容:\n{default_content}"
                    }
        except Exception as inner_e:
            print(f"调用LLM时出错: {str(inner_e)}")
            
            # 尝试重新初始化LLM
            print("尝试重新初始化LLM...")
            initialize_llm()
            
            # 如果重新初始化成功，再次尝试
            if global_llm is not None:
                try:
                    email_content = global_llm.invoke(full_prompt)
                    print(f"重试成功，邮件长度: {len(email_content)}")
                    # 处理内容
                    if isinstance(email_content, str):
                        # 移除各种可能的思考标记
                        email_content = re.sub(r'<think>[\s\S]*?<\/think>', '', email_content)
                        email_content = re.sub(r'<th\s*ink>[\s\S]*?<\/th\s*ink>', '', email_content)
                        email_content = re.sub(r'【思考[:：][\s\S]*?】', '', email_content)
                        email_content = re.sub(r'\[思考[:：][\s\S]*?\]', '', email_content)
                        email_content = re.sub(r'（思考[:：][\s\S]*?）', '', email_content)
                        email_content = re.sub(r'\(思考[:：][\s\S]*?\)', '', email_content)
                        
                        # 格式化处理，确保格式统一
                        email_content = email_content.strip()
                        
                        # 提取主题和收件人
                        recipient_match = re.search(r'收件人[:：]\s*(.+?)[\n\r]', email_content)
                        subject_match = re.search(r'主题[:：]\s*(.+?)[\n\r]', email_content)
                        
                        extracted_recipient = recipient
                        if recipient_match and recipient_match.group(1).strip() not in ["[收件人]", "[未指定]", "请填写收件人"]:
                            extracted_recipient = recipient_match.group(1).strip()
                        
                        extracted_subject = subject
                        if subject_match and subject_match.group(1).strip() not in ["[邮件主题]", "[未指定]", "请填写主题"]:
                            extracted_subject = subject_match.group(1).strip()
                        
                        # 提取纯正文内容
                        content_match = re.search(r'内容[:：][\r\n]+(.+)', email_content, re.DOTALL)
                        if content_match:
                            pure_content = content_match.group(1).strip()
                        else:
                            # 如果没有明确的"内容:"标记，尝试去除收件人和主题行
                            pure_content = email_content
                            if recipient_match:
                                pure_content = pure_content.replace(recipient_match.group(0), '')
                            if subject_match:
                                pure_content = pure_content.replace(subject_match.group(0), '')
                            pure_content = re.sub(r'内容[:：][\r\n]+', '', pure_content)
                            pure_content = pure_content.strip()
                            
                        # 再次清理内容
                        pure_content = re.sub(r'<think>[\s\S]*?<\/think>', '', pure_content)
                        pure_content = re.sub(r'<th\s*ink>[\s\S]*?<\/th\s*ink>', '', pure_content)
                        
                        # 构建格式化的完整邮件内容（包含收件人和主题行）
                        formatted_email = f"收件人: {extracted_recipient}\n主题: {extracted_subject}\n内容:\n{pure_content}"
                        
                        # 返回结构化数据
                        return {
                            "content": pure_content,
                            "recipient": extracted_recipient,
                            "subject": extracted_subject,
                            "full_content": formatted_email
                        }
                except Exception as retry_error:
                    print(f"重试调用LLM失败: {str(retry_error)}")
            
            # 返回默认邮件
            default_content = "尊敬的收件人：\n\n您好！\n\n这是一封自动生成的邮件，因为AI服务暂时无法连接。请稍后再试。\n\n谢谢您的理解。\n\n此致\n敬礼"
            return {
                "content": default_content,
                "recipient": recipient,
                "subject": subject,
                "full_content": f"收件人: {recipient}\n主题: {subject}\n内容:\n{default_content}"
            }
            
    except Exception as e:
        print(f"邮件生成错误: {str(e)}")
        default_content = "生成邮件时遇到错误，请稍后再试。"
        return {
            "content": default_content,
            "recipient": recipient,
            "subject": subject,
            "full_content": f"收件人: {recipient}\n主题: {subject}\n内容:\n{default_content}"
        }

@router.post("/email/save-draft")
async def save_draft(draft: EmailDraft):
    """保存草稿到草稿箱"""
    print(f"保存草稿请求: recipient='{draft.recipient}' subject='{draft.subject}'")
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 插入新草稿
        cursor.execute(
            "INSERT INTO drafts (recipient, subject, content, date) VALUES (?, ?, ?, ?)",
            (draft.recipient, draft.subject, draft.content, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        
        draft_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"status": "success", "id": draft_id, "message": "草稿保存成功"}
    except Exception as e:
        print(f"保存草稿失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存草稿失败: {str(e)}")

@router.get("/email/drafts")
async def get_drafts():
    """获取所有草稿"""
    print("获取草稿箱请求")
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drafts ORDER BY date DESC")
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # 标准化返回格式
        for draft in results:
            # 确保字段名称一致
            if 'id' not in draft:
                draft['id'] = draft.get('id', f"draft_{datetime.datetime.now().timestamp()}_{id(draft)}")
            if 'recipient' not in draft:
                draft['recipient'] = draft.get('to', '')
            if 'content' not in draft:
                draft['content'] = draft.get('body', '')
            if 'date' not in draft:
                draft['date'] = draft.get('created_at', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # 使用标准格式返回
        return {"drafts": results}
    except Exception as e:
        print(f"获取草稿箱数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取草稿箱数据失败: {str(e)}")

@router.post("/email/send-email")
async def send_email(email: EmailSendRequest, background_tasks: BackgroundTasks):
    """发送邮件（实际发送）"""
    print(f"发送邮件请求: recipient='{email.recipient}' subject='{email.subject}' content='{email.content}'")
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 保存到发件箱
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO outbox (recipient, subject, content, date) VALUES (?, ?, ?, ?)",
            (email.recipient, email.subject, email.content, now)
        )
        email_id = cursor.lastrowid
        
        # 同时添加到收件箱（模拟）
        cursor.execute(
            "INSERT INTO inbox (sender, subject, content, date) VALUES (?, ?, ?, ?)",
            ("me@example.com", email.subject, email.content, now)
        )
        
        conn.commit()
        conn.close()
        
        # 在后台发送邮件
        background_tasks.add_task(send_email_task, email.recipient, email.subject, email.content)
        
        return {"status": "success", "email_id": email_id, "message": "邮件已加入发送队列"}
    except Exception as e:
        print(f"发送邮件失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送邮件失败: {str(e)}")

@router.get("/email/inbox")
async def get_inbox():
    """获取收件箱邮件"""
    print("获取收件箱请求")
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inbox ORDER BY date DESC")
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # 标准化返回格式
        for email in results:
            # 确保字段名称一致
            if 'id' not in email:
                email['id'] = email.get('id', f"inbox_{datetime.datetime.now().timestamp()}_{id(email)}")
            if 'sender' not in email:
                email['sender'] = email.get('from', 'unknown@example.com')
            if 'content' not in email:
                email['content'] = email.get('body', '')
            if 'date' not in email:
                email['date'] = email.get('created_at', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # 添加状态字段
            if 'status' not in email:
                email['status'] = 'read' if email.get('read', 0) == 1 else 'unread'
        
        # 使用标准格式返回
        return {"emails": results}
    except Exception as e:
        print(f"获取收件箱数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取收件箱数据失败: {str(e)}")

@router.get("/email/outbox")
async def get_outbox():
    """获取发件箱邮件"""
    print("获取发件箱请求")
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM outbox ORDER BY date DESC")
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # 标准化返回格式
        for email in results:
            # 确保字段名称一致
            if 'id' not in email:
                email['id'] = email.get('id', f"outbox_{datetime.datetime.now().timestamp()}_{id(email)}")
            if 'recipient' not in email:
                email['recipient'] = email.get('to', '')
            if 'content' not in email:
                email['content'] = email.get('body', '')
            if 'date' not in email:
                email['date'] = email.get('created_at', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # 添加状态字段
            if 'status' not in email:
                email['status'] = 'sent'
        
        # 使用标准格式返回
        return {"emails": results}
    except Exception as e:
        print(f"获取发件箱数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取发件箱数据失败: {str(e)}")

@router.delete("/email/drafts/{draft_id}")
async def delete_draft(draft_id: str):
    """删除草稿"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 先检查草稿是否存在
        cursor.execute("SELECT id FROM drafts WHERE id = ?", (draft_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"草稿 {draft_id} 不存在")
        
        # 删除草稿
        cursor.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"草稿 {draft_id} 已删除"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"更新邮件配置时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")

@router.get("/email/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """获取单个草稿详情"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"草稿 {draft_id} 不存在")
        
        result = dict(row)
        conn.close()
        print(f"获取草稿详情成功: {result}")
        return result
    except sqlite3.Error as e:
        print(f"数据库错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        print(f"获取草稿详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/email/drafts/{draft_id}")
async def update_draft(draft_id: str, draft: EmailDraft):
    """更新草稿"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE drafts SET recipient = ?, subject = ?, content = ? WHERE id = ?",
            (draft.recipient, draft.subject, draft.content, draft_id)
        )
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"草稿 {draft_id} 已更新"}
    except Exception as e:
        print(f"更新邮件配置时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")

@router.post("/email/test-connection")
async def test_email_connection(request: dict):
    """测试SMTP和接收邮件服务器连接"""
    print("调用/email/test-connection路由")
    try:
        # 解析请求参数
        smtp_server = request.get("smtp_server")
        smtp_port = request.get("smtp_port")
        receive_type = request.get("receive_type", "imap")
        receive_server = request.get("receive_server")
        receive_port = request.get("receive_port")
        receive_secure = request.get("receive_secure", "ssl")
        username = request.get("smtp_username", request.get("username", ""))  # 优先使用smtp_username，兼容老字段
        password = request.get("smtp_password", request.get("password", ""))  # 优先使用smtp_password，兼容老字段
        
        # 验证必要参数
        if not (smtp_server and smtp_port and username and password):
            raise HTTPException(status_code=400, detail="必须提供SMTP服务器信息和账号密码")
        
        # 构建EmailConfig对象用于测试
        config = EmailConfig(
            smtp_server=smtp_server,
            smtp_port=int(smtp_port),
            smtp_username=username,
            smtp_password=password,
            sender_email=username,
            receive_type=receive_type,
            receive_server=receive_server or "",
            receive_port=int(receive_port or 993),
            receive_secure=receive_secure,
            # 根据端口自动设置SSL/TLS
            smtp_ssl=int(smtp_port) == 465,
            smtp_tls=int(smtp_port) == 587,
            receiving_ssl=receive_secure == "ssl",
            receiving_tls=receive_secure == "starttls"
        )
        
        # 调用统一的测试连接方法
        response = await test_email_connection_internal(config)
        
        # 返回测试结果
        return {
            "smtp_test": {
                "result": "成功" if response["smtp"]["success"] else "失败",
                "error": None if response["smtp"]["success"] else response["smtp"]["message"]
            },
            "receive_test": {
                "result": "成功" if response["receiving"]["success"] else "失败",
                "error": None if response["receiving"]["success"] else response["receiving"]["message"]
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"连接测试过程中发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"连接测试过程中发生错误: {str(e)}")

# 内部测试连接方法，复用代码
async def test_email_connection_internal(config: EmailConfig):
    """测试电子邮件连接内部方法"""
    try:
        log_banner("测试邮件服务器连接", "section")
        
        results = {
            "smtp": {"success": False, "message": ""},
            "receiving": {"success": False, "message": ""}
        }
        
        # 测试SMTP连接
        logger.info(f"正在测试SMTP连接: {config.smtp_server}:{config.smtp_port}")
        try:
            if config.smtp_ssl:
                smtp = smtplib.SMTP_SSL(config.smtp_server, config.smtp_port, timeout=10)
            else:
                smtp = smtplib.SMTP(config.smtp_server, config.smtp_port, timeout=10)
            
            if config.smtp_tls:
                smtp.starttls()
            
            # 尝试登录
            smtp.login(config.smtp_username, config.smtp_password)
            smtp.quit()
            
            results["smtp"]["success"] = True
            results["smtp"]["message"] = "SMTP连接成功!"
            logger.info(colored("✓ SMTP连接测试成功!", "green"))
        except Exception as e:
            results["smtp"]["message"] = f"SMTP连接失败: {str(e)}"
            logger.error(colored(f"✗ SMTP连接测试失败: {str(e)}", "red"))
        
        # 测试接收服务器连接
        logger.info(f"正在测试接收服务器连接: {config.receive_server}:{config.receive_port}")
        try:
            if config.receiving_ssl:
                if config.receive_type.lower() == "imap":
                    imap = imaplib.IMAP4_SSL(config.receive_server, config.receive_port)
                    imap.login(config.smtp_username, config.smtp_password)
                    imap.logout()
                else:  # POP3
                    import poplib
                    pop = poplib.POP3_SSL(config.receive_server, config.receive_port)
                    pop.user(config.smtp_username)
                    pop.pass_(config.smtp_password)
                    pop.quit()
            else:
                if config.receive_type.lower() == "imap":
                    imap = imaplib.IMAP4(config.receive_server, config.receive_port)
                    if config.receiving_tls:
                        imap.starttls()
                    imap.login(config.smtp_username, config.smtp_password)
                    imap.logout()
                else:  # POP3
                    import poplib
                    pop = poplib.POP3(config.receive_server, config.receive_port)
                    if config.receiving_tls:
                        pop.stls()
                    pop.user(config.smtp_username)
                    pop.pass_(config.smtp_password)
                    pop.quit()
            
            results["receiving"]["success"] = True
            results["receiving"]["message"] = "接收服务器连接成功!"
            logger.info(colored(f"✓ {config.receive_type.upper()}接收服务器测试成功!", "green"))
        except Exception as e:
            results["receiving"]["message"] = f"接收服务器连接失败: {str(e)}"
            logger.error(colored(f"✗ {config.receive_type.upper()}接收服务器测试失败: {str(e)}", "red"))
        
        # 记录整体测试结果
        if results["smtp"]["success"] and results["receiving"]["success"]:
            log_system_event("邮件连接测试", "所有连接测试成功")
            log_banner("邮件服务器连接测试全部通过! ✅", "end")
        else:
            log_system_event("邮件连接测试", "部分连接测试失败")
            log_banner("邮件服务器连接测试存在问题! ❌", "end")
        
        return results
    except Exception as e:
        logger.error(f"邮件连接测试过程中发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试连接时出错: {str(e)}")

@router.post("/test-connection")
async def test_email_connection(config: EmailConfig):
    """测试电子邮件连接"""
    return await test_email_connection_internal(config)

@router.put("/email/config")
async def update_email_config(config: EmailConfigUpdate):
    """更新邮件配置"""
    try:
        log_banner("更新邮件配置", "section")
        logger.info(f"接收到的配置: {config}")
        
        # 确保配置目录存在
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        # 如果有原配置，先读取
        existing_config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    existing_config = json.load(f)
            except Exception as e:
                logger.warning(f"读取现有配置失败，将创建新配置: {str(e)}")
        
        # 合并新旧配置数据
        updated_config = {**existing_config}
        
        # 更新SMTP配置
        updated_config["smtp_server"] = config.smtp_server
        updated_config["smtp_port"] = config.smtp_port
        updated_config["smtp_username"] = config.smtp_username  # 修正：使用smtp_username而不是username
        updated_config["smtp_password"] = config.smtp_password  # 修正：使用smtp_password而不是password
        updated_config["sender_email"] = config.smtp_username   # 修正：使用smtp_username
        
        # 更新接收服务器配置
        updated_config["receive_type"] = config.receive_type or "imap"
        updated_config["receive_server"] = config.receive_server
        updated_config["receive_port"] = config.receive_port
        updated_config["receive_secure"] = config.receive_secure or "ssl"
        
        # 根据端口自动设置SSL/TLS
        updated_config["smtp_ssl"] = config.smtp_port == 465
        updated_config["smtp_tls"] = config.smtp_port == 587
        updated_config["receiving_ssl"] = config.receive_secure == "ssl"
        updated_config["receiving_tls"] = config.receive_secure == "starttls"
        
        # 保存配置到文件
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(updated_config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"邮件配置已成功保存到: {CONFIG_FILE}")
            return {"status": "成功", "message": "邮件配置已更新"}
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"保存配置文件失败: {str(e)}")
    except Exception as e:
        logger.error(f"保存邮件配置时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新邮件配置失败: {str(e)}")

# 添加路由启动事件，确保LLM初始化
@router.on_event("startup")
async def startup_event():
    print("邮件模块启动，初始化LLM...")
    initialize_llm()
    print_routes()

@router.get("/email/ping")
async def ping():
    """简单的ping接口，用于前端检查后端连接状态"""
    return {"status": "ok", "message": "Email API服务正常"}

print_routes() # 打印所有路由 

@router.get("/config", response_model=EmailConfig)
async def get_config():
    """获取电子邮件配置"""
    try:
        # 使用彩色输出
        log_banner("获取邮件系统配置", "info")
        
        # 创建默认配置
        default_config = EmailConfig()
        
        if not os.path.exists(CONFIG_FILE):
            # 如果配置文件不存在，返回默认配置
            logger.warning(f"配置文件 {CONFIG_FILE} 不存在，使用默认配置")
            return default_config
        
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                logger.info("成功读取邮件配置文件")
                return EmailConfig(**config_data)
        except json.JSONDecodeError:
            logger.error(f"配置文件 {CONFIG_FILE} 解析失败，使用默认配置")
            return default_config
        except Exception as e:
            logger.error(f"读取配置文件时出错: {str(e)}，使用默认配置")
            return default_config
    except Exception as e:
        # 记录错误
        logger.error(f"读取邮件配置时出错: {str(e)}")
        # 返回默认配置而不是抛出异常
        return default_config

@router.post("/config", response_model=EmailConfig)
@router.put("/config", response_model=EmailConfig)
async def update_config(config: EmailConfig):
    """更新电子邮件配置"""
    try:
        # 使用彩色输出
        log_banner("更新邮件系统配置", "info")
        
        # 确保配置目录存在
        config_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(config_dir):
            logger.info(f"创建配置目录: {config_dir}")
            os.makedirs(config_dir, exist_ok=True)
        
        # 保存配置到文件
        try:
            logger.info(f"保存配置到: {CONFIG_FILE}")
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config.dict(), f, ensure_ascii=False, indent=2)
                
            logger.info(f"邮件配置已更新并保存")
            return config
        except Exception as e:
            logger.error(f"写入配置文件时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=f"配置保存失败: {str(e)}")
    except Exception as e:
        # 记录错误
        logger.error(f"保存邮件配置时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"配置保存失败: {str(e)}")

@router.post("/email/check-new-mails")
async def check_new_mails():
    """检查并获取新邮件"""
    try:
        logger.info("开始检查新邮件")
        
        # 获取邮件配置
        config = get_email_config_internal()
        
        # 如果没有配置接收服务器，返回空结果
        if not config.receive_server:
            logger.warning("未配置接收服务器，无法检查新邮件")
            return {"status": "warning", "message": "未配置接收服务器", "new_mails": []}
        
        # 模拟检查新邮件（开发环境）
        if os.environ.get("DEV_MODE", "False").lower() == "true":
            logger.info("开发模式：模拟获取新邮件")
            
            # 连接数据库
            conn = get_db()
            cursor = conn.cursor()
            
            # 模拟接收一封新邮件
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sender = "sender@example.com"
            subject = f"测试邮件 {now}"
            content = f"这是一封测试邮件，生成于 {now}。\n\n此邮件由系统自动生成，用于测试收件箱功能。"
            
            # 插入到收件箱
            cursor.execute(
                "INSERT INTO inbox (sender, recipient, subject, content, date) VALUES (?, ?, ?, ?, ?)",
                (sender, config.smtp_username, subject, content, now)
            )
            
            mail_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # 返回模拟的新邮件
            return {
                "status": "success", 
                "message": "成功接收1封新邮件",
                "new_mails": [
                    {
                        "id": mail_id,
                        "sender": sender,
                        "recipient": config.smtp_username,
                        "subject": subject,
                        "content": content,
                        "date": now
                    }
                ]
            }
        
        # 实际环境下从邮件服务器获取邮件
        try:
            logger.info(f"正在连接邮件服务器: {config.receive_server}:{config.receive_port}")
            
            # 根据配置选择IMAP或POP3
            if config.receive_type.lower() == "imap":
                # 使用IMAP收取邮件
                new_mails = await fetch_emails_via_imap(config)
            else:
                # 使用POP3收取邮件
                new_mails = await fetch_emails_via_pop3(config)
                
            # 返回获取到的新邮件
            if new_mails:
                return {
                    "status": "success",
                    "message": f"成功接收{len(new_mails)}封新邮件",
                    "new_mails": new_mails
                }
            else:
                return {
                    "status": "info",
                    "message": "没有新邮件",
                    "new_mails": []
                }
        except Exception as e:
            logger.error(f"从邮件服务器获取邮件时出错: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取邮件失败: {str(e)}")
            
    except Exception as e:
        logger.error(f"检查新邮件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查新邮件时出错: {str(e)}")

async def fetch_emails_via_imap(config: EmailConfig):
    """通过IMAP协议获取邮件"""
    try:
        # 连接IMAP服务器
        if config.receiving_ssl:
            imap = imaplib.IMAP4_SSL(config.receive_server, config.receive_port)
        else:
            imap = imaplib.IMAP4(config.receive_server, config.receive_port)
            if config.receiving_tls:
                imap.starttls()
        
        # 登录
        imap.login(config.smtp_username, config.smtp_password)
        
        # 选择收件箱
        imap.select('INBOX')
        
        # 搜索未读邮件
        status, data = imap.search(None, 'UNSEEN')
        if status != 'OK':
            logger.warning("没有找到未读邮件")
            imap.logout()
            return []
        
        # 获取邮件ID列表
        mail_ids = data[0].split()
        if not mail_ids:
            logger.info("没有未读邮件")
            imap.logout()
            return []
        
        logger.info(f"找到 {len(mail_ids)} 封未读邮件")
        
        # 连接数据库
        conn = get_db()
        cursor = conn.cursor()
        
        new_mails = []
        
        # 获取每封邮件
        for mail_id in mail_ids[:10]:  # 最多处理10封邮件
            status, data = imap.fetch(mail_id, '(RFC822)')
            if status != 'OK':
                continue
                
            # 解析邮件
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # 提取发件人和主题
            sender = email.utils.parseaddr(msg['From'])[1]
            subject = msg.get('Subject', '')
            if subject.startswith('=?'):
                # 解码主题
                try:
                    subject, encoding = email.header.decode_header(subject)[0]
                    if isinstance(subject, bytes) and encoding:
                        subject = subject.decode(encoding)
                except:
                    subject = "无法解码的主题"
            
            # 提取正文
            content = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            charset = part.get_content_charset() or 'utf-8'
                            content = part.get_payload(decode=True).decode(charset)
                            break
                        except:
                            content = "无法解码的邮件内容"
            else:
                try:
                    charset = msg.get_content_charset() or 'utf-8'
                    content = msg.get_payload(decode=True).decode(charset)
                except:
                    content = "无法解码的邮件内容"
            
            # 获取日期
            date_str = msg.get('Date', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            try:
                # 尝试将邮件日期转换为标准格式
                parsed_date = email.utils.parsedate_to_datetime(date_str)
                date = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            except:
                # 如果解析失败，使用当前时间
                date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 插入到收件箱
            cursor.execute(
                "INSERT INTO inbox (sender, recipient, subject, content, date) VALUES (?, ?, ?, ?, ?)",
                (sender, config.smtp_username, subject, content, date)
            )
            
            mail_id_db = cursor.lastrowid
            
            # 添加到结果列表
            new_mails.append({
                "id": mail_id_db,
                "sender": sender,
                "recipient": config.smtp_username,
                "subject": subject,
                "content": content,
                "date": date
            })
            
            logger.info(f"已保存邮件: {subject} (从 {sender})")
        
        # 提交更改并关闭连接
        conn.commit()
        conn.close()
        imap.logout()
        
        return new_mails
        
    except Exception as e:
        logger.error(f"通过IMAP获取邮件时出错: {str(e)}")
        raise e

async def fetch_emails_via_pop3(config: EmailConfig):
    """通过POP3协议获取邮件"""
    try:
        import poplib
        
        # 连接到POP3服务器
        if config.receiving_ssl:
            pop3 = poplib.POP3_SSL(config.receive_server, config.receive_port)
        else:
            pop3 = poplib.POP3(config.receive_server, config.receive_port)
            if config.receiving_tls:
                pop3.stls()
        
        # 登录
        pop3.user(config.smtp_username)
        pop3.pass_(config.smtp_password)
        
        # 获取邮件数量和大小
        mail_count, total_size = pop3.stat()
        logger.info(f"邮箱中有 {mail_count} 封邮件，总大小 {total_size} 字节")
        
        if mail_count == 0:
            pop3.quit()
            return []
        
        # 连接数据库
        conn = get_db()
        cursor = conn.cursor()
        
        new_mails = []
        
        # 获取最新的10封邮件
        start = max(1, mail_count - 9)
        for i in range(start, mail_count + 1):
            # 获取邮件
            response, lines, octets = pop3.retr(i)
            
            # 将邮件内容合并为一个字符串
            raw_email = b'\r\n'.join(lines)
            
            # 解析邮件
            msg = email.message_from_bytes(raw_email)
            
            # 提取发件人和主题
            sender = email.utils.parseaddr(msg['From'])[1]
            subject = msg.get('Subject', '')
            if subject.startswith('=?'):
                # 解码主题
                try:
                    subject, encoding = email.header.decode_header(subject)[0]
                    if isinstance(subject, bytes) and encoding:
                        subject = subject.decode(encoding)
                except:
                    subject = "无法解码的主题"
            
            # 提取正文
            content = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            charset = part.get_content_charset() or 'utf-8'
                            content = part.get_payload(decode=True).decode(charset)
                            break
                        except:
                            content = "无法解码的邮件内容"
            else:
                try:
                    charset = msg.get_content_charset() or 'utf-8'
                    content = msg.get_payload(decode=True).decode(charset)
                except:
                    content = "无法解码的邮件内容"
            
            # 获取日期
            date_str = msg.get('Date', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            try:
                # 尝试将邮件日期转换为标准格式
                parsed_date = email.utils.parsedate_to_datetime(date_str)
                date = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            except:
                # 如果解析失败，使用当前时间
                date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 插入到收件箱
            cursor.execute(
                "INSERT INTO inbox (sender, recipient, subject, content, date) VALUES (?, ?, ?, ?, ?)",
                (sender, config.smtp_username, subject, content, date)
            )
            
            mail_id = cursor.lastrowid
            
            # 添加到结果列表
            new_mails.append({
                "id": mail_id,
                "sender": sender,
                "recipient": config.smtp_username,
                "subject": subject,
                "content": content,
                "date": date
            })
            
            logger.info(f"已保存邮件: {subject} (从 {sender})")
        
        # 提交更改并关闭连接
        conn.commit()
        conn.close()
        pop3.quit()
        
        return new_mails
        
    except Exception as e:
        logger.error(f"通过POP3获取邮件时出错: {str(e)}")
        raise e
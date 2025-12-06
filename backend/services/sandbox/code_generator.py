"""
代码生成服务模块

该模块提供了使用LLM（大语言模型）将自然语言提示转换为Python数据分析代码的功能。
使用Ollama服务对接Qwen2.5模型来生成代码。
"""

import asyncio
import traceback
import re
import time  # 用于记录时间
from typing import Optional, List, Dict, Tuple, Any
from loguru import logger # type: ignore
from langchain_ollama import OllamaLLM
import numpy as np

# 初始化LLM客户端
ollama_client = None

def init_ollama_client():
    """初始化Ollama LLM客户端"""
    global ollama_client
    try:
        # 打印更详细的日志
        logger.info("尝试连接Ollama服务...")
        logger.info(f"Ollama服务地址: http://localhost:11434")
        logger.info(f"模型名称: qwen2:7b")
        
        # 尝试连接到本地部署的Ollama服务，使用Qwen2.5:7b模型
        ollama_client = OllamaLLM(
            model="qwen2:7b",  # 正确的模型名称，与您安装的匹配
            base_url="http://localhost:11434",  # Ollama服务地址
            temperature=0.3,  # 低温度，使代码生成更确定性
            timeout=30  # 超时设置
        )
        # 测试连接
        test_response = ollama_client.invoke("测试连接，返回'连接成功'")
        logger.info(f"Ollama测试响应: {test_response}")
        logger.info("成功初始化Ollama LLM客户端")
    except Exception as e:
        logger.error(f"初始化Ollama LLM客户端失败: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        ollama_client = None

# 尝试初始化Ollama客户端
init_ollama_client()

async def process_chat_message(
    message: str, 
    history: List[Dict[str, str]], 
    has_file: bool
) -> Tuple[str, bool, Optional[str]]:
    """处理用户的聊天消息并生成响应
    
    Args:
        message: 用户的消息
        history: 聊天历史记录
        has_file: 是否已上传文件
        
    Returns:
        元组 (响应文本, 是否可以开始分析, 最终提示词)
    """
    global ollama_client
    
    # 如果LLM客户端未初始化，尝试重新初始化
    if ollama_client is None:
        try:
            init_ollama_client()
        except Exception as e:
            logger.error(f"初始化LLM客户端失败: {str(e)}")
            
        # 如果仍然无法初始化
        if ollama_client is None:
            return "抱歉，AI服务暂时不可用。请稍后再试。", False, None
    
    try:
        # 检查是否已上传文件
        if not has_file:
            return "请先上传CSV文件，然后再描述您想要的分析。", False, None
            
        # 解析聊天历史，确定当前对话阶段
        try:
            conversation_state = determine_conversation_state(history)
        except Exception as e:
            logger.error(f"确定对话状态失败: {str(e)}")
            # 如果确定状态失败，默认为初始状态
            conversation_state = "initial"
        
        logger.info(f"当前对话状态: {conversation_state}")
        
        # 检查是否直接提供了列名信息
        column_info = extract_column_info_fallback(message, [])
        if column_info and ("列名" in message or "字段" in message or "：" in message or ":" in message):
            logger.info(f"用户直接提供了列信息: {column_info}")
            conversation_state = "column_info_provided"
        
        try:
            if conversation_state == "initial":
                # 第一轮：用户刚提出分析请求，AI理解并询问数据列
                return await handle_initial_request(message)
                
            elif conversation_state == "column_info_provided":
                # 第二轮：用户提供了列信息，AI确认数据类型
                return await handle_column_confirmation(message, history)
                
            elif conversation_state == "confirmation":
                # 第三轮：用户确认后，准备生成最终代码
                # 直接进入分析阶段，不再提问
                logger.info("用户已确认，准备生成最终代码")
                
                # 获取最终提示词
                response, analysis_ready, final_prompt = await handle_final_confirmation(message, history)
                
                # 确保设置analysis_ready为True，表示可以开始分析
                if analysis_ready:
                    logger.info(f"分析准备就绪，最终提示词: {final_prompt}")
                    return "非常好！我已经准备好为您生成分析代码了。请点击'开始分析'按钮，我将基于您提供的信息进行数据分析。", True, final_prompt
                else:
                    # 如果handle_final_confirmation没有设置analysis_ready，强制设置为True
                    logger.info("强制设置analysis_ready为True")
                    return response, True, final_prompt
                
            else:
                # 如果对话已经完成，则重新开始
                return await handle_initial_request(message)
        except Exception as e:
            logger.error(f"处理对话状态失败: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 如果使用LLM处理失败，尝试简单文本分析确定是否可以开始分析
            if "是" in message or "确认" in message or "开始" in message or "好" in message or "对" in message:
                # 提取列名
                column_info = extract_column_info_fallback(message, history) or "地区,销售额,利润,成本"
                final_prompt = f"分析CSV数据，列名为: {column_info}"
                return "分析即将开始，请稍等...", True, final_prompt
            else:
                return f"抱歉，处理您的请求时出现了错误。您可以尝试直接输入'开始分析'来继续。", False, None
    
    except Exception as e:
        logger.error(f"处理聊天消息失败: {str(e)}")
        logger.error(traceback.format_exc())
        return f"抱歉，处理您的请求时出现了错误。您可以尝试重新上传文件或重新开始对话。", False, None

def determine_conversation_state(history: List[Dict[str, str]]) -> str:
    """根据聊天历史确定当前对话状态
    
    Args:
        history: 聊天历史记录
        
    Returns:
        对话状态: initial, column_info_provided, confirmation, completed
    """
    if not history:
        return "initial"
    
    # 查找AI最后一条消息
    ai_messages = [msg for msg in history if msg.get('role') == 'assistant']
    if not ai_messages:
        return "initial"
    
    last_ai_message = ai_messages[-1]['content']
    
    # 检查最后一条AI消息是否在要求提供列信息
    if ("能否告诉我您CSV文件中包含哪些列名" in last_ai_message or 
        "请提供CSV文件的列名" in last_ai_message or 
        "告诉我您CSV文件中包含哪些列名" in last_ai_message or
        "包含哪些列" in last_ai_message):
        # 查看用户是否已回复
        if len(history) > len(ai_messages) and history[-1].get('role') == 'user':
            # 检查用户回复是否包含列信息相关关键词
            user_reply = history[-1]['content'].lower()
            column_keywords = ['列', 'csv', '包含', '数据', '字段', '：', ':', ',', '，', '有']
            if any(keyword in user_reply for keyword in column_keywords):
                return "column_info_provided"
        return "initial"
    
    # 检查是否是确认数据类型的消息（第二阶段的AI回复）
    confirmation_keywords = [
        "这样的理解正确吗", 
        "理解正确吗", 
        "可以开始分析",
        "我理解您的CSV文件包含以下列",
        "如果正确"
    ]
    
    if any(keyword in last_ai_message for keyword in confirmation_keywords) and len(history) > len(ai_messages) and history[-1].get('role') == 'user':
        # 用户对确认消息已经回复，进入确认阶段
        user_reply = history[-1]['content'].lower().strip()
        # 如果用户回复是简单的肯定或否定，直接判断为确认阶段
        if re.search(r'^(是|确认|正确|可以|好的?|对的?|没问题|开始|继续|分析)$', user_reply) or len(user_reply) < 15:
            return "confirmation"
        
        # 如果用户提供了新的分析需求，也视为确认阶段
        if "分析" in user_reply or "查找" in user_reply or "计算" in user_reply:
            return "confirmation"
    
    # 检查是否已经确认要生成代码
    if "生成分析代码" in last_ai_message and "已准备就绪" in last_ai_message:
        return "completed"
    
    # 如果用户最后一条消息提到了列名，也认为已提供列信息
    if len(history) >= 2 and history[-1].get('role') == 'user':
        user_message = history[-1]['content'].lower()
        if ('列名' in user_message or '字段' in user_message or 
            (('列' in user_message or 'csv' in user_message) and 
             any(x in user_message for x in ['地区', '销售', '利润', '成本', '日期']))):
            return "column_info_provided"   
    
    # 默认状态
    return "initial"

async def handle_initial_request(message: str) -> Tuple[str, bool, Optional[str]]:
    """处理用户的初始分析请求
    
    Args:
        message: 用户的消息
        
    Returns:
        元组 (响应文本, 是否可以开始分析, 最终提示词)
    """
    system_prompt = """你是一个专业的数据分析助手。你的任务是理解用户的数据分析需求，并帮助他们分析CSV文件数据。
请用自然的对话方式与用户交流，理解用户提供的信息，包括他们可能提到的CSV列名。
无需要求用户使用特定格式回复，而是从他们的自然语言描述中提取信息。"""
    
    try:
        # 组合系统提示和用户消息
        response = ollama_client.invoke(f"{system_prompt}\n\n用户消息: {message}")
        return response, False, None
    except Exception as e:
        logger.error(f"处理初始请求失败: {str(e)}")
        return f"抱歉，处理您的请求时出现了错误: {str(e)}", False, None

async def extract_column_info_with_llm(message: str, history: List[Dict[str, str]]) -> str:
    """使用LLM从用户消息中提取列名信息
    
    Args:
        message: 当前用户消息
        history: 聊天历史记录
        
    Returns:
        提取出的列名信息
    """
    # 首先尝试使用简单的文本分析提取列名（作为后备方案）
    extracted_info = extract_column_info_fallback(message, history)
    if extracted_info:
        logger.info(f"通过后备方法提取的列名: {extracted_info}")
        return extracted_info
    
    global ollama_client
    
    # 如果LLM客户端未初始化，尝试初始化，失败后使用后备方案
    if ollama_client is None:
        try:
            init_ollama_client()
        except Exception as e:
            logger.error(f"初始化LLM客户端失败: {str(e)}")
            return extract_column_info_fallback(message, history) or message
    
    # 如果仍然没有LLM客户端，使用后备方案
    if ollama_client is None:
        logger.error("无法初始化LLM客户端，使用后备方法提取列名")
        return extract_column_info_fallback(message, history) or message
    
    try:
        # 构建提取列名的系统提示
        system_prompt = """你是一个专业的数据分析助手。现在你需要从用户的消息中提取CSV文件的列名信息。
请分析用户消息和对话历史，找出所有提到的列名。仅返回提取到的列名，格式为逗号分隔的列表。
例如："地区,销售额,利润,成本"。如果没有明确提及列名，请返回"未找到列名信息"。"""

        # 收集对话历史中的所有用户消息
        user_messages = []
        if history:
            for msg in history:
                if msg.get('role') == 'user':
                    user_messages.append(msg.get('content', ''))
        
        # 添加当前消息
        if message:
            user_messages.append(message)
        
        # 构建完整提示
        context = f"{system_prompt}\n\n用户历史消息: {' | '.join(user_messages)}\n\n请提取所有提到的列名:"
        
        # 调用LLM，添加超时保护
        logger.info("使用LLM提取列名信息...")
        try:
            # 设置超时，防止长时间阻塞
            response = ollama_client.invoke(context)
            
            # 清理响应
            response = response.strip()
            logger.info(f"LLM提取的列名: {response}")
            
            if "未找到" in response or len(response) < 2:
                # 如果没有提取到有效信息，尝试后备方法
                fallback_result = extract_column_info_fallback(message, history)
                return fallback_result or message
                
            return response
        except Exception as e:
            logger.error(f"调用LLM提取列名失败: {str(e)}")
            # 当LLM调用失败时使用后备方法
            fallback_result = extract_column_info_fallback(message, history)
            return fallback_result or message
            
    except Exception as e:
        logger.error(f"使用LLM提取列名失败: {str(e)}")
        # 如果发生任何错误，使用后备方法
        fallback_result = extract_column_info_fallback(message, history)
        return fallback_result or message

def extract_column_info_fallback(message: str, history: List[Dict[str, str]]) -> Optional[str]:
    """使用简单的文本分析从用户消息中提取列名信息（作为LLM的后备方案）
    
    Args:
        message: 当前用户消息
        history: 聊天历史记录
        
    Returns:
        提取出的列名信息或None
    """
    # 定义可能包含列名的关键词
    column_indicators = ['列名', '字段', '列', '包含', 'csv', '：', ':', '为']
    
    # 首先检查当前消息
    if message:
        # 检查是否是明确的列名格式
        colon_match = re.search(r'[:：][ \t]*([\w,，、 \t]+)', message)
        if colon_match:
            columns = colon_match.group(1)
            # 替换各种中文分隔符为英文逗号
            columns = re.sub(r'[，、 \t]+', ',', columns)
            # 清理多余的逗号
            columns = re.sub(r',+', ',', columns)
            # 清理首尾逗号
            columns = columns.strip(',')
            if columns:
                return columns
        
        # 查找逗号分隔的单词列表
        if ',' in message or '，' in message:
            # 替换中文逗号为英文逗号
            normalized = message.replace('，', ',')
            # 尝试提取逗号分隔的部分
            parts = [p.strip() for p in normalized.split(',')]
            if len(parts) >= 2:
                # 过滤掉空部分和过长的部分（可能不是列名）
                columns = [p for p in parts if p and len(p) < 20]
                if len(columns) >= 2:
                    return ','.join(columns)
    
    # 如果当前消息没有找到列名，检查历史消息
    if history:
        for msg in reversed(history):  # 从最近的消息开始
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                
                # 检查是否包含列名相关关键词
                if any(indicator in content for indicator in column_indicators):
                    # 递归调用自身来分析这条历史消息
                    result = extract_column_info_fallback(content, [])
                    if result:
                        return result
                    
                    # 如果上面的方法失败，尝试更简单的提取方法
                    # 查找常见列名
                    common_columns = ['地区', '销售', '利润', '成本', '日期', '价格', '数量']
                    found_columns = []
                    for col in common_columns:
                        if col in content:
                            found_columns.append(col)
                    
                    if len(found_columns) >= 2:
                        return ','.join(found_columns)
    
    # 如果所有方法都失败，返回None
    return None

async def handle_column_confirmation(message: str, history: List[Dict[str, str]]) -> Tuple[str, bool, Optional[str]]:
    """处理用户提供的列信息并确认数据类型
    
    Args:
        message: 用户提供的列信息
        history: 聊天历史
        
    Returns:
        元组 (响应文本, 是否可以开始分析, 最终提示词)
    """
    # 获取用户最初的分析需求
    initial_request = ""
    for msg in history:
        if msg.get('role') == 'user':
            initial_request = msg['content']
            logger.info(f"从历史记录中找到用户消息: {initial_request}")
            break  # 找到第一条用户消息就停止
    
    # 使用LLM提取列信息，而不是简单的关键词匹配
    column_info = await extract_column_info_with_llm(message, history)
    
    logger.info(f"提取的列信息: {column_info}")
    
    # 生成后备响应
    fallback_response = generate_column_confirmation_fallback(column_info)
    
    # 如果LLM客户端未初始化，直接返回后备响应
    if ollama_client is None:
        logger.warning("LLM客户端未初始化，使用后备响应")
        return fallback_response, False, None
    
    system_prompt = """你是一个专业的数据分析助手。请理解用户提供的CSV列名信息，并根据列名推测可能的数据类型。
在回复中，确认你对列名和数据类型的理解，不要讨论可能的分析方向。
最后请明确询问用户："这样的理解正确吗？如果正确，我们可以开始分析。"
保持回复简洁，重点放在确认数据结构上。"""
    
    try:
        # 构建上下文
        context = f"{system_prompt}\n\n用户最初的分析需求: {initial_request}\n用户提供的信息: {column_info}"
        logger.info(f"LLM请求上下文: {context}")
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 调用LLM并获取原始响应
        try:
            raw_response = ollama_client.invoke(context)
            
            # 记录请求时间和原始响应
            elapsed_time = time.time() - start_time
            logger.info(f"LLM请求完成，耗时: {elapsed_time:.2f}秒")
            
            # 转为字符串并清洗响应，确保安全返回
            response_text = str(raw_response)
            
            # 修复可能导致前端解析错误的特殊字符问题
            # 1. 移除前导和尾随的引号
            response_text = response_text.strip('\'"')
            
            # 2. 处理换行符，确保在前端正确显示
            response_text = response_text.replace('\\n', '\n')
            
            # 记录清洗后的响应
            logger.info(f"清洗后的响应: {response_text[:100]}...")
            
            return response_text, False, None
            
        except Exception as llm_error:
            # 记录LLM调用的具体错误
            logger.error(f"LLM调用错误: {str(llm_error)}")
            logger.error(f"错误类型: {type(llm_error).__name__}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 返回后备响应
            return fallback_response, False, None
            
    except Exception as e:
        # 记录整个处理过程的错误
        logger.error(f"列信息确认处理失败: {str(e)}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        
        # 返回后备响应
        return fallback_response, False, None

async def handle_final_confirmation(message: str, history: List[Dict[str, str]]) -> Tuple[str, bool, Optional[str]]:
    """处理用户的最终确认，准备生成代码
    
    Args:
        message: 用户的确认消息
        history: 聊天历史
        
    Returns:
        元组 (响应文本, 是否可以开始分析, 最终提示词)
    """
    # 改进历史搜索逻辑，通过多种策略查找用户的分析需求
    analysis_keywords = ["分析", "查询", "统计", "计算", "找出", "展示", "可视化", "比较", "预测", "找到"]
    
    # 策略1: 首先检查当前消息是否包含分析需求
    logger.info(f"检查当前消息是否包含分析需求: {message}")
    current_message_is_analysis = False
    if len(message) > 10 and any(keyword in message for keyword in analysis_keywords):
        analysis_request = message
        current_message_is_analysis = True
        logger.info(f"当前消息包含分析需求关键词，使用当前消息: {analysis_request}")
    else:
        analysis_request = ""
        logger.info("当前消息不包含明确的分析需求")
    
    # 策略2: 如果当前消息不是分析需求，从历史中查找最可能的分析需求
    if not current_message_is_analysis:
        # 创建一个评分系统，为每条用户消息评分，找出最可能的分析需求
        candidate_requests = []
        for i, msg in enumerate(history):
            if msg.get('role') == 'user':
                content = msg['content']
                # 计算分析关键词的出现次数
                keyword_count = sum(1 for keyword in analysis_keywords if keyword in content)
                # 如果消息较长且包含关键词，可能是分析需求
                if len(content) > 15 and keyword_count > 0:
                    # 创建候选项，包含消息内容、位置和关键词分数
                    candidate_requests.append({
                        'content': content,
                        'position': i,  # 位置靠前的优先级高
                        'score': keyword_count + (len(content) > 30) * 2  # 更长的消息得分更高
                    })
                    logger.info(f"找到候选分析需求 #{i}: {content[:50]}... (得分: {keyword_count})")
        
        # 如果有候选项，选择得分最高的
        if candidate_requests:
            # 根据得分和位置排序（优先考虑得分，其次考虑位置靠前的）
            sorted_candidates = sorted(candidate_requests, 
                                      key=lambda x: (x['score'], -x['position']), 
                                      reverse=True)
            analysis_request = sorted_candidates[0]['content']
            logger.info(f"从历史中选择得分最高的分析需求: {analysis_request[:50]}...")
        else:
            # 如果没有找到合适的候选项，使用第一条用户消息
            for msg in history:
                if msg.get('role') == 'user':
                    analysis_request = msg['content']
                    logger.info(f"未找到明确的分析需求，使用第一条用户消息: {analysis_request[:50]}...")
                    break
    
    # 如果仍然没有找到分析需求，使用当前消息作为后备
    if not analysis_request:
        analysis_request = message
        logger.info(f"未从历史中找到分析需求，使用当前消息: {analysis_request}")
    
    # 使用LLM从整个历史中提取列信息
    column_info = await extract_column_info_with_llm("", history)
    
    # 预处理分析需求文本，替换中文标点为英文标点
    logger.info(f"预处理前的分析需求: {analysis_request}")
    analysis_request = analysis_request.replace('，', ',').replace('；', ';').replace('：', ':').replace('。', '.').replace('？', '?').replace('！', '!')
    logger.info(f"预处理后的分析需求: {analysis_request}")

    # 预处理列信息，替换中文标点为英文标点
    logger.info(f"预处理前的列信息: {column_info}")
    column_info = column_info.replace('，', ',').replace('；', ';').replace('：', ':')
    logger.info(f"预处理后的列信息: {column_info}")
    
    # 确保分析需求不为空
    if not analysis_request or analysis_request.strip() == "":
        analysis_request = "请分析CSV数据"
        logger.warning(f"分析需求为空，使用默认分析需求: {analysis_request}")
    
    # 构建最终的提示词，清晰地区分用户需求和列信息，确保格式一致性
    final_prompt = f"用户分析需求: {analysis_request.strip()}\n数据列信息: {column_info.strip()}"
    logger.info(f"最终提示词: {final_prompt}")
    
    # 验证提示词格式是否正确
    prompt_parts = final_prompt.split("\n")
    if len(prompt_parts) >= 2 and "用户分析需求" in prompt_parts[0] and "数据列信息" in prompt_parts[1]:
        logger.info("提示词格式验证通过")
    else:
        logger.warning("提示词格式可能有问题，重新构建")
        final_prompt = f"用户分析需求: {analysis_request.strip()}\n数据列信息: {column_info.strip()}"
    
    # 准备最终的响应信息
    response = "我将开始分析您的数据，生成可视化图表和洞察。请点击'开始分析'按钮继续。"
    
    # 始终返回analysis_ready=True，表示可以开始分析
    return response, True, final_prompt

def generate_column_confirmation_fallback(column_info: str) -> str:
    """生成列信息确认的后备响应
    
    Args:
        column_info: 提取的列信息
        
    Returns:
        生成的后备响应
    """
    # 将逗号分隔的列表转换为列表
    columns = [col.strip() for col in column_info.replace('，', ',').split(',') if col.strip()]
    
    # 如果没有有效的列名，使用默认响应
    if not columns:
        return "我理解您提供的信息。您是否可以明确指出CSV文件中包含哪些列名？这样我可以更好地帮助您进行分析。"
    
    # 构建响应
    response = f"我理解您的CSV文件包含以下列：\n\n"
    
    # 添加列名及其推测的数据类型
    for col in columns:
        data_type = "数值型" if any(keyword in col for keyword in ["销售", "利润", "成本", "金额", "价格", "数量"]) else "分类型"
        if "日期" in col or "时间" in col:
            data_type = "日期型"
        response += f"- {col}（可能是{data_type}数据）\n"
    
    response += "\n这样的理解正确吗？如果正确，我们可以开始分析。"
    
    return response

async def generate_python_code(prompt: str) -> Optional[str]:
    """基于自然语言提示生成Python数据分析代码
    
    Args:
        prompt: 用户的自然语言提示
        
    Returns:
        生成的Python代码或None（如果生成失败）
    """
    global ollama_client
    
    # 如果LLM客户端未初始化，尝试重新初始化
    if ollama_client is None:
        init_ollama_client()
        if ollama_client is None:
            logger.error("无法初始化LLM客户端，代码生成失败")
            return None
    
    try:
        # 解析提示词，区分分析需求和列信息
        user_requirement = prompt
        column_info = ""
        
        # 记录原始提示词，帮助调试
        logger.info(f"原始提示词: {prompt}")
        
        # 规范化冒号，确保一致性
        normalized_prompt = prompt.replace('：', ':')
        
        # 更强健的提取逻辑
        if "用户分析需求:" in normalized_prompt or "用户分析需求：" in normalized_prompt:
            try:
                # 使用正则表达式更可靠地提取部分
                import re
                
                # 匹配"用户分析需求:"后的内容，直到"数据列信息:"
                user_req_match = re.search(r'用户分析需求:?(.*?)(?=数据列信息:|$)', normalized_prompt, re.DOTALL)
                if user_req_match:
                    user_requirement = user_req_match.group(1).strip()
                    logger.info(f"成功提取用户需求: '{user_requirement}'")
                
                # 匹配"数据列信息:"后的所有内容
                col_info_match = re.search(r'数据列信息:?(.*?)$', normalized_prompt, re.DOTALL)
                if col_info_match:
                    column_info = col_info_match.group(1).strip()
                    logger.info(f"成功提取列信息: '{column_info}'")
            except Exception as e:
                logger.error(f"使用正则表达式提取信息失败: {str(e)}")
                # 回退到旧的提取方法
                parts = normalized_prompt.split("数据列信息:")
                if len(parts) > 1:
                    user_part = parts[0]
                    user_requirement = user_part.replace("用户分析需求:", "").strip()
                    column_info = parts[1].strip()
        
        # 确保用户需求不为空
        if not user_requirement or not user_requirement.strip():
            logger.warning("未能提取到用户需求，使用整个提示词")
            user_requirement = prompt
            
            # 尝试从提示词中分离出可能的列信息
            if "," in prompt or "，" in prompt:
                # 查找可能是列名的部分
                parts = prompt.replace("，", ",").split(",")
                if len(parts) >= 2 and all(len(p.strip()) < 10 for p in parts):
                    column_info = prompt
                    user_requirement = "分析数据"
                    logger.info(f"从提示词中提取列信息: {column_info}")
        
        # 基本代码生成提示
        system_prompt = """你是一个Python数据分析专家。请根据用户的具体需求生成精简的Python数据分析代码，专注于解决用户提出的问题。

生成代码需要遵循以下规则：
1. 仅使用pandas, numpy, matplotlib和seaborn进行数据分析和可视化（不要使用sklearn, scipy或其他额外库）
2. 处理位于'data/input.csv'的CSV文件
3. 结果保存到'data/result.json'
4. 图表保存到'data/charts/'目录（如果需要生成图表）
5. 不要使用中文字体设置，使用默认英文字体
6. 确保结果将numpy类型转换为Python原生类型
7. 确保所有代码使用4个空格的一致缩进
8. 代码应当简洁，直接针对用户的问题
9. 在result字典中包含一个'message'字段，用简单的语言总结分析结果
10. 直接使用用户指定的列名，不要尝试识别或替换列名
11. 如果用户没有明确指定列名，首先打印出所有列名供用户选择"""
        
        # 将系统提示与用户需求结合
        full_prompt = f"{system_prompt}\n\n用户需求: {user_requirement}"
        
        # 如果有列信息，添加到提示中
        if column_info:
            full_prompt += f"\n\n可用的数据列: {column_info}"
            
        full_prompt += "\n\n请生成直接解决这个具体需求的Python代码。"
        
        # 调用LLM生成代码
        logger.info("开始生成分析代码...")
        response = ollama_client.invoke(full_prompt)
        
        # 处理响应，提取代码块
        if response:
            # 尝试提取代码块（如果有的话）
            code = response
            if "```python" in response:
                code_blocks = response.split("```python")
                if len(code_blocks) > 1:
                    code = code_blocks[1].split("```")[0].strip()
            elif "```" in response:
                code_blocks = response.split("```")
                if len(code_blocks) > 1:
                    code = code_blocks[1].strip()
            
            # 确保代码缩进一致（转换为4空格缩进）
            code = normalize_python_indentation(code)
            
            # 检查代码中是否有不支持的库
            unsupported_libs = ['sklearn', 'scipy', 'tensorflow', 'keras', 'torch', 'xgboost', 'lightgbm']
            for lib in unsupported_libs:
                if f"import {lib}" in code or f"from {lib}" in code:
                    logger.warning(f"生成的代码包含不支持的库: {lib}")
                    # 移除相关导入
                    code = re.sub(r'(from\s+' + lib + r'.*?\n|import\s+' + lib + r'.*?\n)', '', code)
            
            # 固定的预定义代码片段 - 开始部分
            imports_and_setup = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import re
from pathlib import Path

# 设置matplotlib避免字体问题
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# 创建图表目录
charts_dir = 'data/charts'
os.makedirs(charts_dir, exist_ok=True)

# 辅助函数：转换NumPy类型为Python原生类型
def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    else:
        return obj
"""

            # 固定的文件读取部分，确保缩进一致
            file_reading = """
# 读取CSV文件
try:
    df = pd.read_csv('data/input.csv')
    print(f"成功读取CSV文件，共{len(df)}行，{len(df.columns)}列")
    print(f"列名: {', '.join(df.columns)}")
    
    # 识别列类型
    column_types = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            column_types[col] = 'numeric'
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            column_types[col] = 'datetime'
        else:
            column_types[col] = 'categorical'
            
    # 打印列类型信息供参考
    print("\n列类型信息:")
    for col, col_type in column_types.items():
        print(f"  {col}: {col_type}")
        
except Exception as e:
    print(f"读取CSV文件失败: {str(e)}")
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump({"error": f"读取CSV文件失败: {str(e)}"}, f, ensure_ascii=False)
    exit(1)
"""
            
            # 备用的简单分析代码块，只在LLM生成的代码有问题时使用
            fallback_analysis = f"""
# 用户分析需求: "{user_requirement}"
# 可用列信息: {column_info}

# 创建结果字典
result = {{
    "data_overview": {{
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns)
    }},
    "data_preview": df.head(5).to_dict(orient='records'),
    "message": "已完成基本数据分析"
}}

# 检查CSV文件中是否有用户提到的列
columns_to_analyze = []
if "{column_info}":
    requested_columns = [col.strip() for col in "{column_info}".split(',')]
    
    # 找出存在于CSV中的列
    for col in requested_columns:
        if col in df.columns:
            columns_to_analyze.append(col)
            if pd.api.types.is_numeric_dtype(df[col]):
                result[f"{{col}}分析"] = {{
                    "总和": float(df[col].sum()),
                    "平均值": float(df[col].mean()),
                    "最大值": float(df[col].max()),
                    "最小值": float(df[col].min())
                }}
                result["message"] += f"，{{col}}总计: {{float(df[col].sum()):.2f}}"

# 如果用户需求包含"地区"并且有一个地区列和一个数值列
if "地区" in "{user_requirement}" and any(col in df.columns for col in ["地区", "省份", "城市"]):
    # 找到地区列
    region_col = None
    for col_name in ["地区", "省份", "城市"]:
        if col_name in df.columns:
            region_col = col_name
            break
    
    if region_col and columns_to_analyze:
        # 找到第一个数值列
        value_col = None
        for col in columns_to_analyze:
            if pd.api.types.is_numeric_dtype(df[col]):
                value_col = col
                break
                
        if value_col:
            region_stats = df.groupby(region_col)[value_col].sum().sort_values(ascending=False)
            result[f"{{region_col}}{{value_col}}分析"] = region_stats.head(5).to_dict()
            
            if len(region_stats) > 0:
                top_region = region_stats.index[0]
                top_value = region_stats.iloc[0]
                result["message"] += f"，{{top_region}}的{{value_col}}最高，为{{float(top_value):.2f}}"
"""
            
            # 固定的结果保存部分
            save_result = """
# 保存结果到JSON文件
try:
    # 确保result变量存在
    if 'result' not in locals() and 'result' not in globals():
        result = {"error": "分析代码未定义result变量", "message": "分析过程中出现错误"}
    
    # 转换NumPy类型为Python原生类型
    result = convert_numpy_types(result)
    
    # 保存结果
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("分析完成，结果已保存到result.json")
except Exception as e:
    print(f"保存结果失败: {str(e)}")
    with open('data/result.json', 'w', encoding='utf-8') as f:
        json.dump({"error": f"保存结果失败: {str(e)}", "message": "分析过程中出现错误"}, f, ensure_ascii=False)
"""

            # 组合固定部分，确保缩进一致
            imports_and_setup = imports_and_setup.strip()
            file_reading = file_reading.strip()
            fallback_analysis = fallback_analysis.strip()
            save_result = save_result.strip()
            
            # 检查LLM生成的代码是否可用
            has_result_var = "result" in code
            has_minimal_code = len(code) > 50 and "df" in code
            has_no_unsupported_libs = not any(f"import {lib}" in code for lib in unsupported_libs)
            
            # 组合最终代码
            final_code = f"{imports_and_setup}\n\n{file_reading}\n\n"
            
            # 根据LLM代码质量决定是否使用LLM生成的代码或备用分析
            if has_result_var and has_minimal_code and has_no_unsupported_libs:
                # 添加LLM生成的核心分析代码
                logger.info("使用LLM生成的分析代码")
                final_code += f"{code}\n\n"
            else:
                logger.warning("LLM生成的代码不完整或包含不支持的库，使用备用分析代码")
                final_code += f"{fallback_analysis}\n\n"
            
            # 确保总是添加结果保存代码
            final_code += f"{save_result}\n"
            
            # 最终验证代码的有效性
            try:
                # 尝试编译代码，检查语法错误
                compile(final_code, '<string>', 'exec')
                logger.info("代码生成成功且语法有效")
                return final_code
            except Exception as compile_error:
                logger.error(f"生成的代码存在语法错误: {str(compile_error)}")
                logger.error(f"错误位置: {traceback.format_exc()}")
                # 当出现语法错误时，返回None，将使用沙盒服务的默认分析脚本
                logger.warning("检测到语法错误，将使用沙盒服务的默认分析脚本")
                return None
        else:
            logger.error("生成代码失败：LLM返回空响应")
            return None
    except Exception as e:
        logger.error(f"生成代码异常: {str(e)}")
        traceback.print_exc()
        return None 

def normalize_python_indentation(code: str, spaces_per_indent: int = 4) -> str:
    """标准化Python代码的缩进，确保使用一致的空格缩进
    
    Args:
        code: Python代码字符串
        spaces_per_indent: 每级缩进的空格数
        
    Returns:
        标准化缩进后的代码
    """
    if not code:
        return ""
        
    # 将制表符替换为空格
    code = code.replace('\t', ' ' * spaces_per_indent)
    
    lines = code.split('\n')
    normalized_lines = []
    
    # 处理每一行
    for line in lines:
        # 跳过空行
        if not line.strip():
            normalized_lines.append('')
            continue
            
        # 计算前导空格数
        leading_spaces = len(line) - len(line.lstrip(' '))
        # 计算应该的缩进级别
        indent_level = leading_spaces // spaces_per_indent
        # 标准化缩进
        normalized_line = ' ' * (indent_level * spaces_per_indent) + line.lstrip(' ')
        normalized_lines.append(normalized_line)
    
    # 组合成最终代码
    return '\n'.join(normalized_lines) 
import logging
from typing import Dict, Any, List, Optional, Union
import re
import json

# 将相对导入改为绝对导入
from backend.services.agent_service import ApprovalAgent
# 修改为使用绝对导入
try:
    from backend.services.langgraph_agent import LangGraphAgent
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logging.warning("LangGraph未安装或导入失败，将仅使用关键词匹配方式")

# 设置日志
logger = logging.getLogger(__name__)

class SmartAgent:
    """智能代理服务，整合关键词匹配和LangGraph智能代理"""
    
    def __init__(self):
        """初始化智能代理服务"""
        logger.info("初始化智能代理服务")
        # 输出更详细的初始化信息
        logger.info("智能代理服务初始化 - 使用关键词匹配优先策略")
        
        # 初始化审批代理
        self.approval_agent = ApprovalAgent()
        
        # 尝试初始化LangGraph代理
        self.langgraph_agent = None
        if LANGGRAPH_AVAILABLE:
            try:
                self.langgraph_agent = LangGraphAgent()
                logger.info("成功初始化LangGraph代理")
            except Exception as e:
                logger.error(f"初始化LangGraph代理失败: {e}")
        
        # 初始化关键词映射
        self._init_keyword_mappings()
    
    def _init_keyword_mappings(self):
        """初始化关键词映射"""
        # 邮件相关关键词(添加"写"关键词，并包含权重信息)
        self.email_keywords = {
            "邮件": 2.0,  # 核心关键词，赋予高权重
            "写": 1.5,    # 添加"写"关键词，中高权重
            "发送": 1.0,
            "写信": 1.5,
            "收件人": 0.8,
            "主题": 0.8,
            "回复": 0.8,
            "转发": 0.8,
            "抄送": 0.5,
            "密送": 0.5,
            "附件": 0.5,
            "邮箱": 0.8
        }
        
        # 审批相关关键词(也调整为字典格式，包含权重)
        self.approval_keywords = {
            "审批": 2.0,  # 核心关键词，赋予高权重
            "申请": 1.5,
            "批准": 1.0,
            "同意": 0.8,
            "拒绝": 0.8,
            "流程": 0.8,
            "请假": 1.5,
            "报销": 1.5,
            "采购": 1.5,
            "用章": 1.5,
            "审核": 0.8
        }
        
        # 文档相关关键词(同样调整为字典格式)
        self.document_keywords = {
            "文档": 2.0,  # 核心关键词，赋予高权重
            "文件": 1.5,
            "附件": 1.0,
            "上传": 1.0,
            "下载": 1.0,
            "共享": 0.8,
            "编辑": 0.8,
            "修改": 0.8,
            "删除": 0.5,
            "预览": 0.5,
            "打印": 0.5
        }
    
    def _keyword_matching(self, user_input: str) -> Dict[str, Any]:
        """使用关键词匹配处理用户输入"""
        user_input = user_input.lower()
        
        # 初始化结果
        result = {
            "success": False,
            "confidence": 0.0,
            "action": "unknown",
            "form_data": {},
            "message": "未能识别意图"
        }
        
        # 使用加权匹配计算置信度
        email_confidence = self._calculate_weighted_confidence(user_input, self.email_keywords)
        approval_confidence = self._calculate_weighted_confidence(user_input, self.approval_keywords)
        document_confidence = self._calculate_weighted_confidence(user_input, self.document_keywords)
        
        # 记录调试信息
        logger.info(f"邮件置信度: {email_confidence}, 审批置信度: {approval_confidence}, 文档置信度: {document_confidence}")
        
        # 确定最高置信度的意图
        confidences = {
            "email": email_confidence,
            "approval": approval_confidence,
            "document": document_confidence
        }
        
        max_intent = max(confidences, key=confidences.get)
        max_confidence = confidences[max_intent]
        
        # 使用更简单的判断逻辑 - 只要有任何置信度，就认为匹配成功
        # 这样可以避免总是返回0的问题
        if max_confidence > 0:  
            result["success"] = True
            result["confidence"] = max_confidence
            
            # 根据最高置信度确定动作
            if max_intent == "email":
                result["action"] = "compose_email"
                result["message"] = "准备撰写邮件"
                
                # 提取可能的邮件信息
                form_data = self._extract_email_info(user_input)
                result["form_data"] = form_data
                
            elif max_intent == "approval":
                result["action"] = "create_approval"
                result["message"] = "准备创建审批流程"
                
                # 使用审批代理进一步处理
                process_type = None
                for key in self.approval_agent.process_types.keys():
                    if key in user_input:
                        process_type = key
                        break
                
                if process_type:
                    # 提取表单数据
                    form_data = {
                        "process_type": process_type
                    }
                    
                    # 提取天数/金额信息
                    days_match = re.search(r'(\d+)\s*[天日]', user_input)
                    amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:元|万元|¥|RMB|CNY)', user_input)
                    
                    if days_match:
                        form_data["days"] = int(days_match.group(1))
                    
                    if amount_match:
                        form_data["amount"] = float(amount_match.group(1))
                    
                    result["form_data"] = form_data
            
            elif max_intent == "document":
                result["action"] = "manage_document"
                result["message"] = "准备管理文档"
        
        return result
        
    def process_user_input(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理用户输入，智能识别意图并执行相应操作"""
        if context is None:
            context = {}
            
        # 确保context中包含references键
        if "references" not in context:
            context["references"] = []
        
        # 记录用户输入
        logger.info(f"处理用户输入: {user_input}")
        
        # 步骤1: 直接匹配特定指令 - 无需计算置信度
        # -------------------------
        lower_input = user_input.lower()
        
        # 邮件指令直接匹配
        # 更宽松的条件以确保匹配成功
        if ((any(word in lower_input for word in ["写", "发", "创建", "撰写", "编写"]) and 
             any(word in lower_input for word in ["邮件", "信", "邮箱", "电子邮件"])) or
            "发邮件" in lower_input or "写邮件" in lower_input or "写信" in lower_input):
            logger.info("直接匹配到邮件指令 (使用模糊匹配)")
            email_info = self._extract_email_info(lower_input)
            logger.info(f"提取的邮件信息: {email_info}")
            
            # 如果是"给导员写邮件请假"这种复合场景，尝试提取请假信息
            if "请假" in lower_input:
                days_match = re.search(r'(\d+)\s*[天日]', lower_input)
                if days_match:
                    days = int(days_match.group(1))
                    if "content" not in email_info or not email_info["content"]:
                        email_info["content"] = f"尊敬的导员：\n\n我因个人原因需要请假{days}天，望批准。\n\n此致\n敬礼"
                    if "subject" not in email_info or not email_info["subject"]:
                        email_info["subject"] = f"请假申请 - {days}天"
            
            return {
                "success": True,
                "confidence": 1.0,
                "action": "compose_email",
                "message": "准备撰写邮件",
                "form_data": email_info
            }
            
        # 审批指令直接匹配
        # 更宽松的匹配条件
        if (any(x in lower_input for x in ["审批", "申请", "请假", "报销", "采购", "休假", "用章"]) or
            (("创建" in lower_input or "发起" in lower_input or "提交" in lower_input) and 
             ("审批" in lower_input or "流程" in lower_input or "申请" in lower_input))):
            logger.info("直接匹配到审批指令 (使用模糊匹配)")
            process_type = None
            for key in self.approval_agent.process_types.keys():
                if key in lower_input:
                    process_type = key
                    break
                    
            form_data = {"process_type": process_type or "请假"}  # 默认请假类型
            
            # 提取天数/金额信息
            days_match = re.search(r'(\d+)\s*[天日]', lower_input)
            amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:元|万元|¥|RMB|CNY)', lower_input)
            
            if days_match:
                form_data["days"] = int(days_match.group(1))
                # 自动添加请假理由
                form_data["reason"] = "个人原因"
                if "病" in lower_input:
                    form_data["reason"] = "生病"
                elif "事" in lower_input:
                    form_data["reason"] = "个人事务"
            
            if amount_match:
                form_data["amount"] = float(amount_match.group(1))
            
            logger.info(f"提取的审批信息: {form_data}")    
            return {
                "success": True,
                "confidence": 1.0,
                "action": "create_approval",
                "message": "准备创建审批流程",
                "form_data": form_data
            }
            
        # 创建用户指令直接匹配
        # 更宽松的匹配条件
        if (("创建" in lower_input or "添加" in lower_input or "新增" in lower_input or "新建" in lower_input) and 
            ("用户" in lower_input or "账号" in lower_input or "账户" in lower_input)):
            logger.info("直接匹配到创建用户指令 (使用模糊匹配)")
            # 提取用户名、角色等信息
            name_match = re.search(r'(?:用户名|姓名)[是为：:]*\s*[""「」《》\s]*([^，。,\.;；""「」《》]*)', lower_input)
            role_match = re.search(r'(?:角色|权限)[是为：:]*\s*[""「」《》\s]*([^，。,\.;；""「」《》]*)', lower_input)
            
            form_data = {}
            if name_match:
                form_data["username"] = name_match.group(1).strip()
            if role_match:
                form_data["role"] = role_match.group(1).strip()
                
            # 检查是否包含"普通用户"关键词
            if "普通" in lower_input and "用户" in lower_input:
                form_data["role"] = "普通用户"
                logger.info("检测到'普通用户'关键词，设置角色为普通用户")
            
            logger.info(f"提取的用户信息: {form_data}")    
            return {
                "success": True,
                "confidence": 1.0,
                "action": "create_user",
                "message": "准备创建用户",
                "form_data": form_data
            }
        
        # 工作流创建指令直接匹配
        # 宽松的匹配条件
        if (("创建" in lower_input or "设计" in lower_input or "新建" in lower_input or "制作" in lower_input) and 
            ("工作流" in lower_input or "流程" in lower_input or "审批流程" in lower_input)):
            logger.info("直接匹配到工作流创建指令 (使用模糊匹配)")
            
            # 提取工作流名称
            name = "新建工作流"
            name_match = re.search(r'(?:创建|设计|新建|制作)([^，。,\.;；]*?)(?:工作流|流程|审批流程)', lower_input)
            if name_match and name_match.group(1).strip():
                name = name_match.group(1).strip()
                if len(name) > 15:  # 如果名称太长，截断
                    name = name[:15]
                # 确保名称以"流程"结尾
                if not (name.endswith('流程') or name.endswith('审批')):
                    name = name + "流程"
                logger.info(f"提取到工作流名称: {name}")
            
            form_data = {
                "name": name,
                "description": "根据AI助手提示自动创建的工作流",
                "prompt": lower_input
            }
            
            logger.info(f"提取的工作流信息: {form_data}")    
            return {
                "success": True,
                "confidence": 1.0,
                "action": "create_workflow",
                "message": "准备创建工作流",
                "form_data": form_data
            }
        
        # 步骤2: 进行关键词匹配 - 只要成功就不用智能体
        # -------------------------
        logger.info("开始进行关键词匹配")
        keyword_result = self._keyword_matching(user_input)
        
        # 记录关键词匹配结果
        logger.info(f"关键词匹配结果: action={keyword_result.get('action', 'unknown')}, confidence={keyword_result.get('confidence', 0)}")
        
        # 只要关键词匹配成功就直接返回，不再考虑置信度
        if keyword_result["success"]:
            logger.info("关键词匹配成功，直接使用结果，不调用智能体")
            return keyword_result
        
        # 步骤3: 关键词匹配失败，才尝试使用LangGraph智能体
        # -------------------------
        if self.langgraph_agent:
            logger.info("关键词匹配失败，尝试使用LangGraph智能体")
            try:
                # 调用LangGraph代理处理
                langgraph_result = self.langgraph_agent.process(user_input, context)
                logger.info(f"LangGraph处理结果: {langgraph_result}")
                
                # 如果LangGraph处理成功，返回结果
                if langgraph_result.get("success", False):
                    return langgraph_result
            except Exception as e:
                logger.error(f"LangGraph处理失败: {e}")
        
        # 步骤4: 完全无法识别
        # -------------------------
        logger.info("无法识别用户意图")
        return {
            "success": False,
            "confidence": 0.0,
            "action": "unknown",
            "message": "无法理解您的意图，请尝试更明确的表述",
            "form_data": {}
        }
        
    def _extract_email_info(self, text: str) -> Dict[str, str]:
        """从文本中提取邮件相关信息"""
        form_data = {}
        
        # 提取收件人、主题、内容
        recipient_match = re.search(r'(?:发送给|收件人|发给|写给)\s*[""「」《》\s]*([^，。,\.;；""「」《》]*)', text)
        subject_match = re.search(r'(?:主题|标题|题目)[是为：:]*\s*[""「」《》\s]*([^，。,\.;；""「」《》]*)', text)
        content_match = re.search(r'(?:内容|正文|内含)[是为：:]*\s*[""「」《》\s]*([^""「」《》]*)', text)
        
        if recipient_match:
            form_data["recipient"] = recipient_match.group(1).strip()
        if subject_match:
            form_data["subject"] = subject_match.group(1).strip()
        if content_match:
            form_data["content"] = content_match.group(1).strip()
            
        return form_data
    
    def _calculate_weighted_confidence(self, user_input: str, keywords_dict: Dict[str, float]) -> float:
        """使用加权匹配计算置信度
        
        Args:
            user_input: 用户输入文本
            keywords_dict: 关键词及其权重字典
            
        Returns:
            float: 加权置信度分数
        """
        # 用于调试
        matched_keywords = []
        matched_weights = []
        
        total_weight = sum(keywords_dict.values())
        matched_weight = 0
        
        # 逐个检查关键词
        for keyword, weight in keywords_dict.items():
            if keyword in user_input:
                matched_weight += weight
                matched_keywords.append(keyword)
                matched_weights.append(weight)
        
        # 输出调试信息
        logger.info(f"匹配到的关键词: {matched_keywords}")
        logger.info(f"关键词权重: {matched_weights}")
        logger.info(f"匹配权重总和: {matched_weight}/{total_weight}")
        
        # 短输入特殊处理，降低置信度要求
        input_length_factor = 1.0
        if len(user_input) < 10:
            input_length_factor = 1.2  # 短输入提升20%置信度
            
        # 修复的置信度计算 - 使用更简单直接的计算方式
        # 只要匹配到任何关键词，就给一个基础置信度
        if matched_weight > 0:
            # 基础置信度0.1，每匹配一个权重1.0的关键词增加0.2的置信度
            base_confidence = 0.1 + (matched_weight / 5)
            logger.info(f"基础置信度: {base_confidence}")
        else:
            base_confidence = 0.0
            
        # 应用输入长度因子
        final_confidence = min(1.0, base_confidence * input_length_factor)
        logger.info(f"最终置信度: {final_confidence}")
        
        return final_confidence
    
    def get_form_suggestions(self, form_id: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """根据表单ID和现有数据，提供智能填充建议"""
        logger.info(f"为表单 {form_id} 提供智能填充建议")
        
        # 初始化结果
        suggestions = {
            "fields": {},
            "workflows": [],
            "approvers": []
        }
        
        # 根据表单ID区分不同类型的表单
        if form_id.startswith("approval_"):
            # 审批表单处理
            if "process_type" in form_data:
                # 获取审批人建议
                approvers_result = self.approval_agent.get_suitable_approvers(
                    form_data["process_type"], 
                    form_data.get("department_id"), 
                    form_data
                )
                
                suggestions["approvers"] = approvers_result["approvers"]
                
                # 如果有文本内容，推荐工作流
                if "content" in form_data and form_data["content"]:
                    workflow = self.approval_agent.recommend_workflow(form_data["content"])
                    suggestions["workflows"].append(workflow)
                
                # 预测审批时间
                emergency_level = 0
                if "title" in form_data and "content" in form_data:
                    combined_text = f"{form_data['title']} {form_data['content']}"
                    emergency_level = self.approval_agent._analyze_emergency_level(combined_text)
                
                approver_count = len(suggestions["approvers"])
                estimated_time = self.approval_agent.predict_approval_time(
                    form_data["process_type"],
                    emergency_level,
                    approver_count
                )
                
                suggestions["fields"]["estimated_time"] = estimated_time
        
        elif form_id.startswith("email_"):
            # 邮件表单处理
            if self.langgraph_agent and "subject" in form_data and form_data["subject"]:
                # 使用LangGraph代理生成邮件内容建议
                try:
                    context = {"form_id": form_id, "form_data": form_data}
                    input_text = f"根据主题'{form_data['subject']}'生成一封专业邮件"
                    
                    result = self.langgraph_agent.process(input_text, context)
                    
                    if result.get("success", False) and "form_data" in result:
                        if "content" in result["form_data"]:
                            suggestions["fields"]["content"] = result["form_data"]["content"]
                except Exception as e:
                    logger.error(f"生成邮件内容建议失败: {e}")
        
        return suggestions 
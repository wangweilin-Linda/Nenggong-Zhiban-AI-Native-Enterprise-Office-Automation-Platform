import os
import json
import re
from typing import Dict, Any, List, Optional, Union, Tuple
import requests
from sqlalchemy.orm import Session
import random
from datetime import datetime, timedelta
import subprocess
import logging

# 设置日志
logger = logging.getLogger(__name__)

class ApprovalAgent:
    """审批代理服务，用于处理复杂的审批逻辑和智能建议"""
    
    def __init__(self):
        """初始化代理服务"""
        logger.info("初始化审批代理服务")
        # 尝试加载本地模型
        self.llm_available = self._check_llm_availability()
        # 初始化关键词字典，用于表单分析
        self._init_keywords_dict()
        
    def _check_llm_availability(self) -> bool:
        """检查LLM服务是否可用"""
        try:
            # 尝试请求本地Ollama服务
            response = requests.get("http://localhost:11434/api/tags", timeout=3)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LLM服务不可用: {str(e)}")
            return False
    
    def _init_keywords_dict(self):
        """初始化关键词字典用于内容分析"""
        self.emergency_keywords = ["紧急", "急需", "立即", "尽快", "加急", "特急", "马上"]
        self.risk_keywords = {
            "高": ["违规", "违反", "超出预算", "未经授权", "异常", "风险", "欺诈"],
            "中": ["延期", "推迟", "更改", "修改", "调整", "变更"],
            "低": ["常规", "例行", "标准", "正常"]
        }
        self.process_types = {
            "请假": ["休假", "病假", "年假", "调休", "事假", "产假"],
            "报销": ["报销", "费用", "支出", "付款", "采购", "消费"],
            "采购": ["采购", "购买", "订购", "购置", "采买"],
            "用章": ["用章", "盖章", "印章", "公章", "合同章", "法人章"]
        }
        
    def analyze_form_data(self, form_data: Dict) -> Dict:
        """分析表单数据，提供更智能的审批建议"""
        if not form_data:
            return {
                "suggestion": "建议人工审核",
                "reason": "未能获取到完整表单数据",
                "risk_level": "中"
            }
            
        # 提取关键字段
        title = form_data.get("title", "")
        content = form_data.get("content", "")
        amount = form_data.get("amount", 0)
        
        combined_text = f"{title} {content}"
        
        # 分析紧急程度
        emergency_level = self._analyze_emergency_level(combined_text)
        
        # 分析风险等级
        risk_level = self._analyze_risk_level(combined_text)
        
        # 分析金额风险(如果存在)
        if amount and isinstance(amount, (int, float)) and amount > 10000:
            risk_level = "高" if amount > 50000 else "中"
            
        # 根据分析结果生成建议
        suggestion, reason = self._generate_suggestion(
            risk_level, emergency_level, combined_text, amount
        )
        
        return {
            "suggestion": suggestion,
            "reason": reason,
            "risk_level": risk_level,
            "emergency_level": emergency_level
        }
        
    def _analyze_emergency_level(self, text: str) -> int:
        """分析文本的紧急程度"""
        if not text:
            return 0
            
        text = text.lower()
        # 计算紧急关键词出现次数
        emergency_count = sum(1 for keyword in self.emergency_keywords if keyword in text)
        
        # 根据紧急关键词数量判断紧急程度
        if emergency_count >= 3:
            return 2  # 非常紧急
        elif emergency_count >= 1:
            return 1  # 紧急
        else:
            return 0  # 普通
    
    def _analyze_risk_level(self, text: str) -> str:
        """分析文本的风险等级"""
        if not text:
            return "低"
            
        text = text.lower()
        
        # 检查高风险关键词
        for keyword in self.risk_keywords["高"]:
            if keyword in text:
                return "高"
                
        # 检查中风险关键词
        for keyword in self.risk_keywords["中"]:
            if keyword in text:
                return "中"
                
        # 默认为低风险
        return "低"
        
    def _generate_suggestion(self, risk_level: str, emergency_level: int, 
                           text: str, amount: Union[int, float, None]) -> Tuple[str, str]:
        """根据风险等级和紧急程度生成建议"""
        # 高风险情况
        if risk_level == "高":
            return "建议人工审核", "检测到高风险因素，需要人工仔细审核"
            
        # 中风险 + 高紧急度
        if risk_level == "中" and emergency_level == 2:
            return "优先审核", "中等风险但非常紧急，建议优先处理并仔细审核"
            
        # 低风险 + 高紧急度
        if risk_level == "低" and emergency_level == 2:
            return "建议通过", "低风险且紧急，可快速审批通过"
            
        # 低风险 + 低紧急度
        if risk_level == "低" and emergency_level < 2:
            return "建议通过", "常规低风险申请，符合标准流程"
            
        # 默认情况
        return "建议审核", "需要根据具体情况进行评估"
    
    def get_suitable_approvers(self, process_type: str, department_id: Optional[int] = None,
                              form_data: Optional[Dict] = None) -> Dict:
        """获取更智能的审批人建议"""
        approvers = []
        reason = ""
        
        # 确定流程类型
        detected_type = self._detect_process_type(process_type, form_data)
        
        # 根据不同流程类型和表单数据推荐审批人
        if detected_type == "请假":
            # 请假审批流程通常需要直接主管
            approvers = [1]  # 假设1是部门主管ID
            reason = "请假申请应由直接主管审批"
            
            # 检查请假天数(如果存在)
            days = form_data.get("days", 0) if form_data else 0
            if isinstance(days, (int, float)) and days > 3:
                approvers = [1, 2]  # 添加更高级别的审批人
                reason = f"请假{days}天超过3天，需要部门主管和人事主管共同审批"
                
        elif detected_type == "报销":
            # 报销审批流程需要财务审批
            approvers = [3]  # 假设3是财务主管ID
            reason = "报销申请应由财务部门审批"
            
            # 检查报销金额
            amount = form_data.get("amount", 0) if form_data else 0
            if isinstance(amount, (int, float)):
                if amount > 5000:
                    approvers = [3, 4]  # 添加财务总监
                    reason = f"报销金额{amount}元超过5000元，需要财务主管和财务总监共同审批"
                    
        elif detected_type == "采购":
            # 采购流程
            approvers = [1, 3]  # 部门主管和财务
            reason = "采购申请需要部门主管和财务共同审批"
            
        elif detected_type == "用章":
            # 用章申请
            approvers = [5]  # 假设5是行政主管ID
            reason = "用章申请由行政部门审批"
            
        else:
            # 默认流程
            approvers = [1, 2]
            reason = "未明确流程类型，建议部门主管和人事主管共同审批"
            
        # 如果有部门ID，确保该部门主管在审批人中
        if department_id and department_id > 0:
            dept_manager_id = self._get_department_manager_id(department_id)
            if dept_manager_id and dept_manager_id not in approvers:
                approvers.insert(0, dept_manager_id)
                reason = f"{reason}，且需要部门主管审批"
            
        return {
            "approvers": approvers,
            "reason": reason,
            "process_type": detected_type
        }
        
    def _detect_process_type(self, process_type: str, form_data: Optional[Dict]) -> str:
        """检测实际的流程类型"""
        if process_type and isinstance(process_type, str):
            process_type = process_type.strip().lower()
            for key, keywords in self.process_types.items():
                if process_type in keywords or any(kw in process_type for kw in keywords):
                    return key
        
        # 从表单数据中推断类型
        if form_data:
            text = ""
            for key, value in form_data.items():
                if isinstance(value, str):
                    text += f" {value}"
            
            for key, keywords in self.process_types.items():
                if any(kw in text.lower() for kw in keywords):
                    return key
                    
        # 默认返回通用类型
        return "通用"
    
    def _get_department_manager_id(self, department_id: int) -> Optional[int]:
        """获取部门主管ID"""
        # 实际应用中应从数据库查询
        # 这里简化为映射关系
        dept_manager_map = {
            1: 10,  # 部门1的主管是用户10
            2: 11,  # 部门2的主管是用户11
            3: 12   # 部门3的主管是用户12
        }
        return dept_manager_map.get(department_id)
    
    def predict_approval_time(self, process_type: str, emergency_level: int = 0,
                             approver_count: int = 1) -> str:
        """更智能地预测审批完成时间"""
        base_time = 0
        
        # 根据流程类型确定基础时间(小时)
        if process_type == "请假":
            base_time = 4
        elif process_type == "报销":
            base_time = 8
        elif process_type == "采购":
            base_time = 12
        elif process_type == "用章":
            base_time = 2
        else:
            base_time = 6
            
        # 根据紧急程度调整
        if emergency_level == 2:  # 非常紧急
            base_time = max(1, base_time // 4)  # 最少1小时
        elif emergency_level == 1:  # 紧急
            base_time = max(2, base_time // 2)  # 最少2小时
            
        # 根据审批人数量调整
        if approver_count > 1:
            base_time = base_time * (1 + (approver_count - 1) * 0.5)  # 每增加一个审批人，时间增加50%
            
        # 获取当前工作时间
        now = datetime.now()
        is_workday = now.weekday() < 5  # 0-4是工作日
        is_work_hour = 9 <= now.hour < 18  # 工作时间为9点到18点
        
        # 非工作时间调整
        if not is_workday:
            base_time = base_time + 24  # 周末至少多等一天
        elif not is_work_hour:
            if now.hour < 9:  # 早上9点前
                base_time = base_time + (9 - now.hour)
            else:  # 晚上6点后
                base_time = base_time + (24 - now.hour + 9)
                
        # 格式化输出
        if base_time < 1:
            return "1小时内"
        elif base_time < 24:
            return f"{round(base_time)}小时内"
        else:
            days = base_time / 24
            return f"{round(days)}天内"

    def recommend_workflow(self, text: str) -> Dict[str, Any]:
        """根据文本内容智能推荐工作流程"""
        # 提取关键信息
        process_type = self._detect_process_type_from_text(text)
        emergency_level = self._analyze_emergency_level(text)
        
        # 构建工作流配置
        workflow = {
            "name": f"{process_type}审批流程",
            "description": f"根据内容自动推荐的{process_type}审批流程",
            "type": process_type.lower(),
            "nodes": [
                {
                    "id": "start",
                    "name": "开始",
                    "type": "start"
                }
            ],
            "edges": []
        }
        
        # 根据不同流程类型构建不同的审批节点
        last_node_id = "start"
        
        # 部门主管审批节点（通用）
        workflow["nodes"].append({
            "id": "department_manager",
            "name": "部门主管审批",
            "type": "approval",
            "roles": ["department_manager"]
        })
        workflow["edges"].append({
            "from": last_node_id,
            "to": "department_manager"
        })
        last_node_id = "department_manager"
        
        # 根据流程类型添加特定节点
        if process_type == "请假":
            # 判断是否需要高级审批
            days_match = re.search(r'(\d+)\s*[天日]', text)
            days = int(days_match.group(1)) if days_match else 0
            
            if days > 3:
                # 添加人事审批节点
                workflow["nodes"].append({
                    "id": "hr_approval",
                    "name": "人事审批",
                    "type": "approval",
                    "roles": ["hr_manager"]
                })
                workflow["edges"].append({
                    "from": last_node_id,
                    "to": "hr_approval"
                })
                last_node_id = "hr_approval"
                
            if days > 7:
                # 添加总经理审批节点
                workflow["nodes"].append({
                    "id": "ceo_approval",
                    "name": "总经理审批",
                    "type": "approval",
                    "roles": ["ceo"]
                })
                workflow["edges"].append({
                    "from": last_node_id,
                    "to": "ceo_approval"
                })
                last_node_id = "ceo_approval"
                
        elif process_type == "报销" or process_type == "采购":
            # 检查是否包含金额信息
            amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:元|万元|¥|RMB|CNY)', text)
            amount = float(amount_match.group(1)) if amount_match else 0
            
            # 财务审批节点
            workflow["nodes"].append({
                "id": "finance_approval",
                "name": "财务审批",
                "type": "approval",
                "roles": ["finance_manager"]
            })
            workflow["edges"].append({
                "from": last_node_id,
                "to": "finance_approval"
            })
            last_node_id = "finance_approval"
            
            if amount > 10000:
                # 添加财务总监审批节点
                workflow["nodes"].append({
                    "id": "finance_director",
                    "name": "财务总监审批",
                    "type": "approval",
                    "roles": ["finance_director"]
                })
                workflow["edges"].append({
                    "from": last_node_id,
                    "to": "finance_director"
                })
                last_node_id = "finance_director"
                
            if amount > 50000:
                # 添加总经理审批节点
                workflow["nodes"].append({
                    "id": "ceo_approval",
                    "name": "总经理审批",
                    "type": "approval",
                    "roles": ["ceo"]
                })
                workflow["edges"].append({
                    "from": last_node_id,
                    "to": "ceo_approval"
                })
                last_node_id = "ceo_approval"
                
        elif process_type == "用章":
            # 添加法务审批节点
            workflow["nodes"].append({
                "id": "legal_approval",
                "name": "法务审批",
                "type": "approval",
                "roles": ["legal_manager"]
            })
            workflow["edges"].append({
                "from": last_node_id,
                "to": "legal_approval"
            })
            last_node_id = "legal_approval"
            
            # 如果包含合同关键词，添加合同专员审批
            if "合同" in text:
                workflow["nodes"].append({
                    "id": "contract_approval",
                    "name": "合同专员审批",
                    "type": "approval",
                    "roles": ["contract_specialist"]
                })
                workflow["edges"].append({
                    "from": last_node_id,
                    "to": "contract_approval"
                })
                last_node_id = "contract_approval"
        
        # 结束节点
        workflow["nodes"].append({
            "id": "end",
            "name": "结束",
            "type": "end"
        })
        workflow["edges"].append({
            "from": last_node_id,
            "to": "end"
        })
        
        # 添加紧急标签
        if emergency_level > 0:
            workflow["urgent"] = True
            workflow["description"] = f"紧急：{workflow['description']}"
            
        return workflow
        
    def _detect_process_type_from_text(self, text: str) -> str:
        """从文本中检测流程类型"""
        text = text.lower()
        
        for process_type, keywords in self.process_types.items():
            if any(keyword in text for keyword in keywords):
                return process_type
                
        return "通用"
        
    def analyze_approval_context(self, instance_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析审批上下文，提供智能建议"""
        result = {
            "analysis": "",
            "suggestions": [],
            "similar_cases": []
        }
        
        try:
            # 提取关键信息
            form_data = instance_data.get("form_data", {})
            status = instance_data.get("status", "")
            process_type = instance_data.get("process_type", "")
            
            if not form_data:
                result["analysis"] = "未提供足够的表单数据进行分析"
                return result
                
            # 获取风险分析
            risk_analysis = self.analyze_form_data(form_data)
            
            # 根据流程类型和风险等级提供建议
            suggestions = []
            
            if risk_analysis["risk_level"] == "高":
                suggestions.append("该申请存在较高风险，建议仔细审核相关证明材料")
                
            if risk_analysis["risk_level"] == "中":
                suggestions.append("请核实申请中的关键信息，确保符合公司规定")
                
            if process_type == "请假" and form_data.get("days", 0) > 3:
                suggestions.append("请确认请假人已妥善安排工作交接")
                
            if process_type == "报销" and form_data.get("amount", 0) > 1000:
                suggestions.append("请核对发票信息是否完整，金额是否符合预算")
                
            # 生成分析结果
            result["analysis"] = f"该{process_type}申请的风险等级为{risk_analysis['risk_level']}，{risk_analysis['reason']}"
            result["suggestions"] = suggestions
            
            # 添加模拟的相似案例
            result["similar_cases"] = self._get_similar_cases(process_type, form_data)
            
            return result
            
        except Exception as e:
            logger.error(f"分析审批上下文失败: {str(e)}")
            result["analysis"] = "分析过程中发生错误，请手动审核"
            return result
            
    def _get_similar_cases(self, process_type: str, form_data: Dict) -> List[Dict]:
        """获取相似案例"""
        # 实际应用中应查询数据库
        # 这里返回模拟数据
        cases = []
        
        if process_type == "请假":
            cases = [
                {"id": 101, "title": "张三请假3天", "status": "approved", "similarity": 0.85},
                {"id": 102, "title": "李四产假申请", "status": "approved", "similarity": 0.72}
            ]
        elif process_type == "报销":
            cases = [
                {"id": 201, "title": "王五差旅费报销", "status": "approved", "similarity": 0.78},
                {"id": 202, "title": "部门团建报销", "status": "rejected", "similarity": 0.65, 
                 "reject_reason": "超出预算限制"}
            ]
            
        return cases[:2]  # 只返回最相似的两个案例
        
    def generate_notification(self, action: str, comment: str = "") -> str:
        """生成通知消息"""
        templates = {
            "approve": [
                "您的申请已审批通过，{comment}",
                "已同意您的申请。{comment}",
                "您的申请已获批准，{comment}"
            ],
            "reject": [
                "很遗憾，您的申请被驳回。原因：{comment}",
                "您的申请未获通过。{comment}",
                "申请被拒绝，原因是：{comment}"
            ],
            "return": [
                "您的申请已被退回，需要补充以下信息：{comment}",
                "申请已退回，请完善：{comment}",
                "需要您进一步补充材料：{comment}"
            ]
        }
        
        action = action.lower()
        if action not in templates:
            return f"您的申请状态已更新：{action}。{comment}"
            
        # 随机选择一个模板
        template = random.choice(templates[action])
        
        # 如果没有评论，使用默认评论
        if not comment:
            if action == "approve":
                comment = "祝您工作顺利"
            elif action == "reject":
                comment = "不符合审批要求"
            elif action == "return":
                comment = "请补充必要的证明材料"
                
        # 填充模板
        return template.format(comment=comment)
from sqlalchemy.orm import Session
from models.document.approval import ApprovalInstance, ApprovalNode, ApprovalProcess, ApprovalHistory
from utils.workflow_parser import parse_workflow_config
from .state_machine import StateContext, PendingState
from .agent_service import ApprovalAgent
from typing import Optional, Dict, List, Any
from .rule_engine import RuleEngine
from database.session import get_db, SessionLocal
from datetime import datetime, timedelta
import os
import json
import traceback
from models.user import User
from models.position import Position
from models.department import Department
from sqlalchemy import text

# 修改初始化方式
AGENT = ApprovalAgent()  # 直接实例化，无需API key

# 在文件顶部添加
rule_engine = RuleEngine()

class ApprovalService:
    def __init__(self, db=None):
        """初始化服务"""
        self.rule_engine = RuleEngine()
        self.agent = AGENT
        self.db = db
        self.workflow_config = parse_workflow_config()
        print(f"审批服务初始化完成，加载了流程配置: {len(self.workflow_config.get('nodes', [])) if 'nodes' in self.workflow_config else len(self.workflow_config.get('states', {}))} 个节点/状态")
    
    def get_workflow_config(self, process_id=None):
        """获取工作流配置，可以根据流程ID获取特定配置"""
        try:
            # 如果提供了流程ID，尝试从数据库加载特定流程的配置
            if process_id:
                db = SessionLocal()
                try:
                    process = db.query(ApprovalProcess).filter(ApprovalProcess.id == process_id).first()
                    if process and process.config:
                        return process.config
                finally:
                    db.close()
            
            # 使用全局配置
            return self.workflow_config
        except Exception as e:
            print(f"获取工作流配置失败: {str(e)}")
            # 返回默认的最小配置
            return {
                "nodes": [
                    {"id": "start", "name": "开始", "type": "start"},
                    {"id": "approval", "name": "审批", "type": "approval"},
                    {"id": "end", "name": "结束", "type": "end"}
                ],
                "edges": [
                    {"source": "start", "target": "approval"},
                    {"source": "approval", "target": "end"}
                ]
            }
    
    def start_approval_process(self, process_id: int, title: str, description: str = None, applicant_id: int = None, form_data: Dict = None, emergency_level: int = 0) -> ApprovalInstance:
        """
        启动审批流程
        
        参数:
        - process_id: 流程定义ID
        - title: 审批标题
        - description: 审批描述
        - applicant_id: 申请人ID
        - form_data: 表单数据
        - emergency_level: 紧急程度(0-普通, 1-紧急, 2-特急)
        
        返回:
        - 审批实例对象
        """
        try:
            # 打印流程启动信息
            print(f"尝试启动流程: {process_id}, 标题: {title}")
            
            # 验证流程定义是否存在
            process = self.db.query(ApprovalProcess).filter(ApprovalProcess.id == process_id).first()
            if not process:
                print(f"找不到流程定义: {process_id}")
                # 创建一个默认流程用于测试
                process = ApprovalProcess(
                    id=process_id,
                    name=f"流程定义 {process_id}",
                    description="自动创建的默认流程",
                    is_active=True,
                    workflow_config={
                        "nodes": [
                            {"id": "start", "name": "开始", "type": "start"},
                            {"id": "manager_approval", "name": "经理审批", "type": "task"},
                            {"id": "end", "name": "结束", "type": "end"}
                        ],
                        "edges": [
                            {"source": "start", "target": "manager_approval"},
                            {"source": "manager_approval", "target": "end"}
                        ]
                    },
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.db.add(process)
                self.db.commit()
                print(f"已创建默认流程: {process.id}")
            
            # 创建审批实例
            instance = ApprovalInstance(
                process_id=process_id,
                title=title,
                description=description or "",
                current_node="start",  # 初始节点
                status="pending",  # 初始状态
                form_data=form_data or {},
                initiator_id=applicant_id,
                emergency_level=emergency_level,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 保存到数据库
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            
            # 添加流程历史记录
            history = ApprovalHistory(
                instance_id=instance.id,
                node_id="start",
                action="create",
                comments="创建审批流程",
                operator_id=str(applicant_id) if applicant_id else "system",
                operated_at=datetime.now()
            )
            self.db.add(history)
            self.db.commit()
            
            # 初始化流程
            self._initialize_workflow(instance.id)
            
            # 返回创建的实例
            print(f"流程启动成功，实例ID: {instance.id}")
            return instance
            
        except Exception as e:
            self.db.rollback()
            print(f"启动审批流程失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"启动审批流程失败: {str(e)}")
    
    def update_approval_status(self, db: Session, instance_id: int, action: str, user: str) -> ApprovalInstance:
        """更新审批状态"""
        try:
            # 获取审批实例
            instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
            if not instance:
                raise ValueError(f"找不到审批实例: {instance_id}")
            
            # 检查当前状态是否允许该操作
            allowed_actions = {
                'pending': ['approve', 'reject', 'return', 'withdraw'],
                'processing': ['approve', 'reject', 'return'],
                'approved': [],
                'rejected': [],
                'withdrawn': [],
                'terminated': []
            }
            
            if action not in allowed_actions.get(instance.status, []):
                raise ValueError(f"当前状态 {instance.status} 不允许执行 {action} 操作")
            
            # 获取当前节点
            current_node = db.query(ApprovalNode).filter(
                ApprovalNode.instance_id == instance_id,
                ApprovalNode.node_id == instance.current_node
            ).first()
            
            if not current_node:
                raise ValueError(f"找不到当前节点: {instance.current_node}")
            
            # 检查节点状态
            if current_node.status != 'pending':
                raise ValueError(f"节点 {current_node.node_id} 当前状态为 {current_node.status}，不能处理")
            
            # 更新节点状态
            current_node.status = self._get_node_status(action)
            current_node.processor = user
            current_node.processed_at = datetime.now()
            
            # 更新实例状态
            if action == 'approve':
                if self._is_last_node(instance):
                    instance.status = 'approved'
                else:
                    instance.status = 'processing'
                    self._advance_to_next_node(instance_id, instance.current_node)
            elif action == 'reject':
                instance.status = 'rejected'
            elif action == 'return':
                instance.status = 'processing'
                self._return_to_previous_node(instance_id, instance.current_node)
            elif action == 'withdraw':
                instance.status = 'withdrawn'
            
            # 记录状态变更历史
            history = ApprovalHistory(
                instance_id=instance_id,
                node_id=instance.current_node,
                approver_id=user,
                action=action,
                created_at=datetime.now()
            )
            db.add(history)
            
            # 提交更改
            db.commit()
            
            print(f"成功更新审批状态: 实例={instance_id}, 操作={action}, 用户={user}")
            return instance
        
        except Exception as e:
            db.rollback()
            print(f"更新审批状态失败: {str(e)}")
            raise

    def _is_last_node(self, instance: ApprovalInstance) -> bool:
        """检查当前节点是否是最后一个节点"""
        try:
            # 获取流程配置
            workflow_config = self.get_workflow_config(instance.process_id)
            
            # 获取当前节点的出边
            outgoing_edges = [edge for edge in workflow_config.get('edges', []) 
                             if edge.get('source') == instance.current_node]
            
            # 如果没有出边，说明是最后一个节点
            return len(outgoing_edges) == 0
        
        except Exception as e:
            print(f"检查最后一个节点失败: {str(e)}")
            return False

    def _return_to_previous_node(self, instance_id: int, current_node_id: str) -> None:
        """返回到上一个节点"""
        try:
            # 获取实例
            instance = self.db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
            if not instance:
                raise ValueError(f"找不到审批实例: {instance_id}")
            
            # 获取流程配置
            workflow_config = self.get_workflow_config(instance.process_id)
            
            # 获取入边
            incoming_edges = [edge for edge in workflow_config.get('edges', []) 
                             if edge.get('target') == current_node_id]
            
            if not incoming_edges:
                raise ValueError(f"节点 {current_node_id} 没有入边，无法返回")
            
            # 获取上一个节点
            previous_node_id = incoming_edges[0].get('source')
            if not previous_node_id:
                raise ValueError(f"无法获取上一个节点ID")
            
            # 更新实例的当前节点
            instance.current_node = previous_node_id
            instance.previous_node = current_node_id
            
            # 更新节点状态
            previous_node = self.db.query(ApprovalNode).filter(
                ApprovalNode.instance_id == instance_id,
                ApprovalNode.node_id == previous_node_id
            ).first()
            
            if previous_node:
                previous_node.status = 'pending'
                previous_node.processor = None
                previous_node.processed_at = None
            
            # 提交更改
            self.db.commit()
            
            print(f"成功返回到上一个节点: {instance_id} -> {previous_node_id}")
        
        except Exception as e:
            self.db.rollback()
            print(f"返回到上一个节点失败: {str(e)}")
            raise

    def can_process_node(self, db: Session = None, instance = None, user_id: str = None) -> bool:
        """验证用户是否有权限处理当前节点"""
        try:
            if not instance or not user_id:
                print("实例或用户ID为空，无法判断权限")
                return False
                
            # 获取实例信息
            instance_dict = {}
            if isinstance(instance, dict):
                instance_dict = instance
            else:
                instance_dict = {c.name: getattr(instance, c.name) for c in instance.__table__.columns if hasattr(instance, c.name)}
            
            # 获取当前节点
            current_node_id = instance_dict.get('current_node')
            if not current_node_id:
                print("当前节点为空，无法判断权限")
                return False
                
            # 获取节点配置
            node = db.query(ApprovalNode).filter(
                ApprovalNode.instance_id == instance_dict.get('id'),
                ApprovalNode.node_id == current_node_id
            ).first()
            
            if not node:
                print(f"找不到节点配置: {current_node_id}")
                return False
                
            # 检查用户是否是节点指定的处理人
            if node.approver and str(user_id) != str(node.approver):
                print(f"用户 {user_id} 不是指定的处理人 {node.approver}")
                return False
                
            # 检查用户是否在允许的用户列表中
            if node.allowed_users and str(user_id) not in [str(u) for u in node.allowed_users]:
                print(f"用户 {user_id} 不在允许的用户列表中")
                return False
                
            # 获取用户信息
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                print(f"找不到用户: {user_id}")
                return False
                
            # 检查用户角色
            if node.allowed_roles:
                user_roles = [role.id for role in user.roles]
                if not any(role_id in user_roles for role_id in node.allowed_roles):
                    print(f"用户 {user_id} 没有所需的角色")
                    return False
                    
            # 检查职位级别
            if node.required_position_level > 0:
                position = db.query(Position).filter(Position.id == user.position_id).first()
                if not position or position.level < node.required_position_level:
                    print(f"用户 {user_id} 职位级别不足")
                    return False
                    
            # 检查部门级别
            if node.required_department_level > 0:
                department = db.query(Department).filter(Department.id == user.department_id).first()
                if not department or department.level < node.required_department_level:
                    print(f"用户 {user_id} 部门级别不足")
                    return False
                    
            return True
            
        except Exception as e:
            print(f"权限检查出错: {str(e)}")
            return False

    def process_approval(self, db: Session, instance_id: int, node_id: str, action: str, 
                         user_id: str, username: str, comments: str = "") -> Dict[str, Any]:
        """
        处理审批任务
        
        参数:
        - db: 数据库会话
        - instance_id: 审批实例ID
        - node_id: 当前节点ID
        - action: 操作类型(approve, reject, return, withdraw)
        - user_id: 操作用户ID
        - username: 操作用户名
        - comments: 审批意见
        
        返回:
        - 处理结果字典
        """
        try:
            # 获取审批实例
            instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
            if not instance:
                raise ValueError(f"找不到审批实例: {instance_id}")
            
            # 验证当前节点
            if instance.current_node != node_id:
                print(f"警告: 提供的节点ID({node_id})与实例当前节点({instance.current_node})不一致")
            
            # 获取流程定义
            process = db.query(ApprovalProcess).filter(ApprovalProcess.id == instance.process_id).first()
            if not process:
                raise ValueError(f"找不到流程定义: {instance.process_id}")
            
            # 获取工作流配置
            workflow_config = process.workflow_config or {}
            
            # 记录审批历史
            history = ApprovalHistory(
                instance_id=instance_id,
                node_id=instance.current_node,
                action=action,
                comments=comments,
                operator_id=user_id,
                operated_at=datetime.now()
            )
            db.add(history)
            
            # 根据操作类型处理
            result = {}
            if action == "approve":
                # 同意操作 - 流转到下一节点
                result = self._handle_approve(db, instance, workflow_config, user_id, username)
            elif action == "reject":
                # 拒绝操作 - 流程终止
                result = self._handle_reject(db, instance, user_id, username, comments)
            elif action == "return":
                # 退回操作 - 返回上一节点或发起人
                result = self._handle_return(db, instance, workflow_config, user_id, username, comments)
            elif action == "withdraw":
                # 撤回操作 - 流程终止
                result = self._handle_withdraw(db, instance, user_id, username, comments)
            else:
                raise ValueError(f"不支持的操作类型: {action}")
            
            # 提交事务
            db.commit()
            
            # 添加操作信息到结果
            result.update({
                "action": action,
                "operator": username,
                "operated_at": datetime.now().isoformat(),
                "comments": comments
            })
            
            return result
        except Exception as e:
            db.rollback()
            print(f"处理审批失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"处理审批失败: {str(e)}")
        
    def _handle_approve(self, db: Session, instance: ApprovalInstance, 
                       workflow_config: Dict, user_id: str, username: str) -> Dict[str, Any]:
        """处理审批同意操作"""
        try:
            # 获取当前节点信息
            current_node_id = instance.current_node
            nodes = workflow_config.get("nodes", [])
            edges = workflow_config.get("edges", [])
            
            current_node = next((node for node in nodes if node.get("id") == current_node_id), None)
            if not current_node:
                raise ValueError(f"找不到节点配置: {current_node_id}")
            
            # 查找下一个节点
            next_edge = next((edge for edge in edges if edge.get("source") == current_node_id), None)
            if not next_edge:
                # 没有下一个节点，流程结束
                instance.status = "approved"
                instance.current_node = "end"
                instance.completed_at = datetime.now()
                db.commit()
                
                return {
                    "status": "approved",
                    "message": "审批流程已完成",
                    "next_node": "end"
                }
            
            # 有下一个节点，流转到下一节点
            next_node_id = next_edge.get("target")
            instance.current_node = next_node_id
            
            # 查找下一个节点信息
            next_node = next((node for node in nodes if node.get("id") == next_node_id), None)
            if next_node and next_node.get("type") == "end":
                # 下一个是结束节点，流程完成
                instance.status = "approved"
                instance.completed_at = datetime.now()
            
            db.commit()
            
            return {
                "status": instance.status,
                "message": "审批已同意",
                "next_node": next_node_id
            }
        except Exception as e:
            raise Exception(f"处理审批同意操作失败: {str(e)}")
        
    def _handle_reject(self, db: Session, instance: ApprovalInstance, 
                      user_id: str, username: str, comments: str) -> Dict[str, Any]:
        """处理审批拒绝操作"""
        try:
            # 更新实例状态为拒绝
            instance.status = "rejected"
            instance.completed_at = datetime.now()
            db.commit()
            
            return {
                "status": "rejected",
                "message": "审批已拒绝",
                "reason": comments
            }
        except Exception as e:
            raise Exception(f"处理审批拒绝操作失败: {str(e)}")
        
    def _handle_return(self, db: Session, instance: ApprovalInstance, workflow_config: Dict,
                      user_id: str, username: str, comments: str) -> Dict[str, Any]:
        """处理审批退回操作"""
        try:
            # 获取当前节点信息
            current_node_id = instance.current_node
            nodes = workflow_config.get("nodes", [])
            edges = workflow_config.get("edges", [])
            
            # 找到通向当前节点的边，确定上一个节点
            prev_edge = next((edge for edge in edges if edge.get("target") == current_node_id), None)
            if not prev_edge:
                # 没有上一个节点，退回到开始
                instance.current_node = "start"
                instance.status = "returned"
            else:
                # 退回到上一个节点
                prev_node_id = prev_edge.get("source")
                instance.current_node = prev_node_id
                instance.status = "returned"
            
            db.commit()
            
            return {
                "status": "returned",
                "message": "审批已退回",
                "next_node": instance.current_node,
                "reason": comments
            }
        except Exception as e:
            raise Exception(f"处理审批退回操作失败: {str(e)}")
        
    def _handle_withdraw(self, db: Session, instance: ApprovalInstance,
                        user_id: str, username: str, comments: str) -> Dict[str, Any]:
        """处理审批撤回操作"""
        try:
            # 检查是否可以撤回(只有发起人可以撤回，且只能在流程未完成时撤回)
            if str(instance.initiator_id) != user_id:
                raise ValueError("只有发起人可以撤回审批")
            
            if instance.status in ["approved", "rejected", "canceled"]:
                raise ValueError(f"当前状态不能撤回: {instance.status}")
            
            # 更新实例状态为撤回
            instance.status = "canceled"
            instance.completed_at = datetime.now()
            db.commit()
            
            return {
                "status": "canceled",
                "message": "审批已撤回",
                "reason": comments
            }
        except Exception as e:
            raise Exception(f"处理审批撤回操作失败: {str(e)}")

    def _get_node_status(self, action: str) -> str:
        """根据操作获取节点状态"""
        status_map = {
            'approve': 'approved',
            'reject': 'rejected',
            'return': 'returned',
            'withdraw': 'withdrawn'
        }
        return status_map.get(action, 'pending')
        
    def _get_default_approver(self, node_config: dict) -> str:
        """获取节点默认审批人"""
        # 实际项目中应根据角色分配策略确定审批人
        return node_config.get('allowed_users', ['system'])[0]

    def get_user_roles(self, db: Session, user_id: str) -> list:
        """获取用户角色（实际项目中应该从用户服务获取）"""
        # 这里使用模拟数据
        role_mapping = {
            'admin': ['admin', 'manager', 'director', 'finance', 'cfo', 'procurement'],
            'user1': ['initiator'],
            'user2': ['manager'],
            'user3': ['director'],
            'finance': ['finance'],
            'procurement': ['procurement']
        }
        return role_mapping.get(user_id, [])

    def check_user_can_approve(self, user_id, node_id, workflow_config, db):
        """检查用户是否有权限处理当前节点的审批"""
        try:
            # 如果节点ID为空，表示无需审批
            if not node_id:
                return False
            
            # 获取用户
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # 如果用户是管理员，总是有权限
            if user.is_admin:
                return True
            
            # 获取节点配置
            node_config = None
            if 'nodes' in workflow_config:
                node_config = next(
                    (node for node in workflow_config.get('nodes', []) if node.get('id') == node_id),
                    None
                )
            
            if not node_config:
                return False
            
            # 如果节点类型不是审批节点，不需要审批
            if node_config.get('type') != 'approval':
                return False
            
            # 检查用户是否在允许的用户列表中
            allowed_users = node_config.get('allowed_users', [])
            if allowed_users and user_id in allowed_users:
                return True
            
            # 检查用户角色
            allowed_roles = node_config.get('allowed_roles', [])
            if allowed_roles:
                user_roles = user.roles if hasattr(user, 'roles') else []
                if any(role in allowed_roles for role in user_roles):
                    return True
                
            # 检查职位级别要求
            required_position_level = node_config.get('required_position_level', 0)
            if required_position_level > 0:
                user_position_level = self._get_user_position_level(user, db)
                if user_position_level <= required_position_level:
                    return True
                
            # 检查部门级别要求
            required_department_level = node_config.get('required_department_level', 0)
            if required_department_level > 0:
                user_department_level = self._get_user_department_level(user, db)
                if user_department_level <= required_department_level:
                    return True
            
            return False
        except Exception as e:
            print(f"检查用户审批权限失败: {str(e)}")
            return False
        
    def _get_user_position_level(self, user, db):
        """获取用户职位级别"""
        try:
            # 获取用户职位信息
            if hasattr(user, 'position_id') and user.position_id:
                position = db.query(Position).filter(Position.id == user.position_id).first()
                if position and hasattr(position, 'level'):
                    return position.level
            return 99  # 默认为最低级别
        except Exception:
            return 99
        
    def _get_user_department_level(self, user, db):
        """获取用户部门级别"""
        try:
            # 获取用户部门信息
            if hasattr(user, 'department_id') and user.department_id:
                department = db.query(Department).filter(Department.id == user.department_id).first()
                if department and hasattr(department, 'level'):
                    return department.level
            return 99  # 默认为最低级别
        except Exception as e:
            print(f"获取用户部门级别失败: {str(e)}")
            return 99
        
    def initialize_workflow(self, db: Session, instance_id: int, process_id: int, user_id: int):
        """初始化工作流"""
        try:
            # 获取流程定义
            process = db.query(ApprovalProcess).filter(ApprovalProcess.id == process_id).first()
            if not process:
                raise ValueError(f"找不到流程定义: {process_id}")
            
            # 获取审批实例
            instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
            if not instance:
                raise ValueError(f"找不到审批实例: {instance_id}")
            
            # 获取流程配置
            workflow_config = self.get_workflow_config(process_id)
            
            # 查找开始节点
            start_node_id = "start"
            start_node_config = None
            
            # 尝试从流程配置中找到开始节点
            if 'nodes' in workflow_config:
                for node in workflow_config.get('nodes', []):
                    if node.get('type') == 'start':
                        start_node_id = node.get('id')
                        start_node_config = node
                        break
            elif 'states' in workflow_config:
                # 如果使用states格式，找到第一个状态
                keys = list(workflow_config.get('states', {}).keys())
                if keys:
                    start_node_id = keys[0]
                    start_node_config = workflow_config['states'][start_node_id]
            
            # 如果找不到开始节点，使用默认配置
            if not start_node_config:
                print(f"在流程配置中找不到开始节点，使用默认值")
                start_node_config = {
                    "id": start_node_id,
                    "name": "开始",
                    "type": "start",
                    "description": "流程开始"
                }
            
            # 设置实例的当前节点为开始节点
            instance.current_node = start_node_id
            instance.status = "pending"
            
            # 创建节点记录
            node = ApprovalNode(
                instance_id=instance_id,
                process_id=process_id,
                node_id=start_node_id,
                name=start_node_config.get('name', '开始'),
                type=start_node_config.get('type', 'start'),
                description=start_node_config.get('description', '流程开始'),
                status="pending",
                is_completed=False,
                created_at=datetime.now()
            )
            db.add(node)
            
            # 创建审批历史记录
            history = ApprovalHistory(
                instance_id=instance_id,
                node_id=start_node_id,
                approver_id=user_id,
                action="create",
                comment="流程创建"
            )
            db.add(history)
            
            # 提交更改
            db.commit()
            
            print(f"成功初始化工作流: {instance_id}")
            return {
                "success": True,
                "instance_id": instance_id,
                "current_node": start_node_id,
                "status": "pending"
            }
        except Exception as e:
            db.rollback()
            print(f"初始化工作流失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def skip_approval(self, db: Session, instance_id: int, to_node_id: str, comment: str, user_id: str):
        """跳过审批节点（仅限管理员或特权用户）"""
        try:
            # 获取审批实例
            instance = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
            if not instance:
                raise ValueError(f"找不到审批实例: {instance_id}")
                
            # 获取当前用户
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                raise ValueError(f"找不到用户: {user_id}")
                
            # 验证权限 - 只有管理员或特权用户可以跳过审批
            if not user.is_admin:
                raise ValueError("只有管理员可以跳过审批流程")
                
            # 获取工作流配置
            workflow_config = self.get_workflow_config(instance.process_id)
            
            # 验证目标节点是否存在
            target_node_config = None
            if 'nodes' in workflow_config:
                for node in workflow_config.get('nodes', []):
                    if node.get('id') == to_node_id:
                        target_node_config = node
                        break
            elif 'states' in workflow_config and to_node_id in workflow_config.get('states', {}):
                target_node_config = workflow_config['states'][to_node_id]
                
            if not target_node_config:
                raise ValueError(f"找不到目标节点: {to_node_id}")
                
            # 获取当前节点
            current_node = db.query(ApprovalNode).filter(
                ApprovalNode.instance_id == instance_id,
                ApprovalNode.node_id == instance.current_node,
                ApprovalNode.status == "pending"
            ).first()
            
            if current_node:
                # 标记当前节点为跳过
                current_node.status = "skipped"
                current_node.comment = f"被管理员跳过: {comment}"
                current_node.processor = user_id
                current_node.processed_at = datetime.now()
            
            # 创建新的节点记录
            new_node = ApprovalNode(
                instance_id=instance_id,
                process_id=instance.process_id,
                node_id=to_node_id,
                name=target_node_config.get('name', to_node_id),
                type=target_node_config.get('type', 'approval'),
                description=target_node_config.get('description', ''),
                approver=None,  # 不指定审批人，由系统根据角色分配
                status="pending"
            )
            db.add(new_node)
            
            # 更新实例状态
            instance.current_node = to_node_id
            instance.updated_at = datetime.now()
            
            # 如果目标节点是结束节点，则标记为完成
            if to_node_id == 'end':
                instance.status = 'completed'
            
            # 创建审批历史记录
            history = ApprovalHistory(
                instance_id=instance_id,
                node_id=instance.current_node,
                approver_id=user_id,
                action="skip",
                comment=f"跳过审批至节点 {to_node_id}: {comment}"
            )
            db.add(history)
            
            # 提交更改
            db.commit()
            
            return {
                'success': True,
                'id': instance.id,
                'status': instance.status,
                'current_node': instance.current_node,
                'message': f"已将审批跳转到 {target_node_config.get('name', to_node_id)}"
            }
        except Exception as e:
            db.rollback()
            print(f"跳过审批节点失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"跳过审批节点失败: {str(e)}")

    def _initialize_workflow(self, instance_id: int) -> None:
        """
        初始化工作流程
        
        参数:
        - instance_id: 审批实例ID
        
        操作:
        - 获取审批实例
        - 获取对应的流程配置
        - 设置初始节点
        - 如果有自动处理节点，执行自动处理
        """
        try:
            # 获取审批实例
            instance = self.db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
            if not instance:
                print(f"找不到审批实例: {instance_id}")
                return
            
            # 获取流程配置
            process = self.db.query(ApprovalProcess).filter(ApprovalProcess.id == instance.process_id).first()
            if not process:
                print(f"找不到流程定义: {instance.process_id}")
                return
            
            # 获取工作流配置
            workflow_config = process.workflow_config
            if not workflow_config or "nodes" not in workflow_config:
                # 创建默认配置
                workflow_config = {
                    "nodes": [
                        {"id": "start", "name": "开始", "type": "start"},
                        {"id": "manager_approval", "name": "经理审批", "type": "task"},
                        {"id": "end", "name": "结束", "type": "end"}
                    ],
                    "edges": [
                        {"source": "start", "target": "manager_approval"},
                        {"source": "manager_approval", "target": "end"}
                    ]
                }
            
            # 设置初始节点(通常是'start')
            start_node = next((node for node in workflow_config.get("nodes", []) if node.get("type") == "start"), None)
            if start_node:
                current_node_id = start_node.get("id", "start")
            else:
                current_node_id = "start"
            
            # 更新实例的当前节点
            instance.current_node = current_node_id
            self.db.commit()
            
            # 自动前进到下一个节点(如果初始节点是自动节点)
            self._advance_to_next_node(instance_id, current_node_id)
            
            print(f"工作流初始化完成，实例ID: {instance_id}，当前节点: {current_node_id}")
        except Exception as e:
            self.db.rollback()
            print(f"初始化工作流失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def _advance_to_next_node(self, instance_id: int, current_node_id: str) -> None:
        """
        根据工作流配置自动推进到下一个节点
        
        参数:
        - instance_id: 审批实例ID
        - current_node_id: 当前节点ID
        """
        try:
            # 获取审批实例
            instance = self.db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
            if not instance:
                print(f"找不到审批实例: {instance_id}")
                return
            
            # 获取流程配置
            process = self.db.query(ApprovalProcess).filter(ApprovalProcess.id == instance.process_id).first()
            if not process or not process.workflow_config:
                print(f"找不到有效的工作流配置: {instance.process_id}")
                return
            
            workflow_config = process.workflow_config
            
            # 获取当前节点信息
            current_node = next((node for node in workflow_config.get("nodes", []) if node.get("id") == current_node_id), None)
            if not current_node:
                print(f"找不到节点信息: {current_node_id}")
                return
            
            # 如果当前是开始节点，自动前进到下一个节点
            if current_node.get("type") == "start":
                # 查找下一个节点
                next_edge = next((edge for edge in workflow_config.get("edges", []) if edge.get("source") == current_node_id), None)
                if next_edge:
                    next_node_id = next_edge.get("target")
                    # 更新当前节点
                    instance.current_node = next_node_id
                    self.db.commit()
                    
                    # 添加历史记录
                    history = ApprovalHistory(
                        instance_id=instance_id,
                        node_id=next_node_id,
                        action="auto_forward",
                        comments="系统自动流转到下一节点",
                        operator_id="system",
                        operated_at=datetime.now()
                    )
                    self.db.add(history)
                    self.db.commit()
                    
                    print(f"自动前进到下一节点: {next_node_id}")
                    
                    # 递归检查下一个节点是否也需要自动前进
                    self._advance_to_next_node(instance_id, next_node_id)
        except Exception as e:
            self.db.rollback()
            print(f"自动前进到下一节点失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def check_timeout_approvals(self) -> None:
        """检查超时的审批流程"""
        try:
            # 获取所有待处理的审批实例
            pending_instances = self.db.query(ApprovalInstance).filter(
                ApprovalInstance.status.in_(['pending', 'processing'])
            ).all()
            
            for instance in pending_instances:
                # 获取当前节点
                current_node = self.db.query(ApprovalNode).filter(
                    ApprovalNode.instance_id == instance.id,
                    ApprovalNode.node_id == instance.current_node
                ).first()
                
                if not current_node:
                    continue
                    
                # 检查节点是否超时
                if self._is_node_timeout(current_node):
                    # 处理超时
                    self._handle_timeout(instance, current_node)
                    
        except Exception as e:
            print(f"检查超时审批失败: {str(e)}")

    def _is_node_timeout(self, node: ApprovalNode) -> bool:
        """检查节点是否超时"""
        try:
            # 获取节点配置
            config = node.config or {}
            timeout_hours = config.get('timeout_hours', 0)
            
            if timeout_hours <= 0:
                return False
            
            # 计算超时时间
            timeout_time = node.created_at + timedelta(hours=timeout_hours)
            return datetime.now() > timeout_time
            
        except Exception as e:
            print(f"检查节点超时失败: {str(e)}")
            return False

    def _handle_timeout(self, instance: ApprovalInstance, node: ApprovalNode) -> None:
        """处理超时节点"""
        try:
            # 获取节点配置
            config = node.config or {}
            timeout_action = config.get('timeout_action', 'auto_approve')
            
            # 根据配置执行超时动作
            if timeout_action == 'auto_approve':
                # 自动通过
                node.status = 'approved'
                node.processor = 'system'
                node.processed_at = datetime.now()
                node.comment = '系统自动通过（超时处理）'
                
                # 更新实例状态
                if self._is_last_node(instance):
                    instance.status = 'approved'
                else:
                    instance.status = 'processing'
                    self._advance_to_next_node(instance.id, instance.current_node)
                
            elif timeout_action == 'auto_reject':
                # 自动拒绝
                node.status = 'rejected'
                node.processor = 'system'
                node.processed_at = datetime.now()
                node.comment = '系统自动拒绝（超时处理）'
                
                # 更新实例状态
                instance.status = 'rejected'
            
            elif timeout_action == 'escalate':
                # 升级处理
                escalation_users = config.get('escalation_users', [])
                if escalation_users:
                    # 更新节点处理人
                    node.approver = escalation_users[0]
                    # 发送通知
                    self._send_timeout_notification(instance, node, escalation_users)
                
            # 记录超时处理历史
            history = ApprovalHistory(
                instance_id=instance.id,
                node_id=node.node_id,
                approver_id='system',
                action='timeout',
                comment=f'节点超时处理: {timeout_action}',
                created_at=datetime.now()
            )
            self.db.add(history)
            
            # 提交更改
            self.db.commit()
            
            print(f"成功处理超时节点: 实例={instance.id}, 节点={node.node_id}, 动作={timeout_action}")
            
        except Exception as e:
            self.db.rollback()
            print(f"处理超时节点失败: {str(e)}")

    def _send_timeout_notification(self, instance: ApprovalInstance, node: ApprovalNode, users: list) -> None:
        """发送超时通知"""
        try:
            # 构建通知内容
            notification = {
                'type': 'approval_timeout',
                'instance_id': instance.id,
                'title': instance.title,
                'node_name': node.name,
                'timeout_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'users': users
            }
            
            # TODO: 实现具体的通知发送逻辑
            print(f"发送超时通知: {notification}")
            
        except Exception as e:
            print(f"发送超时通知失败: {str(e)}")

    def _log_approval_action(self, instance_id: int, action: str, user_id: str, details: dict = None) -> None:
        """记录审批操作日志"""
        try:
            # 构建日志内容
            log_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'action': action,
                'user_id': user_id,
                'details': details or {}
            }
            
            # 获取实例
            instance = self.db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
            if not instance:
                return
            
            # 更新日志
            logs = instance.logs or []
            logs.append(log_entry)
            instance.logs = logs
            
            # 提交更改
            self.db.commit()
            
            print(f"记录审批操作日志: 实例={instance_id}, 操作={action}, 用户={user_id}")
            
        except Exception as e:
            print(f"记录审批操作日志失败: {str(e)}")

    def _log_node_status_change(self, node_id: str, old_status: str, new_status: str, reason: str = None) -> None:
        """记录节点状态变更日志"""
        try:
            # 获取节点
            node = self.db.query(ApprovalNode).filter(ApprovalNode.node_id == node_id).first()
            if not node:
                return
            
            # 构建日志内容
            log_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'old_status': old_status,
                'new_status': new_status,
                'reason': reason
            }
            
            # 更新节点日志
            node_logs = node.logs or []
            node_logs.append(log_entry)
            node.logs = node_logs
            
            # 提交更改
            self.db.commit()
            
            print(f"记录节点状态变更: 节点={node_id}, 状态={old_status}->{new_status}")
            
        except Exception as e:
            print(f"记录节点状态变更日志失败: {str(e)}")

    def _log_error(self, error_type: str, error_message: str, context: dict = None) -> None:
        """记录错误日志"""
        try:
            # 构建错误日志
            error_log = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': error_type,
                'message': error_message,
                'context': context or {}
            }
            
            # TODO: 实现错误日志的存储，可以存储到文件或数据库
            print(f"错误日志: {error_log}")
            
        except Exception as e:
            print(f"记录错误日志失败: {str(e)}")

    def _log_performance(self, operation: str, start_time: datetime, end_time: datetime, details: dict = None) -> None:
        """记录性能日志"""
        try:
            # 计算耗时
            duration = (end_time - start_time).total_seconds()
            
            # 构建性能日志
            performance_log = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'operation': operation,
                'duration': duration,
                'details': details or {}
            }
            
            # TODO: 实现性能日志的存储，可以存储到文件或数据库
            print(f"性能日志: {performance_log}")
            
        except Exception as e:
            print(f"记录性能日志失败: {str(e)}")

    def get_pending_approvals(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取待处理的审批列表
        
        参数:
        - user_id: 当前用户ID
        
        返回:
        - 待处理审批列表
        """
        try:
            # 返回测试数据
            return [
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
        except Exception as e:
            print(f"获取待处理审批失败: {str(e)}")
            return []
            
    def get_my_approvals(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取我发起的审批列表
        
        参数:
        - user_id: 当前用户ID
        
        返回:
        - 我发起的审批列表
        """
        try:
            # 返回测试数据
            return [
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
        except Exception as e:
            print(f"获取我的审批失败: {str(e)}")
            return []
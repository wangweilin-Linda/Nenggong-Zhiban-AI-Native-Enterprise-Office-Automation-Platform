"""
审批流程状态机模块，处理审批流程中的状态转换
"""

from typing import Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class State(ABC):
    """状态抽象基类"""
    def __init__(self, context: 'StateContext'):
        self.context = context
    
    @abstractmethod
    def handle_approve(self, context):
        pass
    
    @abstractmethod
    def handle_reject(self, context):
        pass
    
    @abstractmethod
    def handle_return(self, context):
        pass
    
    @abstractmethod
    def handle_withdraw(self, context):
        pass
    
    def handle_skip(self, context, to_node):
        """处理跳过操作，默认实现"""
        logger.info(f"状态 {self.__class__.__name__} 处理跳过操作到 {to_node}")
        # 检查是否允许跳过
        if not context.can_skip_to(to_node):
            logger.warning(f"不允许从 {context.current_state.__class__.__name__} 跳过到 {to_node}")
            return False
            
        # 执行跳过操作
        context.skip_to(to_node)
        return True

class ApprovalState:
    """基础审批状态类"""
    def __init__(self, context):
        self.context = context
    
    def submit(self):
        """提交申请"""
        raise NotImplementedError("子类必须实现此方法")
    
    def approve(self):
        """批准申请"""
        raise NotImplementedError("子类必须实现此方法")
    
    def reject(self):
        """拒绝申请"""
        raise NotImplementedError("子类必须实现此方法")
    
    def withdraw(self):
        """撤回申请"""
        raise NotImplementedError("子类必须实现此方法")
    
    def return_to_previous(self):
        """退回到上一步"""
        raise NotImplementedError("子类必须实现此方法")


class DraftState(ApprovalState):
    """草稿状态"""
    def submit(self):
        """提交申请"""
        self.context.set_state(PendingState(self.context))
        return {"success": True, "message": "成功提交申请", "next_state": "pending"}
    
    def approve(self):
        """草稿状态无法批准"""
        return {"success": False, "message": "草稿状态无法批准"}
    
    def reject(self):
        """草稿状态无法拒绝"""
        return {"success": False, "message": "草稿状态无法拒绝"}
    
    def withdraw(self):
        """草稿状态无法撤回"""
        return {"success": False, "message": "草稿状态无需撤回"}
    
    def return_to_previous(self):
        """草稿状态无法退回"""
        return {"success": False, "message": "草稿状态无法退回"}


class PendingState(ApprovalState):
    """待审批状态"""
    def submit(self):
        """已提交状态无法再次提交"""
        return {"success": False, "message": "申请已提交，无法再次提交"}
    
    def approve(self):
        """批准申请"""
        self.context.set_state(ApprovedState(self.context))
        return {"success": True, "message": "申请已批准", "next_state": "approved"}
    
    def reject(self):
        """拒绝申请"""
        self.context.set_state(RejectedState(self.context))
        return {"success": True, "message": "申请已拒绝", "next_state": "rejected"}
    
    def withdraw(self):
        """撤回申请"""
        self.context.set_state(WithdrawnState(self.context))
        return {"success": True, "message": "申请已撤回", "next_state": "withdrawn"}
    
    def return_to_previous(self):
        """退回到上一步"""
        self.context.set_state(DraftState(self.context))
        return {"success": True, "message": "申请已退回", "next_state": "draft"}


class ApprovedState(ApprovalState):
    """已批准状态"""
    def submit(self):
        """已批准状态无法提交"""
        return {"success": False, "message": "申请已批准，无法提交"}
    
    def approve(self):
        """已批准状态无法再次批准"""
        return {"success": False, "message": "申请已批准，无法再次批准"}
    
    def reject(self):
        """已批准状态无法拒绝"""
        return {"success": False, "message": "申请已批准，无法拒绝"}
    
    def withdraw(self):
        """已批准状态无法撤回"""
        return {"success": False, "message": "申请已批准，无法撤回"}
    
    def return_to_previous(self):
        """已批准状态无法退回"""
        return {"success": False, "message": "申请已批准，无法退回"}


class RejectedState(ApprovalState):
    """已拒绝状态"""
    def submit(self):
        """已拒绝状态可以重新提交"""
        self.context.set_state(PendingState(self.context))
        return {"success": True, "message": "申请已重新提交", "next_state": "pending"}
    
    def approve(self):
        """已拒绝状态无法批准"""
        return {"success": False, "message": "申请已拒绝，无法批准"}
    
    def reject(self):
        """已拒绝状态无法再次拒绝"""
        return {"success": False, "message": "申请已拒绝，无法再次拒绝"}
    
    def withdraw(self):
        """已拒绝状态无法撤回"""
        return {"success": False, "message": "申请已拒绝，无法撤回"}
    
    def return_to_previous(self):
        """已拒绝状态无法退回"""
        return {"success": False, "message": "申请已拒绝，无法退回"}


class WithdrawnState(ApprovalState):
    """已撤回状态"""
    def submit(self):
        """已撤回状态可以重新提交"""
        self.context.set_state(PendingState(self.context))
        return {"success": True, "message": "申请已重新提交", "next_state": "pending"}
    
    def approve(self):
        """已撤回状态无法批准"""
        return {"success": False, "message": "申请已撤回，无法批准"}
    
    def reject(self):
        """已撤回状态无法拒绝"""
        return {"success": False, "message": "申请已撤回，无法拒绝"}
    
    def withdraw(self):
        """已撤回状态无法再次撤回"""
        return {"success": False, "message": "申请已撤回，无法再次撤回"}
    
    def return_to_previous(self):
        """已撤回状态无法退回"""
        return {"success": False, "message": "申请已撤回，无法退回"}


class StateContext:
    """状态上下文，持有当前状态并管理状态转换"""
    def __init__(self, instance, workflow_config):
        """初始化状态上下文
        
        Args:
            instance: 审批实例对象
            workflow_config: 工作流配置
        """
        self.instance = instance
        self.workflow_config = workflow_config
        
        # 根据实例状态设置初始状态
        self._set_initial_state()
        
    def _set_initial_state(self):
        """根据实例状态设置初始状态"""
        status = self.instance.status.lower() if self.instance.status else "pending"
        
        if status == "draft":
            self.current_state = DraftState(self)
        elif status == "pending" or status == "processing":
            self.current_state = PendingState(self)
        elif status == "approved":
            self.current_state = ApprovedState(self)
        elif status == "rejected":
            self.current_state = RejectedState(self)
        elif status == "withdrawn":
            self.current_state = WithdrawnState(self)
        elif status == "terminated":
            self.current_state = TerminatedState(self)
        else:
            # 默认为待审批状态
            self.current_state = PendingState(self)
            
    def set_state(self, state):
        """设置当前状态
        
        Args:
            state: 新的状态对象
        """
        logger.info(f"状态转换: {self.current_state.__class__.__name__} -> {state.__class__.__name__}")
        self.current_state = state
    
    def approve(self):
        """执行审批操作"""
        return self.current_state.handle_approve(self)
    
    def reject(self):
        """执行拒绝操作"""
        return self.current_state.handle_reject(self)
    
    def return_back(self):
        """执行退回操作"""
        return self.current_state.handle_return(self)
    
    def withdraw(self):
        """执行撤回操作"""
        return self.current_state.handle_withdraw(self)
    
    def skip_to(self, node_id):
        """跳转到指定节点
        
        Args:
            node_id: 目标节点ID
        """
        # 更新实例状态
        self.instance.current_node = node_id
        return True
    
    def can_skip_to(self, node_id):
        """检查是否可以跳转到指定节点
        
        Args:
            node_id: 目标节点ID
            
        Returns:
            bool: 是否允许跳转
        """
        # 只有pending状态的流程可以跳转
        if self.instance.status.lower() not in ["pending", "processing"]:
            return False
            
        # 检查目标节点是否存在
        if self.workflow_config and "nodes" in self.workflow_config:
            nodes = self.workflow_config["nodes"]
            if isinstance(nodes, dict) and node_id in nodes:
                return True
            elif isinstance(nodes, list):
                for node in nodes:
                    if node.get("id") == node_id:
                        return True
                        
        return False

class TerminatedState(State):
    """已终止状态"""
    
    def handle_approve(self, context):
        """已终止状态不能被批准"""
        logger.warning("已终止状态不能被批准")
        return False
        
    def handle_reject(self, context):
        """已终止状态不能被拒绝"""
        logger.warning("已终止状态不能被拒绝")
        return False
        
    def handle_return(self, context):
        """已终止状态不能被退回"""
        logger.warning("已终止状态不能被退回")
        return False
        
    def handle_withdraw(self, context):
        """已终止状态不能被撤回"""
        logger.warning("已终止状态不能被撤回")
        return False
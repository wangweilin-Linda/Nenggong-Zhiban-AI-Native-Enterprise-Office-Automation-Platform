#!/usr/bin/env python
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from models.base import Base
from models.document.workflow_design import WorkflowDesign
from models.user import User


class WorkflowInstance(Base):
    """工作流实例模型，存储工作流运行时状态"""
    __tablename__ = "workflow_instances"

    id = Column(String(36), primary_key=True, index=True)
    workflow_design_id = Column(String(36), ForeignKey("workflow_designs.id"), nullable=False)
    workflow_version_id = Column(String(36), nullable=False, comment="工作流设计版本ID")
    
    title = Column(String(255), nullable=False, comment="审批标题")
    initiator_id = Column(String(36), ForeignKey("users.id"), nullable=False, comment="发起人ID")
    
    # 实例状态：draft(草稿), pending(待审批), processing(审批中), approved(已批准), rejected(已拒绝), withdrawn(已撤回), terminated(已终止)
    status = Column(String(20), nullable=False, default="draft", comment="实例状态")
    
    # 当前节点ID，对应工作流设计中的节点
    current_node = Column(String(36), nullable=True, comment="当前节点ID")
    
    # 表单数据，JSON格式存储
    form_data = Column(JSON, nullable=True, comment="表单数据")
    
    # 业务数据ID，如报销单ID、请假单ID等
    business_id = Column(String(36), nullable=True, comment="业务数据ID")
    business_type = Column(String(50), nullable=True, comment="业务类型")
    
    # 时间记录
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    submit_time = Column(DateTime, nullable=True, comment="提交时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    complete_time = Column(DateTime, nullable=True, comment="完成时间")
    
    # 关联关系
    workflow_design = relationship("WorkflowDesign", backref="instances")
    initiator = relationship("User", backref="initiated_workflows")
    
    # 记录当前处理人，可能是多个
    current_handlers = Column(JSON, nullable=True, comment="当前处理人ID列表")
    
    # 关联审批记录
    approval_records = relationship("ApprovalRecord", back_populates="workflow_instance", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<WorkflowInstance {self.id}: {self.title} - {self.status}>"
    
    @property
    def is_active(self) -> bool:
        """实例是否处于活动状态（可以继续处理）"""
        return self.status in ["pending", "processing"]
    
    @property
    def is_completed(self) -> bool:
        """实例是否已完成（已批准或已拒绝）"""
        return self.status in ["approved", "rejected"]
    
    @property
    def is_terminated(self) -> bool:
        """实例是否已终止（已撤回或已终止）"""
        return self.status in ["withdrawn", "terminated"]
    
    def get_next_handlers(self, workflow_config: Dict[str, Any]) -> List[str]:
        """根据工作流配置获取下一节点的处理人
        
        Args:
            workflow_config: 工作流配置
            
        Returns:
            List[str]: 处理人ID列表
        """
        if not self.current_node or not workflow_config:
            return []
            
        # 获取当前节点的出边
        edges = workflow_config.get("edges", [])
        next_node_id = None
        
        for edge in edges:
            if edge.get("source") == self.current_node:
                next_node_id = edge.get("target")
                break
                
        if not next_node_id:
            return []
            
        # 获取下一节点的处理人
        nodes = workflow_config.get("nodes", [])
        next_node = None
        
        if isinstance(nodes, dict):
            next_node = nodes.get(next_node_id, {})
        else:
            for node in nodes:
                if node.get("id") == next_node_id:
                    next_node = node
                    break
                    
        if not next_node:
            return []
            
        # 返回处理人ID列表
        handlers = next_node.get("handlers", [])
        if isinstance(handlers, list):
            return handlers
        elif isinstance(handlers, str):
            return [handlers]
        else:
            return []
            
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "id": self.id,
            "workflow_design_id": self.workflow_design_id,
            "workflow_version_id": self.workflow_version_id,
            "title": self.title,
            "initiator_id": self.initiator_id,
            "initiator_name": self.initiator.name if self.initiator else None,
            "status": self.status,
            "current_node": self.current_node,
            "form_data": self.form_data,
            "business_id": self.business_id,
            "business_type": self.business_type,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "submit_time": self.submit_time.isoformat() if self.submit_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
            "complete_time": self.complete_time.isoformat() if self.complete_time else None,
            "current_handlers": self.current_handlers,
            "approval_records": [record.to_dict() for record in self.approval_records] if self.approval_records else []
        }
        

class ApprovalRecord(Base):
    """审批记录模型，存储每个节点的审批信息"""
    __tablename__ = "approval_records"
    
    id = Column(String(36), primary_key=True, index=True)
    workflow_instance_id = Column(String(36), ForeignKey("workflow_instances.id"), nullable=False)
    
    node_id = Column(String(36), nullable=False, comment="节点ID")
    node_name = Column(String(100), nullable=True, comment="节点名称")
    
    operator_id = Column(String(36), ForeignKey("users.id"), nullable=False, comment="操作人ID")
    operation = Column(String(20), nullable=False, comment="操作类型：approve, reject, return, withdraw, skip")
    
    comment = Column(Text, nullable=True, comment="审批意见")
    
    # 操作前后的状态
    pre_status = Column(String(20), nullable=True, comment="操作前状态")
    post_status = Column(String(20), nullable=True, comment="操作后状态")
    
    # 其他操作记录
    attachments = Column(JSON, nullable=True, comment="附件列表")
    
    # 操作时间
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联关系
    workflow_instance = relationship("WorkflowInstance", back_populates="approval_records")
    operator = relationship("User", backref="approval_records")
    
    def __repr__(self):
        return f"<ApprovalRecord {self.id}: {self.node_name} - {self.operation}>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "id": self.id,
            "workflow_instance_id": self.workflow_instance_id,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "operator_id": self.operator_id,
            "operator_name": self.operator.name if self.operator else None,
            "operation": self.operation,
            "comment": self.comment,
            "pre_status": self.pre_status,
            "post_status": self.post_status,
            "attachments": self.attachments,
            "create_time": self.create_time.isoformat() if self.create_time else None
        } 
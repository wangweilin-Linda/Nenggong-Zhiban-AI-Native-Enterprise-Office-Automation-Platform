#!/usr/bin/env python
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.document.workflow_instance import WorkflowInstance, ApprovalRecord
from models.document.workflow_design import WorkflowDesign, WorkflowDesignVersion
from models.user import User
from services.state_machine import StateContext

logger = logging.getLogger(__name__)

class WorkflowInstanceService:
    """工作流实例服务，处理工作流实例的生命周期管理"""
    
    @staticmethod
    def create_instance(db: Session, 
                       workflow_design_id: str, 
                       title: str, 
                       initiator_id: str, 
                       form_data: Optional[Dict[str, Any]] = None, 
                       business_id: Optional[str] = None,
                       business_type: Optional[str] = None) -> WorkflowInstance:
        """创建工作流实例
        
        Args:
            db: 数据库会话
            workflow_design_id: 工作流设计ID
            title: 实例标题
            initiator_id: 发起人ID
            form_data: 表单数据
            business_id: 业务数据ID
            business_type: 业务类型
            
        Returns:
            WorkflowInstance: 创建的工作流实例
        """
        # 获取工作流设计
        workflow_design = db.query(WorkflowDesign).filter(WorkflowDesign.id == workflow_design_id).first()
        if not workflow_design:
            raise ValueError(f"工作流设计不存在: {workflow_design_id}")
            
        # 获取最新版本
        latest_version = db.query(WorkflowDesignVersion)\
            .filter(WorkflowDesignVersion.workflow_design_id == workflow_design_id)\
            .order_by(WorkflowDesignVersion.version.desc())\
            .first()
            
        if not latest_version:
            raise ValueError(f"工作流设计没有可用版本: {workflow_design_id}")
            
        # 获取工作流配置
        workflow_config = latest_version.workflow_config
        
        # 找到起始节点
        start_node_id = None
        
        if not workflow_config or "nodes" not in workflow_config:
            raise ValueError(f"工作流配置无效: {workflow_design_id}")
            
        nodes = workflow_config.get("nodes", [])
        
        # 根据节点类型找到起始节点
        if isinstance(nodes, list):
            for node in nodes:
                if node.get("type") == "start":
                    start_node_id = node.get("id")
                    break
        elif isinstance(nodes, dict):
            for node_id, node in nodes.items():
                if node.get("type") == "start":
                    start_node_id = node_id
                    break
                    
        if not start_node_id:
            # 如果没有明确的起始节点，使用第一个节点
            if isinstance(nodes, list) and len(nodes) > 0:
                start_node_id = nodes[0].get("id")
            elif isinstance(nodes, dict) and len(nodes) > 0:
                start_node_id = list(nodes.keys())[0]
                
        # 创建实例
        instance = WorkflowInstance(
            id=str(uuid.uuid4()),
            workflow_design_id=workflow_design_id,
            workflow_version_id=latest_version.id,
            title=title,
            initiator_id=initiator_id,
            status="draft",
            current_node=start_node_id,
            form_data=form_data or {},
            business_id=business_id,
            business_type=business_type,
            create_time=datetime.now(),
            current_handlers=[]  # 草稿状态下没有处理人
        )
        
        db.add(instance)
        db.commit()
        db.refresh(instance)
        
        logger.info(f"创建工作流实例: {instance.id}, 标题: {title}, 发起人: {initiator_id}")
        return instance
        
    @staticmethod
    def submit_instance(db: Session, instance_id: str, operator_id: str, form_data: Optional[Dict[str, Any]] = None) -> WorkflowInstance:
        """提交工作流实例，从草稿状态转为待审批状态
        
        Args:
            db: 数据库会话
            instance_id: 实例ID
            operator_id: 操作人ID
            form_data: 更新的表单数据
            
        Returns:
            WorkflowInstance: 更新后的工作流实例
        """
        # 获取实例
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance:
            raise ValueError(f"工作流实例不存在: {instance_id}")
            
        if instance.status != "draft":
            raise ValueError(f"只有草稿状态的实例可以提交，当前状态: {instance.status}")
            
        # 获取工作流设计版本
        version = db.query(WorkflowDesignVersion).filter(WorkflowDesignVersion.id == instance.workflow_version_id).first()
        if not version:
            raise ValueError(f"工作流设计版本不存在: {instance.workflow_version_id}")
            
        # 获取工作流配置
        workflow_config = version.workflow_config
        
        # 更新表单数据
        if form_data:
            instance.form_data = {**instance.form_data, **form_data} if instance.form_data else form_data
            
        # 获取下一个节点的处理人
        next_handlers = instance.get_next_handlers(workflow_config)
        
        # 更新实例状态
        instance.status = "pending"
        instance.submit_time = datetime.now()
        instance.update_time = datetime.now()
        instance.current_handlers = next_handlers
        
        # 创建提交记录
        record = ApprovalRecord(
            id=str(uuid.uuid4()),
            workflow_instance_id=instance_id,
            node_id=instance.current_node,
            node_name=WorkflowInstanceService._get_node_name(workflow_config, instance.current_node),
            operator_id=operator_id,
            operation="submit",
            pre_status="draft",
            post_status="pending",
            create_time=datetime.now()
        )
        
        db.add(record)
        db.commit()
        db.refresh(instance)
        
        logger.info(f"提交工作流实例: {instance.id}, 操作人: {operator_id}, 当前状态: {instance.status}")
        return instance
        
    @staticmethod
    def approve(db: Session, instance_id: str, operator_id: str, comment: Optional[str] = None, attachments: Optional[List[Any]] = None) -> WorkflowInstance:
        """审批通过工作流实例
        
        Args:
            db: 数据库会话
            instance_id: 实例ID
            operator_id: 操作人ID
            comment: 审批意见
            attachments: 附件列表
            
        Returns:
            WorkflowInstance: 更新后的工作流实例
        """
        # 获取实例
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance:
            raise ValueError(f"工作流实例不存在: {instance_id}")
            
        # 检查权限：操作人必须在当前处理人列表中
        if instance.current_handlers and operator_id not in instance.current_handlers:
            raise ValueError(f"操作人 {operator_id} 不在当前处理人列表中")
            
        # 获取工作流设计版本
        version = db.query(WorkflowDesignVersion).filter(WorkflowDesignVersion.id == instance.workflow_version_id).first()
        if not version:
            raise ValueError(f"工作流设计版本不存在: {instance.workflow_version_id}")
            
        # 获取工作流配置
        workflow_config = version.workflow_config
        
        # 使用状态机处理状态转换
        pre_status = instance.status
        context = StateContext(instance)
        context.approve()
        
        # 创建审批记录
        record = ApprovalRecord(
            id=str(uuid.uuid4()),
            workflow_instance_id=instance_id,
            node_id=instance.current_node,
            node_name=WorkflowInstanceService._get_node_name(workflow_config, instance.current_node),
            operator_id=operator_id,
            operation="approve",
            comment=comment,
            pre_status=pre_status,
            post_status=instance.status,
            attachments=attachments,
            create_time=datetime.now()
        )
        
        db.add(record)
        
        # 判断是否进入下一节点
        nodes = workflow_config.get("nodes", [])
        edges = workflow_config.get("edges", [])
        
        # 判断当前节点是否为结束节点
        current_node = None
        if isinstance(nodes, list):
            for node in nodes:
                if node.get("id") == instance.current_node:
                    current_node = node
                    break
        elif isinstance(nodes, dict):
            current_node = nodes.get(instance.current_node, {})
            
        # 如果当前节点是结束节点或没有出边，则完成流程
        is_end_node = current_node and current_node.get("type") == "end"
        has_outgoing_edge = False
        
        for edge in edges:
            if edge.get("source") == instance.current_node:
                has_outgoing_edge = True
                break
                
        if is_end_node or not has_outgoing_edge:
            instance.status = "approved"
            instance.complete_time = datetime.now()
            instance.current_handlers = []
        else:
            # 获取下一个节点
            next_node_id = None
            for edge in edges:
                if edge.get("source") == instance.current_node:
                    next_node_id = edge.get("target")
                    break
                    
            if next_node_id:
                instance.current_node = next_node_id
                instance.current_handlers = instance.get_next_handlers(workflow_config)
                
                # 更新状态为processing表示流程在继续
                if instance.status == "pending":
                    instance.status = "processing"
        
        instance.update_time = datetime.now()
        db.commit()
        db.refresh(instance)
        
        logger.info(f"审批通过工作流实例: {instance.id}, 操作人: {operator_id}, 当前状态: {instance.status}")
        return instance
        
    @staticmethod
    def reject(db: Session, instance_id: str, operator_id: str, comment: Optional[str] = None, attachments: Optional[List[Any]] = None) -> WorkflowInstance:
        """拒绝工作流实例
        
        Args:
            db: 数据库会话
            instance_id: 实例ID
            operator_id: 操作人ID
            comment: 审批意见
            attachments: 附件列表
            
        Returns:
            WorkflowInstance: 更新后的工作流实例
        """
        # 获取实例
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance:
            raise ValueError(f"工作流实例不存在: {instance_id}")
            
        # 检查权限：操作人必须在当前处理人列表中
        if instance.current_handlers and operator_id not in instance.current_handlers:
            raise ValueError(f"操作人 {operator_id} 不在当前处理人列表中")
            
        # 获取工作流设计版本
        version = db.query(WorkflowDesignVersion).filter(WorkflowDesignVersion.id == instance.workflow_version_id).first()
        if not version:
            raise ValueError(f"工作流设计版本不存在: {instance.workflow_version_id}")
            
        # 获取工作流配置
        workflow_config = version.workflow_config
        
        # 使用状态机处理状态转换
        pre_status = instance.status
        context = StateContext(instance)
        context.reject()
        
        # 创建审批记录
        record = ApprovalRecord(
            id=str(uuid.uuid4()),
            workflow_instance_id=instance_id,
            node_id=instance.current_node,
            node_name=WorkflowInstanceService._get_node_name(workflow_config, instance.current_node),
            operator_id=operator_id,
            operation="reject",
            comment=comment,
            pre_status=pre_status,
            post_status=instance.status,
            attachments=attachments,
            create_time=datetime.now()
        )
        
        db.add(record)
        
        # 更新实例
        instance.complete_time = datetime.now()
        instance.current_handlers = []
        instance.update_time = datetime.now()
        
        db.commit()
        db.refresh(instance)
        
        logger.info(f"拒绝工作流实例: {instance.id}, 操作人: {operator_id}, 当前状态: {instance.status}")
        return instance
        
    @staticmethod
    def return_to_previous(db: Session, instance_id: str, operator_id: str, comment: Optional[str] = None) -> WorkflowInstance:
        """退回工作流实例到上一节点
        
        Args:
            db: 数据库会话
            instance_id: 实例ID
            operator_id: 操作人ID
            comment: 审批意见
            
        Returns:
            WorkflowInstance: 更新后的工作流实例
        """
        # 获取实例
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance:
            raise ValueError(f"工作流实例不存在: {instance_id}")
            
        # 检查权限：操作人必须在当前处理人列表中
        if instance.current_handlers and operator_id not in instance.current_handlers:
            raise ValueError(f"操作人 {operator_id} 不在当前处理人列表中")
            
        # 获取工作流设计版本
        version = db.query(WorkflowDesignVersion).filter(WorkflowDesignVersion.id == instance.workflow_version_id).first()
        if not version:
            raise ValueError(f"工作流设计版本不存在: {instance.workflow_version_id}")
            
        # 获取工作流配置
        workflow_config = version.workflow_config
        
        # 使用状态机处理状态转换
        pre_status = instance.status
        context = StateContext(instance)
        context.return_to_previous()
        
        # 获取审批记录，按时间倒序
        records = db.query(ApprovalRecord)\
            .filter(ApprovalRecord.workflow_instance_id == instance_id)\
            .order_by(ApprovalRecord.create_time.desc())\
            .all()
            
        # 找到上一个节点（排除当前节点的记录）
        previous_node_id = None
        current_node_id = instance.current_node
        
        for record in records:
            if record.node_id != current_node_id:
                previous_node_id = record.node_id
                break
                
        if not previous_node_id:
            # 如果找不到上一个节点，退回到发起节点
            edges = workflow_config.get("edges", [])
            nodes = workflow_config.get("nodes", [])
            
            # 找到起始节点
            start_node_id = None
            if isinstance(nodes, list):
                for node in nodes:
                    if node.get("type") == "start":
                        start_node_id = node.get("id")
                        break
            elif isinstance(nodes, dict):
                for node_id, node in nodes.items():
                    if node.get("type") == "start":
                        start_node_id = node_id
                        break
                        
            previous_node_id = start_node_id or instance.current_node
        
        # 创建审批记录
        record = ApprovalRecord(
            id=str(uuid.uuid4()),
            workflow_instance_id=instance_id,
            node_id=instance.current_node,
            node_name=WorkflowInstanceService._get_node_name(workflow_config, instance.current_node),
            operator_id=operator_id,
            operation="return",
            comment=comment,
            pre_status=pre_status,
            post_status=instance.status,
            create_time=datetime.now()
        )
        
        db.add(record)
        
        # 更新实例
        instance.current_node = previous_node_id
        
        # 如果退回到起始节点，处理人为发起人
        if workflow_config.get("nodes", {}).get(previous_node_id, {}).get("type") == "start":
            instance.current_handlers = [instance.initiator_id]
        else:
            # 否则获取上一节点的处理人
            previous_handlers = []
            for prev_record in records:
                if prev_record.node_id == previous_node_id:
                    previous_handlers.append(prev_record.operator_id)
                    break
                    
            instance.current_handlers = previous_handlers or [instance.initiator_id]
            
        instance.update_time = datetime.now()
        
        db.commit()
        db.refresh(instance)
        
        logger.info(f"退回工作流实例: {instance.id}, 操作人: {operator_id}, 当前状态: {instance.status}")
        return instance
        
    @staticmethod
    def withdraw(db: Session, instance_id: str, operator_id: str, comment: Optional[str] = None) -> WorkflowInstance:
        """撤回工作流实例
        
        Args:
            db: 数据库会话
            instance_id: 实例ID
            operator_id: 操作人ID
            comment: 撤回原因
            
        Returns:
            WorkflowInstance: 更新后的工作流实例
        """
        # 获取实例
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance:
            raise ValueError(f"工作流实例不存在: {instance_id}")
            
        # 检查权限：只有发起人可以撤回
        if instance.initiator_id != operator_id:
            raise ValueError(f"只有发起人可以撤回工作流实例")
            
        # 获取工作流设计版本
        version = db.query(WorkflowDesignVersion).filter(WorkflowDesignVersion.id == instance.workflow_version_id).first()
        if not version:
            raise ValueError(f"工作流设计版本不存在: {instance.workflow_version_id}")
            
        # 获取工作流配置
        workflow_config = version.workflow_config
        
        # 使用状态机处理状态转换
        pre_status = instance.status
        context = StateContext(instance)
        context.withdraw()
        
        # 创建审批记录
        record = ApprovalRecord(
            id=str(uuid.uuid4()),
            workflow_instance_id=instance_id,
            node_id=instance.current_node,
            node_name=WorkflowInstanceService._get_node_name(workflow_config, instance.current_node),
            operator_id=operator_id,
            operation="withdraw",
            comment=comment,
            pre_status=pre_status,
            post_status=instance.status,
            create_time=datetime.now()
        )
        
        db.add(record)
        
        # 更新实例
        instance.complete_time = datetime.now()
        instance.current_handlers = []
        instance.update_time = datetime.now()
        
        db.commit()
        db.refresh(instance)
        
        logger.info(f"撤回工作流实例: {instance.id}, 操作人: {operator_id}, 当前状态: {instance.status}")
        return instance
        
    @staticmethod
    def get_instance(db: Session, instance_id: str) -> Optional[WorkflowInstance]:
        """获取工作流实例
        
        Args:
            db: 数据库会话
            instance_id: 实例ID
            
        Returns:
            Optional[WorkflowInstance]: 工作流实例或None
        """
        return db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        
    @staticmethod
    def get_instances_by_initiator(db: Session, initiator_id: str, skip: int = 0, limit: int = 100) -> List[WorkflowInstance]:
        """获取用户发起的工作流实例列表
        
        Args:
            db: 数据库会话
            initiator_id: 发起人ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[WorkflowInstance]: 工作流实例列表
        """
        return db.query(WorkflowInstance)\
            .filter(WorkflowInstance.initiator_id == initiator_id)\
            .order_by(WorkflowInstance.create_time.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()
            
    @staticmethod
    def get_instances_by_handler(db: Session, handler_id: str, skip: int = 0, limit: int = 100) -> List[WorkflowInstance]:
        """获取用户需要处理的工作流实例列表
        
        Args:
            db: 数据库会话
            handler_id: 处理人ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[WorkflowInstance]: 工作流实例列表
        """
        # 使用JSON操作符查找current_handlers中包含handler_id的记录
        # 注意：不同数据库的JSON操作符可能不同，这里假设使用PostgreSQL
        return db.query(WorkflowInstance)\
            .filter(
                WorkflowInstance.status.in_(["pending", "processing"]),
                WorkflowInstance.current_handlers.contains([handler_id])
            )\
            .order_by(WorkflowInstance.update_time.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()
            
    @staticmethod
    def get_approval_records(db: Session, instance_id: str) -> List[ApprovalRecord]:
        """获取工作流实例的审批记录
        
        Args:
            db: 数据库会话
            instance_id: 实例ID
            
        Returns:
            List[ApprovalRecord]: 审批记录列表
        """
        return db.query(ApprovalRecord)\
            .filter(ApprovalRecord.workflow_instance_id == instance_id)\
            .order_by(ApprovalRecord.create_time.asc())\
            .all()
            
    @staticmethod
    def _get_node_name(workflow_config: Dict[str, Any], node_id: str) -> Optional[str]:
        """从工作流配置中获取节点名称
        
        Args:
            workflow_config: 工作流配置
            node_id: 节点ID
            
        Returns:
            Optional[str]: 节点名称
        """
        if not workflow_config or not node_id:
            return None
            
        nodes = workflow_config.get("nodes", [])
        
        if isinstance(nodes, list):
            for node in nodes:
                if node.get("id") == node_id:
                    return node.get("name", "未命名节点")
        elif isinstance(nodes, dict):
            node = nodes.get(node_id, {})
            return node.get("name", "未命名节点")
            
        return "未命名节点" 
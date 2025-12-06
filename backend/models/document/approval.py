from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Enum, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base  # 使用相对导入
from sqlalchemy.sql import func

class ApprovalProcess(Base):
    """审批流程定义表"""
    __tablename__ = "approval_processes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False, comment="流程名称")
    code = Column(String(50), unique=True, comment="流程编码")
    description = Column(Text, comment="流程描述")
    config = Column(JSON, comment="流程配置JSON")
    form_schema = Column(JSON, comment="表单定义Schema")
    form_template = Column(String(255), comment="表单模板路径")
    is_active = Column(Boolean, default=True, comment="是否启用")
    version = Column(String(20), comment="版本号")
    business_type = Column(String(50), comment="业务类型") 
    creator_id = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    instances = relationship("ApprovalInstance", back_populates="process")
    policies = relationship("ApprovalPolicy", back_populates="process")
    creator = relationship("User", foreign_keys=[creator_id])
    nodes = relationship("ApprovalNode", back_populates="process", cascade="all, delete-orphan")

class ApprovalInstance(Base):
    """审批流程实例表"""
    __tablename__ = "approval_instances"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("approval_processes.id"), nullable=False)
    title = Column(String(200), nullable=False, comment="审批标题")
    business_id = Column(String(50), comment="关联业务ID")
    initiator_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="发起人ID")
    department_id = Column(Integer, ForeignKey("departments.id"), comment="申请部门ID")
    current_node = Column(String(50), comment="当前节点ID")
    previous_node = Column(String(50), comment="上一节点ID")
    status = Column(Enum("draft", "pending", "processing", "approved", "rejected", "withdrawn", "terminated", name="approval_status"), default="pending", comment="状态")
    form_data = Column(JSON, comment="表单数据")
    emergency_level = Column(Integer, default=0, comment="紧急程度 0-普通 1-紧急 2-特急")
    spend_time = Column(Integer, default=0, comment="审批耗时(秒)")
    logs = Column(JSON, comment="流程日志")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    process = relationship("ApprovalProcess", back_populates="instances")
    nodes = relationship("ApprovalNode", back_populates="instance")
    department = relationship("Department")
    initiator = relationship("User", foreign_keys=[initiator_id])
    histories = relationship("ApprovalHistory", back_populates="instance")

class ApprovalNode(Base):
    """审批节点记录表"""
    __tablename__ = "approval_nodes"
    __table_args__ = (
        UniqueConstraint("process_id", "node_id", name="unique_node_in_process"),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("approval_processes.id"), nullable=False)
    instance_id = Column(Integer, ForeignKey("approval_instances.id"), nullable=True)
    node_id = Column(String(50), nullable=False, comment="节点ID")
    name = Column(String(100), nullable=False, comment="节点名称")
    type = Column(String(50), nullable=False, comment="节点类型：start/approval/condition/end")
    description = Column(Text, comment="节点描述")
    required_position_level = Column(Integer, default=0, comment="需要的职位级别，0表示不限制")
    required_department_level = Column(Integer, default=0, comment="需要的部门级别，0表示不限制")
    allowed_roles = Column(JSON, default=list, comment="允许的角色列表")
    allowed_users = Column(JSON, default=list, comment="允许的用户列表")
    config = Column(JSON, comment="节点配置")
    condition_value = Column(Boolean, nullable=True, comment="条件节点的计算结果")
    is_completed = Column(Boolean, default=False, comment="节点是否已完成")
    status = Column(String(50), default="pending", comment="节点状态：pending/processing/approved/rejected/returned")
    approver = Column(String(100), nullable=True, comment="指定审批人")
    processor = Column(String(100), nullable=True, comment="实际处理人")
    processed_at = Column(DateTime, nullable=True, comment="处理时间")
    comment = Column(Text, nullable=True, comment="处理意见")
    attachment = Column(String(255), nullable=True, comment="附件路径")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    process = relationship("ApprovalProcess", back_populates="nodes")
    instance = relationship("ApprovalInstance", back_populates="nodes")
    
    def evaluate_condition(self, form_data, user_info=None):
        """评估条件节点的值"""
        if self.type != 'condition':
            return None
            
        if not self.config or 'conditions' not in self.config:
            return True  # 没有条件配置则默认为真
            
        conditions = self.config['conditions']
        result = True
        
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator', '==')
            value = condition.get('value')
            
            # 特殊字段处理
            if field == '_user_level' and user_info:
                field_value = user_info.get('position_level', 0)
            elif field == '_department_level' and user_info:
                field_value = user_info.get('department_level', 0)
            elif field in form_data:
                field_value = form_data.get(field)
            else:
                continue  # 字段不存在则跳过
                
            # 条件评估
            if operator == '==':
                condition_result = field_value == value
            elif operator == '!=':
                condition_result = field_value != value
            elif operator == '>':
                condition_result = field_value > value
            elif operator == '>=':
                condition_result = field_value >= value
            elif operator == '<':
                condition_result = field_value < value
            elif operator == '<=':
                condition_result = field_value <= value
            elif operator == 'in':
                condition_result = field_value in value if isinstance(value, list) else False
            else:
                condition_result = False
                
            # 默认条件之间是AND关系
            result = result and condition_result
            
        self.condition_value = result
        return result

class ApprovalHistory(Base):
    """审批历史记录"""
    __tablename__ = "approval_histories"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("approval_instances.id"), nullable=False, comment="流程实例ID")
    node_id = Column(String(50), comment="节点ID")
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, comment="关联文档ID")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="处理人ID")
    action = Column(String(50), nullable=False, comment="操作类型(approve/reject/return/withdraw/create)")
    comment = Column(Text, comment="处理意见")
    form_data_snapshot = Column(JSON, comment="表单数据快照")
    ip_address = Column(String(50), comment="操作IP")
    device_info = Column(String(200), comment="设备信息")
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联关系
    document = relationship("Document", back_populates="approval_histories")
    approver = relationship("User", back_populates="approval_histories")
    instance = relationship("ApprovalInstance", back_populates="histories")

class ApprovalTemplate(Base):
    """审批流程模板"""
    __tablename__ = "approval_templates"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="模板名称")
    description = Column(Text, comment="模板描述")
    config = Column(JSON, nullable=False, comment="流程配置JSON")
    form_schema = Column(JSON, comment="表单定义Schema")
    creator_id = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    business_type = Column(String(50), comment="业务类型")
    is_system = Column(Boolean, default=False, comment="是否系统预设模板")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    creator = relationship("User", foreign_keys=[creator_id])

class ApprovalPolicy(Base):
    """审批策略表"""
    __tablename__ = "approval_policies"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("approval_processes.id"), nullable=False)
    name = Column(String(100), nullable=False, comment="策略名称")
    description = Column(Text, comment="策略描述")
    conditions = Column(JSON, comment="适用条件JSON")
    actions = Column(JSON, comment="执行动作JSON")
    priority = Column(Integer, default=0, comment="优先级，数字越大优先级越高")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    process = relationship("ApprovalProcess", back_populates="policies")
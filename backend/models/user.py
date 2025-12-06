from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Table, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import sqlalchemy
import sys

# 修改为相对导入
from .base import Base

# 删除重复和错误的导入
# from backend.models.base import Base  # 删除这行

# 清除User类的冲突定义
for key in list(Base.registry._class_registry.keys()):
    if "User" in key or "Role" in key:
        del Base.registry._class_registry[key]

# 定义用户角色关联表
user_role = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    extend_existing=True
)

class User(Base):
    """用户表"""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}  # 添加这行解决表重复定义问题
    __module__ = "backend.models.user"  # 显式指定完整模块路径

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    real_name = Column(String(100), nullable=True)
    hashed_password = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    position_level = Column(Integer, default=0, comment="职位级别，数字越小级别越高，1表示最高级别")
    department_level = Column(Integer, default=0, comment="部门级别，数字越小级别越高，1表示最高级别")
    approval_limit = Column(JSON, default=dict, comment="审批权限限制，比如{'leave': {'days': 2, 'level': 1}}表示请假审批权限为2天，且仅限1级审批")
    avatar = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login = Column(DateTime, nullable=True)

    # 修改关联关系定义
    department = relationship("Department", 
                            foreign_keys=[department_id],
                            primaryjoin="User.department_id == Department.id",
                            back_populates="users")
    position = relationship("Position", 
                          foreign_keys=[position_id],
                          primaryjoin="User.position_id == Position.id",
                          back_populates="users")
    
    # 添加与文档的关系
    documents = relationship("Document", back_populates="owner", foreign_keys="Document.owner_id")
    
    roles = relationship("Role", secondary=user_role, back_populates="users")
    managed_departments = relationship("Department", 
                                    primaryjoin="User.id == Department.manager_id",
                                    back_populates="manager")
    
    approval_histories = relationship("ApprovalHistory", back_populates="approver")
    
    def __str__(self):
        return f"User(id={self.id}, username={self.username})"
        
    def _get_position_level(self):
        """获取用户的职位等级"""
        if self.position:
            return self.position.level
        return 0
        
    def _get_department_level(self):
        """获取用户的部门等级"""
        if self.department:
            return self.department.level
        return 0
        
    @property
    def permissions(self):
        """获取用户的所有权限"""
        perms = set()
        for role in self.roles:
            for permission in role.permissions:
                perms.add(f"{permission.resource}:{permission.action}")
        return list(perms)
        
    @property
    def is_manager(self):
        """判断用户是否是管理者"""
        if self.position and self.position.is_management:
            return True
        if self.managed_departments:
            return True
        return False
        
    @property
    def can_approve(self):
        """判断用户是否有审批权限"""
        if self.is_admin or self.is_manager:
            return True
        for role in self.roles:
            if any("approve" in perm.action for perm in role.permissions):
                return True
        return False
        
    def can_approve_workflow(self, workflow_type, node_config=None, form_data=None):
        """判断用户是否可以审批特定流程
        
        Args:
            workflow_type: 流程类型，如 'leave'、'expense' 等
            node_config: 当前节点配置
            form_data: 表单数据，用于条件判断
        
        Returns:
            bool: 是否有权限审批
        """
        # 管理员始终有权限
        if self.is_admin:
            return True
            
        # 检查是否是特定审批人
        if node_config and 'approvers' in node_config:
            if self.id in node_config['approvers']:
                return True
                
        # 检查职位级别要求
        if node_config and 'required_position_level' in node_config:
            required_level = node_config['required_position_level']
            if self.position_level > 0 and self.position_level <= required_level:
                # 职位级别满足要求
                
                # 检查审批限制
                if workflow_type in self.approval_limit:
                    limit_config = self.approval_limit[workflow_type]
                    
                    # 如果是请假审批，检查天数限制
                    if workflow_type == 'leave' and form_data and 'days' in form_data:
                        if form_data['days'] <= limit_config.get('days', 0):
                            return True
                        # 如果天数超过限制但用户级别足够高
                        if 'level' in limit_config and self.position_level <= limit_config['level']:
                            return True
                    # 其他类型流程的限制条件
                    elif 'level' in limit_config and self.position_level <= limit_config['level']:
                        return True
                else:
                    # 没有特定限制，只按职位级别判断
                    return True
                    
        # 检查部门级别要求
        if node_config and 'required_department_level' in node_config:
            required_level = node_config['required_department_level']
            if self.department_level > 0 and self.department_level <= required_level:
                return True
                
        # 检查角色要求
        if node_config and 'allowed_roles' in node_config:
            user_roles = [role.name for role in self.roles]
            if any(role in node_config['allowed_roles'] for role in user_roles):
                return True
                
        return False 

# 角色模型
class Role(Base):
    """角色模型"""
    __module__ = "backend.models.user"
    __tablename__ = "roles"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    permissions_text = Column(Text, name="permissions")  # 改名为permissions_text，但数据库中仍为permissions
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系定义
    users = relationship("User", secondary=user_role, back_populates="roles")
    
    def __repr__(self):
        return f"<Role {self.name}>"
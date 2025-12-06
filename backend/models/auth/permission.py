from sqlalchemy import Column, Integer, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import Base

# 角色-权限关联表
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

class Permission(Base):
    """权限表"""
    __tablename__ = "permissions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    resource = Column(String(50), nullable=False)  # 资源，如user, role, document
    action = Column(String(50), nullable=False)    # 操作，如create, read, update, delete
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系定义移至关系初始化函数

    def __repr__(self):
        return f"<Permission {self.name}>"

# 避免循环导入，在外部初始化关系
def initialize_relationships():
    from models.auth.role import RoleAuth
    Permission.roles = relationship(
        "RoleAuth",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="joined"
    )
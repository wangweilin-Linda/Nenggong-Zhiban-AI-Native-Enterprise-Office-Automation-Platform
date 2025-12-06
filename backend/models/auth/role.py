from sqlalchemy import Column, Integer, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import Base

class RoleAuth(Base):
    """角色权限表"""
    __tablename__ = "roles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    permissions_text = Column(Text, name="permissions")  # 与user.py保持一致
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系定义移至关系初始化函数

    def __repr__(self):
        return f"<Role {self.name}>"

# 避免循环导入，在外部初始化关系
def initialize_relationships():
    from models.auth.permission import Permission, role_permissions
    RoleAuth.users = relationship("User", secondary="user_roles", lazy="joined")
    RoleAuth.permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="joined"
    )
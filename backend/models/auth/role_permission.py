from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base

class RolePermission(Base):
    """角色权限关联表"""
    __tablename__ = "role_permissions"
    __table_args__ = {'extend_existing': True}

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now()) 
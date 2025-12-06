from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base

class UserRole(Base):
    """用户角色关联表"""
    __tablename__ = "user_roles"
    __table_args__ = {'extend_existing': True}

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now()) 
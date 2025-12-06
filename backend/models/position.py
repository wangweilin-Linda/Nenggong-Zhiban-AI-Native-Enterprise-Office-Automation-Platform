from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

# 清除Position类的冲突定义
for key in list(Base.registry._class_registry.keys()):
    if "Position" in key:
        del Base.registry._class_registry[key]

class Position(Base):
    """职位模型"""
    __module__ = "backend.models.position"
    __tablename__ = "positions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, unique=True)
    code = Column(String(50), unique=True)
    level = Column(Integer, default=0)  # 职位级别，0为最高级
    sort_order = Column(Integer, default=0)  # 排序顺序
    is_active = Column(Boolean, default=True)
    is_management = Column(Boolean, default=False)  # 是否为管理岗位
    description = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系定义 - 使用完全限定路径
    departments = relationship("Department", 
                              secondary="department_position",
                              back_populates="positions")
    users = relationship("User", back_populates="position")
    
    def __repr__(self):
        return f"<Position {self.name}>"
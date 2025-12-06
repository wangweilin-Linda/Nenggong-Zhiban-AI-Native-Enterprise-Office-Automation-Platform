from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Table
from sqlalchemy.orm import relationship
from models.base import Base  # 修改这行，删除 backend 前缀
from datetime import datetime

# 清除Department类的冲突定义
for key in list(Base.registry._class_registry.keys()):
    if "Department" in key or "DepartmentPosition" in key:
        del Base.registry._class_registry[key]

# 显式定义关联表，使用完全限定路径
department_position = Table(
    "department_position",
    Base.metadata,
    Column("department_id", Integer, ForeignKey("departments.id"), primary_key=True),
    Column("position_id", Integer, ForeignKey("positions.id"), primary_key=True),
    extend_existing=True
)

# 重新定义Department类
class Department(Base):
    """部门模型"""
    __module__ = "backend.models.department"
    __tablename__ = "departments"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, unique=True)
    code = Column(String(50), unique=True)
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    level = Column(Integer, default=0)  # 部门级别，0为最高级
    sort_order = Column(Integer, default=0)  # 排序顺序
    is_active = Column(Boolean, default=True)
    description = Column(String(200))
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系定义
    parent = relationship("Department", remote_side=[id], back_populates="children")
    children = relationship("Department", back_populates="parent")
    positions = relationship("Position", secondary=department_position, back_populates="departments")
    users = relationship("User", back_populates="department", foreign_keys="User.department_id")
    manager = relationship("User", foreign_keys=[manager_id])
    
    def __repr__(self):
        return f"<Department {self.name}>"

# 定义DepartmentPosition类
class DepartmentPosition(Base):
    """部门职位关联模型"""
    __module__ = "backend.models.department"
    __tablename__ = "department_position_relations"
    __table_args__ = {'extend_existing': True}
    
    department_id = Column(Integer, ForeignKey("departments.id"), primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id"), primary_key=True)
    is_default = Column(Boolean, default=False)  # 是否为默认职位
    
    # 关系定义
    department = relationship("Department")
    position = relationship("Position")
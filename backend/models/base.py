from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
import re

# 定义命名约定
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": 'uq_%(table_name)s_%(column_0_name)s',
    "ck": 'ck_%(table_name)s_%(constraint_name)s',
    "fk": 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    "pk": 'pk_%(table_name)s'
}

# 创建元数据对象
metadata = MetaData(naming_convention=convention)

# 创建基类，设置元数据
Base = declarative_base(metadata=metadata)

# 防止模型类冲突，清理旧的模型定义
def clear_model_registry(model_name):
    """清理注册表中特定模型的引用，避免'Multiple classes found for path'错误"""
    model_keys = []
    for key in list(Base.registry._class_registry.keys()):
        if isinstance(key, str) and model_name in key:
            model_keys.append(key)
    
    for key in model_keys:
        del Base.registry._class_registry[key]

# 初始化时清理常见冲突模型
clear_model_registry("Department")
clear_model_registry("User")
clear_model_registry("Position")
clear_model_registry("Role")

# 设置所有表的默认属性
def _declarative_constructor(self, **kwargs):
    """自定义构造函数，处理关键字参数"""
    for key, value in kwargs.items():
        if hasattr(self.__class__, key):
            setattr(self, key, value)

Base.__init__ = _declarative_constructor

# 重写__table_args__
class _Base:
    # 默认表参数，所有模型都会有extend_existing=True
    __table_args__ = {
        'extend_existing': True,
        'sqlite_autoincrement': True
    }

# 使Base继承_Base类的属性，这样所有模型都会自动获得extend_existing=True
for name, attr in _Base.__dict__.items():
    if not name.startswith('__') or name == '__table_args__':
        setattr(Base, name, attr)

class BaseModel(Base):
    """基础模型类，包含通用字段"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
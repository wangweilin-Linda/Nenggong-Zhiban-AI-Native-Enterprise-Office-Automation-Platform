from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import json
import uuid

from ..base import Base  # 使用相对导入
from ..user import User  # 使用相对导入

class WorkflowDesign(Base):
    """工作流设计模型"""
    __tablename__ = "workflow_designs"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, comment="工作流名称")
    description = Column(Text, nullable=True, comment="工作流描述")
    workflow_config = Column(JSON, nullable=True, comment="工作流配置(JSON格式)")
    diagram = Column(Text, nullable=True, comment="工作流图表(Mermaid格式)")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建者ID")
    is_published = Column(Boolean, default=False, comment="是否已发布")
    published_template_id = Column(String(36), nullable=True, comment="发布后的模板ID")
    version = Column(Integer, default=1, comment="版本号")
    parent_id = Column(String(36), ForeignKey("workflow_designs.id"), nullable=True, comment="父设计ID")
    design_prompt = Column(Text, nullable=True, comment="设计提示")
    design_feedback = Column(Text, nullable=True, comment="设计反馈")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系
    creator = relationship("User", foreign_keys=[created_by])
    parent = relationship("WorkflowDesign", remote_side=[id], backref="children")
    versions = relationship("WorkflowDesignVersion", back_populates="design", cascade="all, delete-orphan")

    def save(self):
        """保存当前设计到数据库"""
        from database.session import get_db_session
        try:
            session = next(get_db_session())
            session.add(self)
            session.commit()
            session.refresh(self)
            return self
        except Exception as e:
            session.rollback()
            raise e

    @classmethod
    def get_by_id(cls, design_id):
        """通过ID获取设计"""
        from database.session import get_db_session
        try:
            session = next(get_db_session())
            return session.query(cls).filter(cls.id == design_id).first()
        except Exception as e:
            raise e

    @classmethod
    def get_by_user(cls, user_id):
        """获取用户创建的所有设计"""
        from database.session import get_db_session
        try:
            session = next(get_db_session())
            return session.query(cls).filter(cls.created_by == user_id).all()
        except Exception as e:
            raise e

    @classmethod
    def get_published(cls):
        """获取所有已发布的设计"""
        from database.session import get_db_session
        try:
            session = next(get_db_session())
            return session.query(cls).filter(cls.is_published == True).all()
        except Exception as e:
            raise e


class WorkflowDesignVersion(Base):
    """工作流设计历史记录"""
    __tablename__ = "workflow_design_histories"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_id = Column(String(36), ForeignKey("workflow_designs.id"), nullable=False, comment="设计ID")
    version = Column(Integer, nullable=False, comment="版本号")
    workflow_config = Column(JSON, nullable=True, comment="工作流配置(JSON格式)")
    diagram = Column(Text, nullable=True, comment="工作流图表(Mermaid格式)")
    change_description = Column(Text, nullable=True, comment="变更描述")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建者ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    # 关系
    design = relationship("WorkflowDesign", back_populates="versions")
    creator = relationship("User", foreign_keys=[created_by])

    def save(self):
        """保存历史记录到数据库"""
        from database.session import get_db_session
        try:
            session = next(get_db_session())
            session.add(self)
            session.commit()
            session.refresh(self)
            return self
        except Exception as e:
            session.rollback()
            raise e

    @classmethod
    def get_versions(cls, design_id):
        """获取设计的所有历史版本"""
        from database.session import get_db_session
        try:
            session = next(get_db_session())
            return session.query(cls).filter(cls.design_id == design_id).order_by(cls.version.desc()).all()
        except Exception as e:
            raise e 
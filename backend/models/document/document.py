from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base  # 使用相对导入
import enum
from datetime import datetime

class DocumentStatus(enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    ARCHIVED = "archived"

class DocumentType(Base):
    """文档类型表"""
    __tablename__ = "document_types"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联关系
    documents = relationship("Document", back_populates="document_type")

class Document(Base):
    """文档表"""
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)
    type_id = Column(Integer, ForeignKey("document_types.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("document_categories.id"), nullable=True)
    is_public = Column(Boolean, default=False)
    can_comment = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联关系
    owner = relationship("User", back_populates="documents")
    document_type = relationship("DocumentType", back_populates="documents")
    category = relationship("DocumentCategory", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    comments = relationship("DocumentComment", back_populates="document", cascade="all, delete-orphan")
    attachments = relationship("DocumentAttachment", back_populates="document", cascade="all, delete-orphan")
    # 添加缺失的审批历史关系
    approval_histories = relationship("ApprovalHistory", back_populates="document")

class DocumentCategory(Base):
    """文档分类表"""
    __tablename__ = "document_categories"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    parent_id = Column(Integer, ForeignKey("document_categories.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联关系
    documents = relationship("Document", back_populates="category")
    children = relationship("DocumentCategory", backref="parent", remote_side=[id])

class DocumentAttachment(Base):
    """文档附件表"""
    __tablename__ = "document_attachments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    # 关联关系
    document = relationship("Document", back_populates="attachments")

class DocumentComment(Base):
    """文档评论表"""
    __tablename__ = "document_comments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # 关联关系
    document = relationship("Document", back_populates="comments")
    user = relationship("User")

class DocumentVersion(Base):
    """文档版本表"""
    __tablename__ = "document_versions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    version = Column(Integer, default=1)
    content = Column(Text)
    changes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())

    # 关联关系
    document = relationship("Document", back_populates="versions")
    creator = relationship("User")
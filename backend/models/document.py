"""
这个文件已弃用，使用models/document/document.py中的Document模型。
保留此文件仅为兼容性，通过重定向导入正确的模型。
"""

# 直接从document/document.py导入
from .document.document import Document, DocumentStatus, DocumentType, DocumentCategory, DocumentAttachment, DocumentComment, DocumentVersion

# 导出所有需要的模型
__all__ = ['Document', 'DocumentStatus', 'DocumentType', 'DocumentCategory', 'DocumentAttachment', 'DocumentComment', 'DocumentVersion'] 
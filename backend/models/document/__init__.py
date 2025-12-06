# Empty init file

# 导入必要的模型
from .document import Document, DocumentCategory
from .approval import ApprovalProcess, ApprovalInstance, ApprovalNode, ApprovalHistory
from .workflow_design import WorkflowDesign, WorkflowDesignVersion

# 注意：organization.py中的模型已被禁用，请改用backend/models/department.py和position.py

__all__ = [
    'Document',
    'DocumentCategory',
    'ApprovalProcess',
    'ApprovalInstance',
    'ApprovalNode', 
    'ApprovalHistory',
    'WorkflowDesign',
    'WorkflowDesignVersion'
]

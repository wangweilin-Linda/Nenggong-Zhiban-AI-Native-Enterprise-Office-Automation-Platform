import sys
import os

# 加载项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 导入基本类
from .base import Base
from database import engine

# 通过修改导入顺序来解决循环依赖问题
# 1. 先导入基础模型和用户模型
from .user import User
from .department import Department
from .position import Position

# 2. 然后导入权限相关模型
from .auth.role import RoleAuth
from .auth.permission import Permission
from .auth.role_permission import RolePermission
from .auth.user_role import UserRole

# 3. 最后导入文档和工作流模型
from .document.document import Document, DocumentStatus, DocumentType, DocumentVersion, DocumentComment, DocumentAttachment
from .document.workflow_design import WorkflowDesign, WorkflowDesignVersion
from .document.approval import ApprovalProcess, ApprovalInstance, ApprovalHistory, ApprovalNode

# 配置所有表的extend_existing=True以避免重复定义错误
for table in Base.metadata.tables.values():
    table.extend_existing = True

# 确保权限相关表正确初始化
Permission.__table__.extend_existing = True
RoleAuth.__table__.extend_existing = True
RolePermission.__table__.extend_existing = True
UserRole.__table__.extend_existing = True

# 确保所有模型定义都已导入，然后初始化关系
def initialize_model_relationships():
    """
    初始化模型之间的关系
    注意：这个函数应该在所有模型导入后调用
    """
    print("初始化模型关系...")
    
    # 确保所有模型类已正确加载
    models = [RoleAuth, Permission, User, Department, Position, Document, 
              DocumentType, DocumentVersion, DocumentComment, DocumentAttachment,
              ApprovalProcess, ApprovalInstance, ApprovalHistory, ApprovalNode]
    print(f"已加载 {len(models)} 个模型类")
    
    # 显式配置registry，解决关系映射问题
    from sqlalchemy.orm import configure_mappers
    try:
        # 调用configure_mappers确保所有映射器配置正确
        configure_mappers()
        print("所有映射器配置成功")
    except Exception as e:
        print(f"配置映射器时出错: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    # 验证关键关系
    try:
        # 检查User.documents关系
        assert hasattr(User, 'documents'), "User没有documents关系"
        # 检查Document.owner关系
        assert hasattr(Document, 'owner'), "Document没有owner关系"
        # 检查Document.approval_histories关系
        assert hasattr(Document, 'approval_histories'), "Document没有approval_histories关系"
        # 检查Document.versions关系
        assert hasattr(Document, 'versions'), "Document没有versions关系"
        print("关键模型关系验证通过")
    except AssertionError as e:
        print(f"模型关系验证失败: {e}")
        raise
    
    return True

# 导出模型和初始化函数
__all__ = [
    'Base', 'engine', 'User', 'RoleAuth', 'Permission',
    'Document', 'DocumentStatus', 'DocumentType', 'DocumentVersion', 'DocumentComment', 'DocumentAttachment',
    'WorkflowDesign', 'WorkflowDesignVersion',
    'Department', 'Position', 'ApprovalProcess', 'ApprovalInstance',
    'ApprovalNode', 'ApprovalHistory', 'initialize_model_relationships'
]
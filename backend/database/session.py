from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
from dotenv import load_dotenv
# 正确导入Base
from models.base import Base
import database

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 加载环境变量（只从根目录加载）
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
load_dotenv(dotenv_path)

# 获取数据库URL，如果不存在则使用SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./oa.db")
print(f"使用数据库连接: {DATABASE_URL}")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 添加初始化数据库函数
def init_db():
    try:
        # 导入所有模型以确保它们被注册
        print("正在注册数据库模型...")
        
        # 导入用户和权限模型
        from backend.models.auth.permission import Permission
        from backend.models.auth.role import Role
        from backend.models.user import User
        from backend.models.auth.user_role import UserRole
        # 导入部门和职位模型
        from backend.models.department import Department, DepartmentPosition
        from backend.models.position import Position
        print("用户和权限模型已注册")
        
        # 导入文档相关模型
        from backend.models.document.document import Document, DocumentCategory
        from backend.models.document.workflow_design import WorkflowDesign, WorkflowDesignVersion
        from backend.models.document.approval import ApprovalProcess, ApprovalInstance, ApprovalNode, ApprovalHistory
        print("文档相关模型已注册")
        
        # 创建所有表
        print("创建数据库表...")
        Base.metadata.create_all(bind=engine)
        
        # 配置映射器关系
        from sqlalchemy.orm import configure_mappers
        try:
            configure_mappers()
            print("所有映射器关系配置成功")
        except Exception as e:
            print(f"配置映射器关系时出错: {e}")
            import traceback
            traceback.print_exc()
            
        print("数据库初始化完成")
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
        raise

# 创建数据库引擎和session
get_db_session = get_db
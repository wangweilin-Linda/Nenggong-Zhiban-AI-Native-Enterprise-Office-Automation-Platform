import os
import sys
import importlib
import inspect
import pkgutil
from sqlalchemy import text
from datetime import datetime
from passlib.context import CryptContext

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from sqlalchemy import inspect as sa_inspect, MetaData
from backend.models.base import Base
from backend.database.session import engine, init_db, get_db

# 密码哈希工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def reset_database():
    """
    重置数据库：删除所有表并重新创建
    """
    try:
        # 清理元数据缓存，避免表重复定义错误
        Base.metadata.clear()
        
        # 清理当前数据库连接中的表
        inspector = sa_inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # 以事务方式执行
        connection = engine.connect()
        transaction = connection.begin()
        
        try:
            # 禁用外键约束（SQLite特性）
            connection.execute(text("PRAGMA foreign_keys = OFF"))
            
            # 先删除所有存在的表
            print(f"正在删除已存在的表: {existing_tables}")
            for table_name in existing_tables:
                connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            
            # 提交删除操作
            transaction.commit()
        except Exception as e:
            transaction.rollback()
            print(f"删除表失败: {str(e)}")
            raise
        finally:
            connection.close()
        
        # 重新导入所有模型，确保它们被正确注册到元数据中
        print("正在重新注册模型...")
        import_all_models()
        
        # 创建所有表
        print("正在重新创建数据库表...")
        Base.metadata.create_all(bind=engine)
        print("数据库表创建完成")
        
        # 表创建完成后，创建初始管理员账户
        try:
            create_admin_user()
        except Exception as e:
            print(f"创建管理员用户失败: {str(e)}")
            # 继续执行，不因为创建用户失败而影响整个初始化流程
        
        print("数据库重置完成！")
    except Exception as e:
        print(f"数据库重置失败: {str(e)}")
        import traceback
        traceback.print_exc()

def create_admin_user():
    """创建管理员用户"""
    print("正在创建管理员用户...")
    
    # 直接使用引擎执行SQL，确保表存在
    with engine.connect() as conn:
        # 检查users表是否存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
        if not result.first():
            print("users表不存在，跳过创建管理员用户")
            return
        
        # 检查admin用户是否已存在
        admin_exists = conn.execute(text("SELECT id FROM users WHERE username = 'admin'")).first()
        
        if not admin_exists:
            # 生成密码哈希
            hashed_password = pwd_context.hash("admin")
            
            # 插入admin用户
            conn.execute(
                text("""
                INSERT INTO users (username, email, hashed_password, real_name, is_admin, created_at, updated_at) 
                VALUES (:username, :email, :password, :real_name, :is_admin, :created_at, :updated_at)
                """), 
                {
                    "username": "admin",
                    "email": "admin@example.com",
                    "password": hashed_password,
                    "real_name": "系统管理员",
                    "is_admin": True,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            )
            conn.commit()
            print("管理员用户创建成功")
        else:
            print("管理员用户已存在")

def import_all_models():
    """以正确的顺序导入所有模型并检查导入是否成功"""
    try:
        # 清理所有模型的注册缓存
        for cls_name in list(Base.registry._class_registry):
            if isinstance(cls_name, str) and not cls_name.startswith('_'):
                del Base.registry._class_registry[cls_name]
        
        # 按顺序导入和注册基础模型
        from backend.models.user import User
        print(f"已注册User模型，表名: {User.__tablename__}")
        
        from backend.models.department import Department
        print(f"已注册Department模型，表名: {Department.__tablename__}")
        
        from backend.models.position import Position
        print(f"已注册Position模型，表名: {Position.__tablename__}")
        
        # 导入其他模型
        try:
            from backend.models.auth.role import Role
            print(f"已注册Role模型，表名: {Role.__tablename__}")
        except Exception as e:
            print(f"导入Role模型失败: {str(e)}")
        
        try:
            from backend.models.auth.permission import Permission
            print(f"已注册Permission模型，表名: {Permission.__tablename__}")
        except Exception as e:
            print(f"导入Permission模型失败: {str(e)}")
        
        try:
            from backend.models.auth.user_role import UserRole
            print(f"已注册UserRole模型，表名: {UserRole.__tablename__}")
        except Exception as e:
            print(f"导入UserRole模型失败: {str(e)}")
        
        try:
            from backend.models.document.document import Document
            print(f"已注册Document模型，表名: {Document.__tablename__}")
        except Exception as e:
            print(f"导入Document模型失败: {str(e)}")
        
        # 在这里导入其他模型...
        
        # 列出所有已注册的模型
        print("\n已注册的所有模型:")
        for cls_name, cls in Base.registry._class_registry.items():
            if isinstance(cls_name, str) and not cls_name.startswith('_'):
                try:
                    print(f"- {cls_name}: 表名 {cls.__tablename__}")
                except:
                    print(f"- {cls_name}")
                    
    except Exception as e:
        print(f"导入模型失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reset_database()

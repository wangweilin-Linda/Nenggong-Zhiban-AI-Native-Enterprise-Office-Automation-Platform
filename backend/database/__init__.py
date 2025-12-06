# 数据库包初始化文件 
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time

# 创建数据库引擎
SQLALCHEMY_DATABASE_URL = "sqlite:///./oa.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 保留get_session函数以兼容旧代码
def get_session():
    """获取数据库会话（同步版本）"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# 数据库初始化状态
_db_initialized = False

def init_db(force_recreate=False):
    """初始化数据库，确保只执行一次"""
    global _db_initialized
    
    if _db_initialized and not force_recreate:
        print("数据库已初始化，跳过")
        return
    
    print("初始化数据库...")
    
    # 如果force_recreate为True，尝试删除现有数据库文件
    if force_recreate:
        try:
            db_file = "oa.db"
            if os.path.exists(db_file):
                print(f"删除现有数据库文件: {db_file}")
                for attempt in range(3):  # 尝试3次
                    try:
                        os.remove(db_file)
                        print("数据库文件已删除")
                        break
                    except PermissionError:
                        print(f"文件被占用，等待解锁... (尝试 {attempt+1}/3)")
                        time.sleep(1)  # 等待1秒后重试
                    except Exception as e:
                        print(f"删除数据库文件失败: {e}")
                        break
        except Exception as e:
            print(f"处理数据库文件时出错: {e}")
    
    try:
        # 创建所有表
        print("创建数据库表结构...")
        Base.metadata.create_all(bind=engine)
        print("数据库表结构创建完成")
        _db_initialized = True
    except Exception as e:
        print(f"创建数据库表结构失败: {e}")
        import traceback
        traceback.print_exc()

def setup_db():
    """设置数据库，确保表结构和基础数据存在"""
    init_db(force_recreate=False)
    print("数据库设置完成")

# 打印一条消息表示包已加载
print("Database package initialized.") 
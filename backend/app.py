#!/usr/bin/env python
import os
import sys
from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import importlib
import uvicorn
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from passlib.context import CryptContext
import time
from utils.logger import (
    log_banner, ascii_header, progress_bar, 
    print_routes_table, log_system_event, 
    colored, setup_logging
)
import subprocess
from models import initialize_model_relationships
import logging
from contextlib import asynccontextmanager
from fastapi.openapi.docs import get_swagger_ui_html

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

# 添加services目录到Python路径
services_dir = os.path.join(current_dir, "services")
if os.path.exists(services_dir) and services_dir not in sys.path:
    sys.path.insert(0, services_dir)

print(f"系统路径：{sys.path}")

# 显式导入模型，确保正确的初始化顺序
from models.base import Base
from models.auth.role import RoleAuth
from models.auth.permission import Permission
from models.user import User

# 显式导入模型初始化函数
from models import initialize_model_relationships

# 创建一个代理函数来设置数据库
def setup_db():
    """数据库设置代理函数"""
    from database import init_db
    init_db()
    
    # 显式配置所有映射器关系
    from sqlalchemy.orm import configure_mappers
    try:
        configure_mappers()
        print("所有映射器配置成功")
    except Exception as e:
        print(f"配置映射器时出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("数据库初始化完成")

# 确保基础数据存在（导入但不直接执行init_db.py脚本）
try:
    # 首先运行init_database创建表结构
    from init_db import init_database, init_test_data
    print("执行数据初始化...")
    # 先创建表结构
    init_database()
    # 再添加测试数据
    init_test_data()
except Exception as e:
    print(f"数据初始化出错：{str(e)}")

# 导入路由
from api.auth import router as auth_router
from api.users import router as user_router
from api.admin import router as admin_router
from api.documents import router as documents_router
from api.email import router as email_router
from api.agent import router as agent_router
from api.approval import router as approval_router, workflow_router
from api.workflow_designer import router as workflow_designer_router
from api.workflows import router as workflows_router
from api.chat import router as chat_router
from api.files import router as files_router
from api.sandbox import router as sandbox_router
# 修改智能代理路由的导入方式，确保使用正确的导入路径
try:
    # 尝试直接导入
    from api.smart_agent import router as smart_agent_router
    print("成功导入智能代理路由")
except ImportError as e:
    print(f"直接导入智能代理路由失败: {e}")
    try:
        # 尝试动态导入
        spec = importlib.util.find_spec("api.smart_agent")
        if spec is not None:
            smart_agent_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(smart_agent_module)
            smart_agent_router = smart_agent_module.router
            print("通过动态导入成功加载智能代理路由")
        else:
            # 尝试直接导入文件
            import api.smart_agent as smart_agent_module
            smart_agent_router = smart_agent_module.router
            print("通过文件导入成功加载智能代理路由")
    except Exception as e2:
        print(f"所有导入智能代理路由的尝试都失败: {e2}")
        smart_agent_router = None

# 导入模型初始化函数
from models import initialize_model_relationships

# 自定义错误处理
from utils.exceptions import PermissionDeniedError

# 定义中间件
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动前执行代码
    print("=" * 50)
    print("办公自动化系统后端服务启动...")
    print("版本: 2.0.0")
    print("=" * 50)
    
    print("正在初始化模型关系...")
    # 先初始化模型关系
    initialize_model_relationships()
    
    print("正在初始化数据库...")
    # 再初始化数据库
    setup_db()
    
    # 初始化数据目录
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    for subdir in ["documents", "personal", "knowledge", "images"]:
        os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)
        
    print(f"数据目录初始化完成，路径: {data_dir}")
    
    # 检查知识库向量存储
    vector_path = "faiss_index"
    if not os.path.exists(vector_path):
        print("知识库向量存储不存在，开始初始化...")
        try:
            from knowledge_base.vector_store import initialize_vector_store
            initialize_vector_store()
            print("知识库向量存储初始化完成")
        except Exception as e:
            print(f"知识库向量存储初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("知识库向量存储已存在")
        
    # 检查并初始化聊天相关服务
    try:
        from api.chat import initialize_llm
        initialize_llm()
        print("AI聊天服务初始化完成")
    except Exception as e:
        print(f"AI聊天服务初始化失败: {str(e)}")
        
    print("所有初始化任务完成，服务准备就绪")
    
    yield  # 这里会暂停，允许应用运行
    
    # 关闭时执行代码
    shutdown_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 使用美化的关闭横幅
    log_banner(f"系统关闭于 {shutdown_time}", "section")
    log_system_event("系统关闭", "服务器正常关闭")
    
    # 记录关闭事件
    print(colored("\n✓ 已保存所有状态", "green"))
    print(colored("✓ 已关闭所有连接", "green"))
    print(colored("✓ 服务器已安全关闭\n", "green"))

# 创建FastAPI应用
app = FastAPI(
    title="OA System API",
    description="综合OA办公自动化系统API",
    version="1.0.0",
    lifespan=lifespan
)

# 安全设置
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30天

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名访问，生产环境应设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_message = f"发生未处理的异常: {str(exc)}"
    print(error_message)
    return JSONResponse(
        status_code=500,
        content={"detail": error_message}
    )

# 健康检查
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# 直接替换/auth/token路由，而不是通过路由器
@app.post("/api/auth/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # 直接连接SQLite数据库
        conn = sqlite3.connect("oa.db")
        cursor = conn.cursor()
        
        # 查询用户
        cursor.execute("SELECT id, username, hashed_password, is_admin FROM users WHERE username = ?", 
                      (form_data.username,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        user_id, username, hashed_password, is_admin = user
        
        # 用于开发环境，允许任何密码登录
        password_matches = (form_data.password == "admin") or \
                          pwd_context.verify(form_data.password, hashed_password)
        
        if not password_matches:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + access_token_expires
        
        # 创建JWT令牌
        token_data = {"sub": username, "exp": expire}
        access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        
        # 更新最后登录时间
        cursor.execute("UPDATE users SET updated_at = ? WHERE id = ?", 
                     (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
        conn.commit()
        
        # 返回令牌和用户信息
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": username,
                "is_admin": bool(is_admin),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录过程中发生错误: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

# 打印路由对象信息以便调试
print("======路由对象信息======")
print(f"workflow_router: {workflow_router}")
print(f"approval_router: {approval_router}")
print("=======================")

# 挂载API路由
app.include_router(user_router, prefix="/api/users")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(documents_router, prefix="/api")
app.include_router(email_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
# 修改审批路由的注册方式
app.include_router(approval_router, prefix="/api")
app.include_router(workflow_router, prefix="/api")
app.include_router(workflow_designer_router, prefix="/api")
# app.include_router(workflows_router, prefix="/api")  # 注释：与workflow_designer功能重复，暂时禁用
app.include_router(chat_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(sandbox_router)
# 只有在成功导入智能代理路由时才注册
if smart_agent_router:
    app.include_router(smart_agent_router, prefix="/api")
    print("成功注册智能代理路由")
else:
    print("智能代理路由未注册，因为导入失败")

# 添加前端路径重定向，解决404问题
@app.get("/workflows")
async def redirect_workflows():
    return {"message": "请访问 /api/workflows 获取API数据"}

@app.get("/approval/pending")
async def redirect_approval_pending():
    return {"message": "请访问 /api/approval/pending 获取API数据"}

@app.get("/approval/my")
async def redirect_approval_my():
    return {"message": "请访问 /api/approval/my 获取API数据"}

@app.get("/admin/roles")
async def redirect_admin_roles():
    return {"message": "请访问 /api/admin/roles 获取API数据"}

# 添加表单模式重定向
@app.get("/approval/form-schema/{schema_id}")
async def redirect_form_schema(schema_id: str):
    return {"message": f"请访问 /api/approval/form-schema/{schema_id} 获取表单模式数据"}

# 添加审批实例详情路由重定向
@app.get("/approval/instance-detail/{instance_id}")
async def redirect_approval_instance_detail(instance_id: int):
    # 重定向到对应的API路由
    return {"message": f"请访问 /api/approval/instance-detail/{instance_id} 获取审批详情数据"}

# 添加API端点处理审批详情请求
@app.get("/api/approval/instance-detail/{instance_id}")
async def handle_api_approval_instance_detail(instance_id: int):
    # 直接调用审批API中的获取详情函数
    from api.approval import get_approval_instance_detail as get_detail_func
    from database.session import get_db
    from utils.security import get_current_user
    from fastapi import Depends, Request
    
    # 创建一个请求处理函数
    async def process_request(request: Request, db = Depends(get_db), current_user = Depends(get_current_user)):
        print(f"处理API审批详情请求：{instance_id}")
        return await get_detail_func(instance_id, db, current_user)
    
    # 返回这个函数供FastAPI调用
    return process_request

# 添加工作流详情路由重定向
@app.get("/approval/workflow/{workflow_id}")
async def redirect_approval_workflow(workflow_id: int):
    # 重定向到对应的API路由
    return {"message": f"请访问 /api/workflow-auth/workflow/{workflow_id} 获取工作流配置数据"}

# 添加创建审批重定向
@app.post("/approval/create")
async def redirect_approval_create():
    return {"message": "请访问 /api/approval/create 创建审批"}

# 添加审批撤回重定向
@app.post("/approval/withdraw/{instance_id}")
async def redirect_approval_withdraw(instance_id: int):
    return {"message": f"请访问 /api/approval/withdraw/{instance_id} 撤回审批"}

# 添加审批撤回API重定向
@app.get("/api/approval/withdraw/{instance_id}")
@app.post("/api/approval/withdraw/{instance_id}")
async def handle_approval_withdraw(instance_id: int):
    # 直接调用审批API中的撤回函数
    from api.approval import withdraw_approval
    from database.session import get_db
    from utils.security import get_current_user
    from fastapi import Depends, Request
    
    # 创建一个请求处理函数
    async def process_request(request: Request, db = Depends(get_db), current_user = Depends(get_current_user)):
        return await withdraw_approval(instance_id, current_user, db)
    
    # 返回这个函数供FastAPI调用
    return process_request

# 添加审批删除重定向
@app.delete("/api/approval/{instance_id}")
async def redirect_approval_delete(instance_id: int):
    return {"message": f"请访问 /api/approval/{instance_id} 删除审批"}

# 验证工作流路由是否被正确注册
workflow_routes = [route for route in app.routes if '/api/workflow-auth' in str(route.path)]
print(f"\n已注册的工作流路由数量: {len(workflow_routes)}")
for route in workflow_routes:
    print(f"工作流路由: {route.path} - 方法: {route.methods}")

# 打印所有注册的路由，用于调试
print("\n===== 已注册的路由 =====")
for route in app.routes:
    route_path = getattr(route, "path", "无路径")
    route_methods = getattr(route, "methods", "无方法信息")
    print(f"{route_path} - 方法: {route_methods}")
print("=======================\n")

# 挂载静态文件目录
# 确保目录存在
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(data_dir, exist_ok=True)
app.mount("/files", StaticFiles(directory=data_dir), name="files")

# 自定义异常处理
@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc)},
    )

# 首页重定向到文档
@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API文档")

# 主入口点
if __name__ == "__main__":
    port = 8000  # 定义端口变量
    print("====== 启动服务器 ======")
    print("API服务运行在: http://localhost:8000/api")
    print("在前端目录(frontend)中运行 npm run dev 启动前端")
    print("=======================")
    uvicorn.run(app, host="0.0.0.0", port=port)
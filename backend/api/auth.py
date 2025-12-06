from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
import json
import sys
import os

from database.session import get_db
from utils.security import create_access_token, get_current_user, verify_password, TokenData
from config.settings import settings
from models.user import User
from services.user_service import UserService

router = APIRouter(
    prefix="/auth",
    tags=["认证"],
    responses={404: {"description": "Not found"}},
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# 定义请求和响应模型
class LoginRequest(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    real_name: Optional[str] = None
    is_admin: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserInfo

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str
    real_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('密码不匹配')
        return v
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('用户名必须只包含字母和数字')
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    real_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_admin: bool = False
    
    class Config:
        from_attributes = True

# 直接登录处理，不使用UserService和ORM
def authenticate_user(db: Session, username: str, password: str):
    """验证用户凭证"""
    try:
        # 从环境变量或配置获取管理员初始密码（默认为admin，生产环境应修改）
        ADMIN_DEFAULT_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin')
        
        # 特殊处理admin账户初始化
        if username == 'admin':
            # 检查admin用户是否存在
            admin_check = db.execute(text("SELECT id, hashed_password FROM users WHERE username = 'admin'")).first()
            
            if not admin_check:
                # 创建admin用户 - 使用原生SQL避免ORM冲突
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                hashed_password = pwd_context.hash(ADMIN_DEFAULT_PASSWORD)
                
                db.execute(
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
                db.commit()
                print(f"✓ 管理员账户已创建，初始密码: {ADMIN_DEFAULT_PASSWORD}")
                print("⚠️ 请登录后立即修改密码！")
            
        # 查询普通用户 - 使用原生SQL避免ORM冲突
        user = db.execute(
            text("SELECT id, username, email, hashed_password, real_name, is_admin FROM users WHERE username = :username"),
            {"username": username}
        ).first()
        
        if not user:
            return None
            
        # 验证密码
        if not verify_password(password, user.hashed_password):
            return None
            
        # 返回用户信息 
        return {
            "id": user.id, 
            "username": user.username,
            "email": user.email,
            "real_name": user.real_name,
            "is_admin": user.is_admin
        }
    except Exception as e:
        print(f"验证用户时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"登录过程中发生错误: {str(e)}")

# 请求处理函数
async def verify_admin(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """验证当前用户是否为管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """表单方式登录，获取访问令牌"""
    try:
        # 使用表单数据
        username = form_data.username
        password = form_data.password
        
        user = authenticate_user(db, username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码不正确",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 创建访问令牌
        access_token = create_access_token(data={"sub": user["username"]})
        
        # 返回令牌和用户基本信息
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"登录失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"登录过程中发生错误: {str(e)}")

@router.post("/login-json", response_model=Token)
async def login_with_json(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """JSON方式登录，获取访问令牌"""
    try:
        user = authenticate_user(db, login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码不正确",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 创建访问令牌
        access_token = create_access_token(data={"sub": user["username"]})
        
        # 返回令牌和用户基本信息
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"登录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"登录过程中发生错误: {str(e)}")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    try:
        # 检查用户名是否已存在
        if UserService.get_user_by_username(db, user.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否已存在
        if UserService.get_user_by_email(db, user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在"
            )
        
        # 创建用户 (移除确认密码字段)
        user_data = user.dict(exclude={"confirm_password"})
        # 确保键名与模型字段匹配
        if "real_name" in user_data and user_data["real_name"]:
            user_data["full_name"] = user_data["real_name"]
            
        db_user = UserService.create_user(db, user_data)
        
        return UserResponse.from_orm(db_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册过程中发生错误: {str(e)}"
        )

@router.get("/users/me", response_model=Dict[str, Any])
async def get_current_user_info(current_user = Depends(get_current_user)):
    """获取当前用户信息"""
    # 简化返回数据，避免复杂关系
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "real_name": current_user["real_name"],
        "is_admin": current_user["is_admin"]
    }

@router.post("/logout")
async def logout():
    """用户登出（客户端需自行处理令牌）"""
    return {"message": "登出成功"}
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
from pydantic import BaseModel

from config.settings import settings
from database.session import get_db
# 避免直接导入User类
# from backend.models import User

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置
SECRET_KEY = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
ALGORITHM = settings.ALGORITHM if hasattr(settings, 'ALGORITHM') else "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES if hasattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES') else 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def verify_token(token: str) -> Optional[dict]:
    """验证令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Token数据模型
class TokenData(BaseModel):
    username: Optional[str] = None

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """获取当前用户（使用原生SQL，不依赖ORM）"""
    print(f"Authenticating token: {token[:20]}...")  # 打印部分token用于调试
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码令牌
        print("尝试解码令牌...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"令牌解码成功，有效载荷: {payload}")
        username: str = payload.get("sub")
        if username is None:
            print("令牌中未找到username(sub)字段")
            raise credentials_exception
        token_data = TokenData(username=username)
        print(f"用户名: {username}")
    except JWTError as e:
        print(f"JWT解码错误: {str(e)}")
        raise credentials_exception
    
    try:
        # 特殊处理admin用户
        if username == 'admin':
            # 使用SQL检查admin用户是否存在
            admin_check = db.execute(text("SELECT id FROM users WHERE username = 'admin'")).first()
            
            if not admin_check:
                # 如果admin用户不存在，返回默认admin信息
                return {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@example.com",
                    "real_name": "系统管理员",
                    "is_admin": True,
                    "roles": [{"name": "admin", "permissions": [
                        {"resource": "approval", "action": "read"},
                        {"resource": "approval", "action": "read_own"}
                    ]}]
                }
            
        # 使用SQL查询用户信息
        user = db.execute(
            text("SELECT id, username, email, real_name, is_admin FROM users WHERE username = :username"),
            {"username": username}
        ).first()
        
        if user is None:
            raise credentials_exception
            
        # 查询用户角色信息
        roles = []
        
        # 这里如果有用户角色表，可以查询用户的角色
        # 为简化处理，我们为每个用户添加一个默认角色，并赋予审批相关权限
        roles.append({
            "name": "default",
            "permissions": [
                {"resource": "approval", "action": "read"},
                {"resource": "approval", "action": "read_own"}
            ]
        })
        
        # 返回用户信息字典
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "real_name": user.real_name,
            "is_admin": user.is_admin,
            "roles": roles
        }
    except Exception as e:
        print(f"获取当前用户出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户信息时发生错误: {str(e)}")

def check_permission(user: Dict[str, Any], permission_code: str) -> bool:
    """检查用户是否有指定权限"""
    # 管理员拥有所有权限
    if user.get("is_admin", False):
        return True
        
    # 非管理员检查具体权限
    try:
        # 解析权限代码
        resource, action = permission_code.split(":")
        
        # 检查用户角色
        for role in user.get("roles", []):
            for permission in role.get("permissions", []):
                if permission.get("resource") == resource and permission.get("action") == action:
                    return True
                    
        return False
    except Exception as e:
        print(f"权限检查错误: {str(e)}")
        return False

def require_permission(resource: str, action: str):
    """权限检查装饰器"""
    async def permission_checker(
        current_user: Any = Depends(get_current_user)
    ) -> Any:
        if not check_permission(current_user, resource):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return permission_checker

async def get_admin_user(current_user: Any = Depends(get_current_user)):
    """确保当前用户是管理员"""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以访问此接口"
        )
    return current_user
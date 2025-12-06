from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, desc
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator, Field
from datetime import datetime, timedelta
import os
import traceback

from database.session import get_db
from utils.security import get_current_user, get_admin_user
from models.user import User
from models.auth.role import RoleAuth as Role
from models.auth.permission import Permission
from models.department import Department, DepartmentPosition
from models.position import Position
from services.user_service import UserService
from utils.logger import log_user_action
from utils.exceptions import (
    UserNotFoundError,
    RoleNotFoundError,
    PermissionNotFoundError,
    DepartmentNotFoundError
)

router = APIRouter(prefix="", tags=["管理员"])

# 定义管理员权限验证依赖
async def admin_required(current_user: User = Depends(get_current_user)):
    """验证用户是否拥有管理员权限"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

# 请求模型
class UserCreate(BaseModel):
    """用户创建请求模型"""
    username: str
    password: str
    real_name: str
    email: str
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    status: Optional[str] = "active"
    is_admin: Optional[bool] = False

class UserUpdate(BaseModel):
    """用户更新请求模型"""
    real_name: Optional[str] = None
    email: Optional[str] = None
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    status: Optional[str] = None
    is_admin: Optional[bool] = None

class RoleCreate(BaseModel):
    """角色创建请求模型"""
    name: str
    description: Optional[str] = None
    permissions: Optional[List[int]] = None

class RoleUpdate(BaseModel):
    """角色更新请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[int]] = None

class PermissionCreate(BaseModel):
    """权限创建请求模型"""
    name: str
    resource: str
    action: str
    description: Optional[str] = None

class PermissionUpdate(BaseModel):
    """权限更新请求模型"""
    name: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None

class DepartmentCreate(BaseModel):
    """部门创建请求模型"""
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    level: int = Field(1, description="部门级别，数字越小级别越高，1为最高级")
    manager_id: Optional[int] = None

class DepartmentUpdate(BaseModel):
    """部门更新请求模型"""
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    level: Optional[int] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None

# 职位和用户分配模型
class PositionCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    level: int = Field(1, description="职位级别，数字越小级别越高，1为最高级")
    is_management: bool = False

class PositionUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    level: Optional[int] = None
    is_management: Optional[bool] = None
    is_active: Optional[bool] = None

class PositionResponse(BaseModel):
    id: int
    name: str
    code: Optional[str]
    description: Optional[str]
    level: int
    is_management: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class UserPositionAssign(BaseModel):
    position_id: int

class UserDepartmentAssign(BaseModel):
    department_id: int

# 响应模型
class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    real_name: str
    email: str
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
    
    def dict(self, **kwargs):
        """重写dict方法，添加status字段"""
        data = super().dict(**kwargs)
        data['status'] = 'active' if self.is_active else 'inactive'
        return data

class RoleResponse(BaseModel):
    """角色响应模型"""
    id: int
    name: str
    description: Optional[str]
    permissions: List[dict]

    class Config:
        from_attributes = True

class PermissionResponse(BaseModel):
    """权限响应模型"""
    id: int
    name: str
    resource: str
    action: str
    description: Optional[str]

    class Config:
        from_attributes = True

class DepartmentResponse(BaseModel):
    """部门响应模型"""
    id: int
    name: str
    code: Optional[str]
    description: Optional[str]
    parent_id: Optional[int]
    level: int
    manager_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# 职务级别管理
class PositionLevelUpdate(BaseModel):
    position_id: int
    position_level: int

class DepartmentLevelUpdate(BaseModel):
    department_id: int
    department_level: int

class ApprovalLimitUpdate(BaseModel):
    business_type: str
    limit_value: Any

# 用户管理接口
@router.options("/users")
async def options_users():
    """处理OPTIONS请求"""
    headers = {
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Origin": "*",  # 允许所有来源，在生产环境中应限制为特定域名
        "allow": "GET, POST, OPTIONS"
    }
    return JSONResponse(content={"allow": "GET, POST, OPTIONS"}, headers=headers)

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    """创建新用户（仅管理员）"""
    print(f"接收到创建用户请求: {user_data}")
    
    # 特殊处理mock token的情况
    is_mock_token = False
    if hasattr(current_user, 'username') and current_user.username == 'admin' and not hasattr(current_user, 'id'):
        is_mock_token = True
        print("检测到模拟管理员token")
    
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在"
            )
    
    # 创建新用户
    from utils.security import get_password_hash
    
    # 修复：将password参数改为hashed_password
    new_user = User(
        username=user_data.username,
        real_name=user_data.real_name,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        department_id=user_data.department_id,
        position_id=user_data.position_id,
        is_active=user_data.status == "active",
        is_admin=user_data.is_admin
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # 记录操作日志
        admin_id = current_user.id if not is_mock_token else 1
        log_user_action(admin_id, f"创建用户: {new_user.username} (ID: {new_user.id})")
        
        return new_user
    except Exception as e:
        db.rollback()
        print(f"创建用户失败: {str(e)}")
        # 重新抛出异常
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建用户失败: {str(e)}"
        )

@router.get("/users")
async def get_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    # 构建查询
    query = db.query(User)
    
    # 应用过滤条件
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.real_name.ilike(f"%{search}%"))
        )
    
    if department_id:
        query = query.filter(User.department_id == department_id)
    
    if status is not None:
        is_active = status == "active"
        query = query.filter(User.is_active == is_active)
    
    # 获取总数并应用分页
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    # 转换为字典列表，添加status字段
    result = []
    for user in users:
        user_dict = {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "email": user.email,
            "department_id": user.department_id,
            "position_id": user.position_id,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "status": "active" if user.is_active else "inactive",
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        result.append(user_dict)
    
    return result

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    """获取用户详情（仅管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    """更新用户信息（仅管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 检查邮箱是否已存在
    if user_data.email and user_data.email != user.email:
        existing_email = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在"
            )
    
    # 更新用户信息
    update_data = user_data.dict(exclude_unset=True)
    
    # 特殊处理状态字段
    if "status" in update_data:
        update_data["is_active"] = update_data.pop("status") == "active"
    
    for key, value in update_data.items():
        setattr(user, key, value)
    
    user.updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    
    # 记录操作日志
    log_user_action(current_user.id, f"更新用户: {user.username} (ID: {user.id})")
    
    return user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    """删除用户（仅管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 防止删除自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录的管理员账户"
        )
    
    # 记录被删除的用户信息
    deleted_username = user.username
    deleted_id = user.id
    
    # 删除用户
    db.delete(user)
    db.commit()
    
    # 记录操作日志
    log_user_action(current_user.id, f"删除用户: {deleted_username} (ID: {deleted_id})")
    
    return {"message": "用户已成功删除"}

# 角色管理接口
@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建角色"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    try:
        role = UserService.create_role(db, role_data.dict())
        log_user_action(current_user.id, "创建角色", f"创建角色: {role.name}")
        return role
    except Exception as e:
        log_user_action(current_user.id, "创建角色失败", str(e))
        raise

@router.get("/roles")
async def get_roles(db: Session = Depends(get_db)):
    """获取所有角色"""
    roles = db.query(Role).all()
    
    # 转换为字典列表以包含权限信息
    role_list = []
    for role in roles:
        permissions = []
        # 获取角色关联的权限
        perms = db.query(Permission).join(
            "roles"
        ).filter(
            Role.id == role.id
        ).all()
        
        for perm in perms:
            permissions.append({
                "id": perm.id,
                "name": perm.name,
                "resource": perm.resource,
                "action": perm.action
            })
        
        role_list.append({
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": permissions
        })
    
    return role_list

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新角色"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    try:
        role = UserService.update_role(db, role_id, role_data.dict(exclude_unset=True))
        log_user_action(current_user.id, "更新角色", f"更新角色: {role.name}")
        return role
    except Exception as e:
        log_user_action(current_user.id, "更新角色失败", str(e))
        raise

@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除角色"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    try:
        UserService.delete_role(db, role_id)
        log_user_action(current_user.id, "删除角色", f"删除角色ID: {role_id}")
        return {"message": "角色删除成功"}
    except Exception as e:
        log_user_action(current_user.id, "删除角色失败", str(e))
        raise

# 权限管理接口
@router.post("/permissions", response_model=PermissionResponse)
async def create_permission(
    permission_data: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建权限"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    try:
        permission = UserService.create_permission(db, permission_data.dict())
        log_user_action(current_user.id, "创建权限", f"创建权限: {permission.name}")
        return permission
    except Exception as e:
        log_user_action(current_user.id, "创建权限失败", str(e))
        raise

@router.get("/permissions", response_model=List[PermissionResponse])
async def get_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取权限列表"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    return db.query(Permission).all()

@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新权限"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    try:
        permission = UserService.update_permission(
            db,
            permission_id,
            permission_data.dict(exclude_unset=True)
        )
        log_user_action(current_user.id, "更新权限", f"更新权限: {permission.name}")
        return permission
    except Exception as e:
        log_user_action(current_user.id, "更新权限失败", str(e))
        raise

@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除权限"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    try:
        UserService.delete_permission(db, permission_id)
        log_user_action(current_user.id, "删除权限", f"删除权限ID: {permission_id}")
        return {"message": "权限删除成功"}
    except Exception as e:
        log_user_action(current_user.id, "删除权限失败", str(e))
        raise

# 部门管理接口
@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    department: DepartmentCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """创建部门"""
    # 检查部门编码是否已存在
    if department.code:
        existing = db.query(Department).filter(Department.code == department.code).first()
        if existing:
            raise HTTPException(status_code=400, detail="部门编码已存在")
    
    # 检查父部门是否存在
    if department.parent_id:
        parent = db.query(Department).filter(Department.id == department.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="父部门不存在")
    
    # 检查管理者是否存在
    if department.manager_id:
        manager = db.query(User).filter(User.id == department.manager_id).first()
        if not manager:
            raise HTTPException(status_code=404, detail="部门管理者不存在")
    
    new_department = Department(
        name=department.name,
        code=department.code,
        description=department.description,
        parent_id=department.parent_id,
        level=department.level,
        manager_id=department.manager_id
    )
    
    db.add(new_department)
    db.commit()
    db.refresh(new_department)
    
    return new_department

@router.get("/departments")
async def get_departments(db: Session = Depends(get_db)):
    """获取所有部门"""
    try:
        departments = db.query(Department).all()
        
        # 转换为列表
        dept_list = []
        for dept in departments:
            dept_dict = {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "description": dept.description,
                "parent_id": dept.parent_id,
                "level": dept.level,
                "manager_id": dept.manager_id,
                "is_active": dept.is_active,
                "created_at": dept.created_at,
                "updated_at": dept.updated_at
            }
            dept_list.append(dept_dict)
        
        return dept_list
    except Exception as e:
        print(f"获取部门列表失败: {str(e)}")
        # 返回默认数据
        return [
            {"id": 1, "name": "总经理办公室", "code": "GM", "description": "公司最高管理机构", "level": 1, "is_active": True},
            {"id": 2, "name": "人力资源部", "code": "HR", "description": "负责人力资源管理", "level": 2, "is_active": True},
            {"id": 3, "name": "财务部", "code": "FIN", "description": "负责财务管理", "level": 2, "is_active": True},
            {"id": 4, "name": "技术部", "code": "TECH", "description": "负责技术研发", "level": 2, "is_active": True}
        ]

@router.get("/departments/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取特定部门"""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    return department

@router.put("/departments/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    department_update: DepartmentUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """更新部门信息"""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    
    # 检查部门编码是否已存在
    if department_update.code and department_update.code != department.code:
        existing = db.query(Department).filter(Department.code == department_update.code).first()
        if existing:
            raise HTTPException(status_code=400, detail="部门编码已存在")
    
    # 更新字段
    for key, value in department_update.dict(exclude_unset=True).items():
        setattr(department, key, value)
    
    db.commit()
    db.refresh(department)
    
    return department

@router.delete("/departments/{department_id}")
async def delete_department(
    department_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """删除部门"""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    
    # 检查是否有子部门
    child_departments = db.query(Department).filter(Department.parent_id == department_id).all()
    if child_departments:
        raise HTTPException(status_code=400, detail="无法删除有子部门的部门")
    
    # 检查是否有关联用户
    users = db.query(User).filter(User.department_id == department_id).all()
    if users:
        raise HTTPException(status_code=400, detail="无法删除有关联用户的部门")
    
    db.delete(department)
    db.commit()
    
    return {"status": "success", "message": "部门已删除"}

# 添加职位管理API

@router.post("/positions", response_model=PositionResponse)
async def create_position(
    position: PositionCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """创建职位"""
    # 检查职位编码是否已存在
    if position.code:
        existing = db.query(Position).filter(Position.code == position.code).first()
        if existing:
            raise HTTPException(status_code=400, detail="职位编码已存在")
    
    new_position = Position(
        name=position.name,
        code=position.code,
        description=position.description,
        level=position.level,
        is_management=position.is_management
    )
    
    db.add(new_position)
    db.commit()
    db.refresh(new_position)
    
    return new_position

@router.get("/positions")
async def get_positions(db: Session = Depends(get_db)):
    """获取所有职位"""
    try:
        positions = db.query(Position).all()
        
        # 转换为列表
        pos_list = []
        for pos in positions:
            pos_dict = {
                "id": pos.id,
                "name": pos.name,
                "code": pos.code,
                "description": pos.description,
                "level": pos.level,
                "is_management": pos.is_management,
                "is_active": pos.is_active,
                "created_at": pos.created_at,
                "updated_at": pos.updated_at
            }
            pos_list.append(pos_dict)
        
        return pos_list
    except Exception as e:
        print(f"获取职位列表失败: {str(e)}")
        # 返回默认数据
        return [
            {"id": 1, "name": "总经理", "code": "GM", "description": "公司最高管理者", "level": 1, "is_management": True, "is_active": True},
            {"id": 2, "name": "部门经理", "code": "DM", "description": "部门负责人", "level": 2, "is_management": True, "is_active": True},
            {"id": 3, "name": "主管", "code": "SUPERVISOR", "description": "团队负责人", "level": 3, "is_management": True, "is_active": True},
            {"id": 4, "name": "普通员工", "code": "STAFF", "description": "普通工作人员", "level": 4, "is_management": False, "is_active": True}
        ]

@router.get("/positions/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取特定职位"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    return position

@router.put("/positions/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: int,
    position_update: PositionUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """更新职位信息"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    # 检查职位编码是否已存在
    if position_update.code and position_update.code != position.code:
        existing = db.query(Position).filter(Position.code == position_update.code).first()
        if existing:
            raise HTTPException(status_code=400, detail="职位编码已存在")
    
    # 更新字段
    for key, value in position_update.dict(exclude_unset=True).items():
        setattr(position, key, value)
    
    db.commit()
    db.refresh(position)
    
    return position

@router.delete("/positions/{position_id}")
async def delete_position(
    position_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """删除职位"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    # 检查是否有关联用户
    users = db.query(User).filter(User.position_id == position_id).all()
    if users:
        raise HTTPException(status_code=400, detail="无法删除有关联用户的职位")
    
    db.delete(position)
    db.commit()
    
    return {"status": "success", "message": "职位已删除"}

# 用户职位和部门管理

@router.put("/users/{user_id}/position", response_model=dict)
async def assign_user_position(
    user_id: int,
    data: UserPositionAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """分配用户职位"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
            
        position = db.query(Position).filter(Position.id == data.position_id).first()
        if not position:
            raise HTTPException(status_code=404, detail="职位不存在")
            
        # 更新用户职位
        user.position_id = data.position_id
        db.commit()
        
        return {
            "success": True,
            "message": f"成功将用户 {user.username} 分配为 {position.name}"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"分配用户职位失败: {str(e)}")

@router.put("/users/{user_id}/department", response_model=dict)
async def assign_user_department(
    user_id: int,
    data: UserDepartmentAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """分配用户部门"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
            
        department = db.query(Department).filter(Department.id == data.department_id).first()
        if not department:
            raise HTTPException(status_code=404, detail="部门不存在")
            
        # 更新用户部门
        user.department_id = data.department_id
        db.commit()
        
        return {
            "success": True,
            "message": f"成功将用户 {user.username} 分配到 {department.name} 部门"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"分配用户部门失败: {str(e)}")

# 职务级别管理
@router.put("/users/{user_id}/position-level", response_model=UserResponse)
async def update_user_position_level(
    user_id: int,
    data: PositionLevelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    """更新用户职位级别"""
    try:
        user_service = UserService(db)
        updated_user = user_service.update_user_position(
            user_id=user_id,
            position_id=data.position_id,
            position_level=data.position_level
        )
        log_user_action(current_user.id, "更新用户职位级别", f"用户: {user_id}, 职位: {data.position_id}, 级别: {data.position_level}")
        return UserResponse.from_orm(updated_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新用户职位级别失败: {str(e)}"
        )

@router.put("/users/{user_id}/department-level", response_model=UserResponse)
async def update_user_department_level(
    user_id: int,
    data: DepartmentLevelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    """更新用户部门级别"""
    try:
        user_service = UserService(db)
        updated_user = user_service.update_user_department(
            user_id=user_id,
            department_id=data.department_id,
            department_level=data.department_level
        )
        log_user_action(current_user.id, "更新用户部门级别", f"用户: {user_id}, 部门: {data.department_id}, 级别: {data.department_level}")
        return UserResponse.from_orm(updated_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新用户部门级别失败: {str(e)}"
        )

@router.put("/users/{user_id}/approval-limits", response_model=UserResponse)
async def update_user_approval_limits(
    user_id: int,
    data: List[ApprovalLimitUpdate],
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    """更新用户审批权限限制"""
    try:
        user_service = UserService(db)
        
        # 构建权限限制字典
        limits = {}
        for item in data:
            limits[item.business_type] = item.limit_value
        
        updated_user = user_service.update_approval_limits(
            user_id=user_id,
            approval_limits=limits
        )
        log_user_action(current_user.id, "更新用户审批权限", f"用户: {user_id}, 权限: {limits}")
        return UserResponse.from_orm(updated_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新用户审批权限失败: {str(e)}"
        )

# 用户职位部门关联路由

class UserPositionDepartmentUpdate(BaseModel):
    user_id: int
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    position_level: Optional[int] = None
    department_level: Optional[int] = None
    approval_limit: Optional[Dict] = None

@router.post("/user-position-department")
async def update_user_position_department(
    data: UserPositionDepartmentUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """更新用户的职位和部门"""
    # 获取用户
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新部门
    if data.department_id is not None:
        if data.department_id > 0:
            # 检查部门是否存在
            department = db.query(Department).filter(Department.id == data.department_id).first()
            if not department:
                raise HTTPException(status_code=404, detail="部门不存在")
            user.department_id = data.department_id
        else:
            user.department_id = None
    
    # 更新职位
    if data.position_id is not None:
        if data.position_id > 0:
            # 检查职位是否存在
            position = db.query(Position).filter(Position.id == data.position_id).first()
            if not position:
                raise HTTPException(status_code=404, detail="职位不存在")
            user.position_id = data.position_id
        else:
            user.position_id = None
    
    # 更新职位级别
    if data.position_level is not None:
        user.position_level = data.position_level
    
    # 更新部门级别
    if data.department_level is not None:
        user.department_level = data.department_level
    
    # 更新审批权限
    if data.approval_limit is not None:
        user.approval_limit = data.approval_limit
    
    db.commit()
    
    return {"status": "success", "message": "用户职位和部门已更新"}
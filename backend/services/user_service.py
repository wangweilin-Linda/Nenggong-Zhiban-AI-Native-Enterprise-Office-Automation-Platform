from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.user import User
from models.auth.role import RoleAuth as Role
from models.auth.permission import Permission
from utils.security import get_password_hash, verify_password
from utils.exceptions import (
    UserExistsError,
    UserNotFoundError,
    RoleNotFoundError,
    PermissionNotFoundError,
    DepartmentNotFoundError
)
from utils.logger import log_user_action

class UserService:
    """用户服务类"""
    
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_user(db: Session, user_data: dict) -> User:
        """创建用户"""
        # 检查用户名是否已存在
        if UserService.get_user_by_username(db, user_data["username"]):
            raise UserExistsError("用户名已存在")
        
        # 检查邮箱是否已存在
        if user_data.get("email") and UserService.get_user_by_email(db, user_data["email"]):
            raise UserExistsError("邮箱已存在")
        
        # 创建用户对象
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            password=get_password_hash(user_data["password"]),
            full_name=user_data.get("full_name") or user_data.get("real_name", ""),
            department_id=user_data.get("department_id"),
            position_id=user_data.get("position_id"),
            is_active=user_data.get("is_active", True),
            is_admin=user_data.get("is_admin", False)
        )
        
        # 如果指定了角色，添加角色
        if "roles" in user_data:
            roles = db.query(Role).filter(Role.id.in_(user_data["roles"])).all()
            user.roles = roles
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """验证用户"""
        user = UserService.get_user_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.password):
            return None
        return user

    @staticmethod
    def update_user(db: Session, user_id: int, user_data: dict) -> User:
        """更新用户信息"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise UserNotFoundError("用户不存在")
        
        # 更新用户信息
        for key, value in user_data.items():
            if key == "password":
                value = get_password_hash(value)
            if hasattr(user, key):
                setattr(user, key, value)
        
        # 更新角色
        if "roles" in user_data:
            roles = db.query(Role).filter(Role.id.in_(user_data.roles)).all()
            user.roles = roles
        
        db.commit()
        db.refresh(user)
        
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> None:
        """删除用户"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise UserNotFoundError("用户不存在")
        
        db.delete(user)
        db.commit()

    @staticmethod
    def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            return False
            
        if not verify_password(old_password, user.password):
            return False
            
        user.password = get_password_hash(new_password)
        db.commit()
        return True

    @staticmethod
    def get_users(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """获取用户列表"""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_role(db: Session, role_data: dict) -> Role:
        """创建角色"""
        role = Role(
            name=role_data["name"],
            description=role_data.get("description")
        )
        
        # 如果指定了权限，添加权限
        if "permissions" in role_data:
            permissions = db.query(Permission).filter(
                Permission.id.in_(role_data["permissions"])
            ).all()
            role.permissions = permissions
        
        db.add(role)
        db.commit()
        db.refresh(role)
        
        return role
    
    @staticmethod
    def update_role(db: Session, role_id: int, role_data: dict) -> Role:
        """更新角色"""
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise RoleNotFoundError("角色不存在")
        
        # 更新角色信息
        for key, value in role_data.items():
            if hasattr(role, key):
                setattr(role, key, value)
        
        # 更新权限
        if "permissions" in role_data:
            permissions = db.query(Permission).filter(
                Permission.id.in_(role_data["permissions"])
            ).all()
            role.permissions = permissions
        
        db.commit()
        db.refresh(role)
        
        return role
    
    @staticmethod
    def delete_role(db: Session, role_id: int) -> None:
        """删除角色"""
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise RoleNotFoundError("角色不存在")
        
        db.delete(role)
        db.commit()
    
    @staticmethod
    def create_permission(db: Session, permission_data: dict) -> Permission:
        """创建权限"""
        permission = Permission(
            resource=permission_data["resource"],
            action=permission_data["action"],
            description=permission_data.get("description")
        )
        
        db.add(permission)
        db.commit()
        db.refresh(permission)
        
        return permission
    
    @staticmethod
    def update_permission(db: Session, permission_id: int, permission_data: dict) -> Permission:
        """更新权限"""
        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise PermissionNotFoundError("权限不存在")
        
        for key, value in permission_data.items():
            if hasattr(permission, key):
                setattr(permission, key, value)
        
        db.commit()
        db.refresh(permission)
        
        return permission
    
    @staticmethod
    def delete_permission(db: Session, permission_id: int) -> None:
        """删除权限"""
        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise PermissionNotFoundError("权限不存在")
        
        db.delete(permission)
        db.commit()
    
    # 注释掉与Department相关的方法
    """
    @staticmethod
    def create_department(db: Session, department_data: dict):
        pass
    
    @staticmethod
    def update_department(db: Session, department_id: int, department_data: dict):
        pass
    
    @staticmethod
    def delete_department(db: Session, department_id: int):
        pass
    
    @staticmethod
    def get_department_tree(db: Session):
        pass

    def get_user_permissions(self, user_id: int):
        pass

    def check_permission(self, user_id: int, resource: str, action: str):
        pass

    def create_department(self, department_data: Dict[str, Any]):
        pass

    def update_department(self, department_id: int, department_data: Dict[str, Any]):
        pass

    def delete_department(self, department_id: int):
        pass

    def get_department_tree(self):
        pass

    def update_user_position(self, user_id: int, position_id: int, position_level: int = None):
        pass
    
    def update_user_department(self, user_id: int, department_id: int, department_level: int = None):
        pass
    
    def update_approval_limits(self, user_id: int, approval_limits: Dict[str, Any]):
        pass
    """ 

    def get_user_permissions(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户所有权限"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
            
            permissions = []
            for role in user.roles:
                for permission in role.permissions:
                    permissions.append({
                        "id": permission.id,
                        "name": permission.name,
                        "resource": permission.resource,
                        "action": permission.action
                    })
            
            return permissions
        except Exception as e:
            print(f"获取用户权限错误: {str(e)}")
            return []
        
    def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户所有角色"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
            
            roles = []
            for role in user.roles:
                roles.append({
                    "id": role.id,
                    "name": role.name,
                    "permissions": [{
                        "id": p.id,
                        "name": p.name,
                        "resource": p.resource,
                        "action": p.action
                    } for p in role.permissions]
                })
            
            return roles
        except Exception as e:
            print(f"获取用户角色错误: {str(e)}")
            return [] 
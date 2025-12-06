from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Callable

from backend.database.session import get_db
from backend.models.user import User
from backend.services.auth_service import get_current_user, check_permission

def require_permissions(resource: str, action: str):
    """权限验证装饰器"""
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        if not check_permission(current_user, resource, action, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return dependency

def admin_required(current_user: User = Depends(get_current_user)):
    """管理员权限验证装饰器"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
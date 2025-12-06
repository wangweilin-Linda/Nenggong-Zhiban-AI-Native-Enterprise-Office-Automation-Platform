from sqlalchemy import Table, Column, Integer, ForeignKey
from models.base import Base

# 所有关联表定义集中在这里，使用extend_existing=True避免重复定义错误
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    extend_existing=True
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True),
    extend_existing=True
)
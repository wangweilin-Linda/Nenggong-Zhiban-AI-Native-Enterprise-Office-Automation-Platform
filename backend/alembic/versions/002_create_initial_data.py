"""create initial data

Revision ID: 002
Revises: 001
Create Date: 2024-03-21 10:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
from sqlalchemy.sql import table, column
from backend.utils.security import get_password_hash

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # 创建表引用
    departments = table('departments',
        column('id', sa.Integer),
        column('name', sa.String),
        column('parent_id', sa.Integer),
        column('description', sa.String),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )

    roles = table('roles',
        column('id', sa.Integer),
        column('name', sa.String),
        column('description', sa.String),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )

    permissions = table('permissions',
        column('id', sa.Integer),
        column('name', sa.String),
        column('resource', sa.String),
        column('action', sa.String),
        column('description', sa.String),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )

    users = table('users',
        column('id', sa.Integer),
        column('employee_id', sa.String),
        column('username', sa.String),
        column('password_hash', sa.String),
        column('real_name', sa.String),
        column('department_id', sa.Integer),
        column('position', sa.String),
        column('email', sa.String),
        column('phone', sa.String),
        column('is_active', sa.Boolean),
        column('is_admin', sa.Boolean),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )

    user_roles = table('user_roles',
        column('user_id', sa.Integer),
        column('role_id', sa.Integer)
    )

    role_permissions = table('role_permissions',
        column('role_id', sa.Integer),
        column('permission_id', sa.Integer)
    )

    now = datetime.utcnow()

    # 创建默认部门
    op.bulk_insert(departments, [
        {
            'name': '系统管理部',
            'description': '系统管理部门',
            'created_at': now,
            'updated_at': now
        }
    ])

    # 创建基本权限
    op.bulk_insert(permissions, [
        {
            'name': '用户管理',
            'resource': 'users',
            'action': 'create',
            'description': '创建用户',
            'created_at': now,
            'updated_at': now
        },
        {
            'name': '用户管理',
            'resource': 'users',
            'action': 'read',
            'description': '查看用户',
            'created_at': now,
            'updated_at': now
        },
        {
            'name': '用户管理',
            'resource': 'users',
            'action': 'update',
            'description': '更新用户',
            'created_at': now,
            'updated_at': now
        },
        {
            'name': '用户管理',
            'resource': 'users',
            'action': 'delete',
            'description': '删除用户',
            'created_at': now,
            'updated_at': now
        },
        {
            'name': '角色管理',
            'resource': 'roles',
            'action': 'create',
            'description': '创建角色',
            'created_at': now,
            'updated_at': now
        },
        {
            'name': '角色管理',
            'resource': 'roles',
            'action': 'read',
            'description': '查看角色',
            'created_at': now,
            'updated_at': now
        },
        {
            'name': '角色管理',
            'resource': 'roles',
            'action': 'update',
            'description': '更新角色',
            'created_at': now,
            'updated_at': now
        },
        {
            'name': '角色管理',
            'resource': 'roles',
            'action': 'delete',
            'description': '删除角色',
            'created_at': now,
            'updated_at': now
        }
    ])

    # 创建基本角色
    op.bulk_insert(roles, [
        {
            'name': '超级管理员',
            'description': '系统超级管理员',
            'created_at': now,
            'updated_at': now
        },
        {
            'name': '普通用户',
            'description': '普通用户',
            'created_at': now,
            'updated_at': now
        }
    ])

    # 创建管理员用户
    op.bulk_insert(users, [
        {
            'employee_id': 'admin001',
            'username': 'admin',
            'password_hash': get_password_hash('admin123'),
            'real_name': '系统管理员',
            'department_id': 1,
            'position': '系统管理员',
            'email': 'admin@example.com',
            'phone': '13800138000',
            'is_active': True,
            'is_admin': True,
            'created_at': now,
            'updated_at': now
        }
    ])

    # 为管理员分配超级管理员角色
    op.bulk_insert(user_roles, [
        {
            'user_id': 1,
            'role_id': 1
        }
    ])

    # 为超级管理员角色分配所有权限
    op.bulk_insert(role_permissions, [
        {'role_id': 1, 'permission_id': 1},
        {'role_id': 1, 'permission_id': 2},
        {'role_id': 1, 'permission_id': 3},
        {'role_id': 1, 'permission_id': 4},
        {'role_id': 1, 'permission_id': 5},
        {'role_id': 1, 'permission_id': 6},
        {'role_id': 1, 'permission_id': 7},
        {'role_id': 1, 'permission_id': 8}
    ])


def downgrade():
    # 删除所有初始数据
    op.execute('DELETE FROM role_permissions')
    op.execute('DELETE FROM user_roles')
    op.execute('DELETE FROM users')
    op.execute('DELETE FROM roles')
    op.execute('DELETE FROM permissions')
    op.execute('DELETE FROM departments') 
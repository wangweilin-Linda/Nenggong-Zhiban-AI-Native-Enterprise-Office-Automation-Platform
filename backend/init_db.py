#!/usr/bin/env python
import os
import sys
import sqlite3
from datetime import datetime, timedelta
import json

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

# 数据库路径
def get_db_path():
    """获取数据库路径"""
    db_path = os.path.join(current_dir, 'oa.db')
    print(f"数据库路径: {db_path}")
    return db_path

def init_database():
    try:
        print("初始化数据库...")
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建users表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            real_name TEXT,
            hashed_password TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 0,
            department_id INTEGER,
            position_id INTEGER,
            position_level INTEGER DEFAULT 0,
            department_level INTEGER DEFAULT 0,
            avatar TEXT,
            created_at TEXT,
            updated_at TEXT,
            last_login TEXT,
            FOREIGN KEY (department_id) REFERENCES departments (id),
            FOREIGN KEY (position_id) REFERENCES positions (id)
        )
        ''')
        
        # 创建departments表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            description TEXT,
            parent_id INTEGER,
            level INTEGER DEFAULT 1,
            manager_id INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (parent_id) REFERENCES departments (id),
            FOREIGN KEY (manager_id) REFERENCES users (id)
        )
        ''')
        
        # 创建positions表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            description TEXT,
            level INTEGER DEFAULT 1,
            is_management INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        # 创建roles表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            permissions TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        # 创建user_roles表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER,
            role_id INTEGER,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (role_id) REFERENCES roles (id)
        )
        ''')
        
        # 创建permissions表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            resource TEXT NOT NULL,
            action TEXT NOT NULL,
            description TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        # 创建role_permissions表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER,
            permission_id INTEGER,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles (id),
            FOREIGN KEY (permission_id) REFERENCES permissions (id)
        )
        ''')
        
        # 创建approval_process表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS approval_process (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            config TEXT,
            form_template TEXT,
            created_at TEXT,
            is_active INTEGER DEFAULT 1
        )
        ''')
        
        # 创建approval_instance表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS approval_instance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process_id INTEGER,
            title TEXT NOT NULL,
            initiator_id INTEGER,
            current_node TEXT,
            status TEXT,
            form_data TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (process_id) REFERENCES approval_process (id),
            FOREIGN KEY (initiator_id) REFERENCES users (id)
        )
        ''')
        
        # 创建approval_node表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS approval_node (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id INTEGER,
            node_id TEXT,
            node_name TEXT,
            approver_id INTEGER,
            status TEXT,
            comment TEXT,
            attachment TEXT,
            created_at TEXT,
            FOREIGN KEY (instance_id) REFERENCES approval_instance (id),
            FOREIGN KEY (approver_id) REFERENCES users (id)
        )
        ''')
        
        # 创建approval_history表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS approval_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id INTEGER,
            node_id TEXT,
            approver_id INTEGER,
            action TEXT,
            comment TEXT,
            created_at TEXT,
            FOREIGN KEY (instance_id) REFERENCES approval_instance (id),
            FOREIGN KEY (approver_id) REFERENCES users (id)
        )
        ''')
        
        # 创建documents表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            document_type TEXT,
            status TEXT,
            creator_id INTEGER,
            department_id INTEGER,
            current_approver_id INTEGER,
            attachments TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (creator_id) REFERENCES users (id),
            FOREIGN KEY (department_id) REFERENCES departments (id),
            FOREIGN KEY (current_approver_id) REFERENCES users (id)
        )
        ''')
        
        conn.commit()
        print("数据库初始化完成")
        
    except Exception as e:
        print(f"初始化数据库时出错: {str(e)}")
        raise

def init_test_data():
    try:
        print("添加测试数据...")
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查admin用户是否存在
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_exists = cursor.fetchone()
        
        # 如果admin用户不存在，创建一个
        if not admin_exists:
            # admin密码使用简单的哈希，这里用的是bcrypt哈希的"admin"
            admin_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
            
            # 插入admin用户
            cursor.execute('''
            INSERT INTO users (username, email, hashed_password, is_admin, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', 'admin@example.com', admin_password, 1, 
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            print("Admin用户创建成功！")
        else:
            print("Admin用户已存在，无需创建。")
        
        # 检查是否已有部门数据
        cursor.execute("SELECT COUNT(*) FROM departments")
        if cursor.fetchone()[0] == 0:
            # 添加测试部门
            departments = [
                ("总经理办公室", "GM", None, 1),
                ("人力资源部", "HR", 1, 2),
                ("财务部", "FIN", 1, 2),
                ("技术部", "TECH", 1, 2)
            ]
            
            for name, code, parent_id, level in departments:
                cursor.execute(
                    "INSERT INTO departments (name, code, parent_id, level, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, code, parent_id, level, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
            
            print("添加测试部门成功")
        
        # 检查是否已有职位数据
        cursor.execute("SELECT COUNT(*) FROM positions")
        if cursor.fetchone()[0] == 0:
            positions = [
                ("总经理", 1, 1),
                ("部门经理", 2, 1),
                ("主管", 3, 1),
                ("普通员工", 4, 0)
            ]
            
            for pos_name, level, is_management in positions:
                cursor.execute('''
                INSERT INTO positions (name, level, is_management, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                ''', (pos_name, level, is_management,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            print("添加默认职位成功！")
        
        # 添加默认角色
        cursor.execute("SELECT COUNT(*) FROM roles")
        if cursor.fetchone()[0] == 0:
            roles = [
                ("管理员", "系统管理员，拥有全部权限"),
                ("部门经理", "管理部门业务和人员"),
                ("高级员工", "拥有较高权限的员工"),
                ("普通员工", "基本权限")
            ]
            
            for role_name, description in roles:
                cursor.execute('''
                INSERT INTO roles (name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ''', (role_name, description,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            print("添加默认角色成功！")
        
        conn.commit()
        print("测试数据添加完成")
        
    except Exception as e:
        print(f"添加测试数据时出错: {str(e)}")
        raise

if __name__ == "__main__":
    init_database()
    init_test_data()
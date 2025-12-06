class UserExistsError(Exception):
    """用户已存在异常"""
    pass

class UserNotFoundError(Exception):
    """用户不存在异常"""
    pass

class RoleNotFoundError(Exception):
    """角色不存在异常"""
    pass

class PermissionNotFoundError(Exception):
    """权限不存在异常"""
    pass

class DepartmentNotFoundError(Exception):
    """部门不存在异常"""
    pass

class InvalidPasswordError(Exception):
    """密码无效异常"""
    pass

class PermissionDeniedError(Exception):
    """权限不足异常"""
    pass

class WorkflowNotFoundError(Exception):
    """工作流不存在异常"""
    pass

class WorkflowValidationError(Exception):
    """工作流验证异常"""
    pass

class DatabaseError(Exception):
    """数据库操作异常"""
    pass

class AuthenticationError(Exception):
    """认证异常"""
    pass

class TokenError(Exception):
    """令牌异常"""
    pass

class ValidationError(Exception):
    """数据验证异常"""
    pass

class BusinessError(Exception):
    """业务逻辑异常"""
    pass 
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from typing import Union, Dict, Any, Optional
from backend.utils.exceptions import (
    UserExistsError,
    AuthenticationError,
    AuthorizationError, 
    NotFoundError,
    ValidationError,
    BusinessError
)

async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """
    处理HTTP异常
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

async def database_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    处理数据库异常
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "数据库错误"}
    )

async def user_exists_error_handler(_: Request, exc: UserExistsError) -> JSONResponse:
    """
    处理用户已存在错误
    """
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"message": "用户已存在", "detail": str(exc)}
    )

async def authentication_error_handler(_: Request, exc: AuthenticationError) -> JSONResponse:
    """
    处理认证错误
    """
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": "认证失败", "detail": str(exc)}
    )

async def authorization_error_handler(_: Request, exc: AuthorizationError) -> JSONResponse:
    """
    处理授权错误
    """
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"message": "没有权限", "detail": str(exc)}
    )

async def not_found_error_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    """
    处理资源未找到错误
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"message": "资源不存在", "detail": str(exc)}
    )

async def validation_error_handler(_: Request, exc: ValidationError) -> JSONResponse:
    """
    处理数据验证错误
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"message": "数据验证错误", "detail": str(exc)}
    )

async def business_error_handler(_: Request, exc: BusinessError) -> JSONResponse:
    """
    处理业务逻辑错误
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": "业务逻辑错误", "detail": str(exc)}
    )

class ErrorHandler:
    """
    错误处理器，用于注册全局异常处理
    """
    
    @staticmethod
    def handle_error(
        request: Request, 
        error: Exception
    ) -> Union[Dict[str, Any], JSONResponse]:
        """
        通用错误处理函数
        """
        if isinstance(error, HTTPException):
            return http_error_handler(request, error)
        elif isinstance(error, SQLAlchemyError):
            return database_error_handler(request, error)
        elif isinstance(error, UserExistsError):
            return user_exists_error_handler(request, error)
        elif isinstance(error, AuthenticationError):
            return authentication_error_handler(request, error)
        elif isinstance(error, AuthorizationError):
            return authorization_error_handler(request, error)
        elif isinstance(error, NotFoundError):
            return not_found_error_handler(request, error)
        elif isinstance(error, ValidationError):
            return validation_error_handler(request, error)
        elif isinstance(error, BusinessError):
            return business_error_handler(request, error)
        
        # 处理其他未知异常
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"未知错误: {str(error)}"}
        )
    
    @staticmethod
    def create_error_response(
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        创建统一格式的错误响应
        """
        content = {
            "error": {
                "message": message,
                "code": error_code or str(status_code)
            }
        }
        
        if extra:
            content["error"].update(extra)
            
        return JSONResponse(
            status_code=status_code,
            content=content
        )

def add_error_handlers(app) -> None:
    """
    添加全局异常处理器到FastAPI应用
    """
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.add_exception_handler(UserExistsError, user_exists_error_handler)
    app.add_exception_handler(AuthenticationError, authentication_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(BusinessError, business_error_handler) 
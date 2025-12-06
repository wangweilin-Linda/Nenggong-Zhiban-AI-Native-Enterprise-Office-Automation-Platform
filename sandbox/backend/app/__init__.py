from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.logging import setup_logging
from .core.middleware import error_handler_middleware
from .api.v1.api import api_router

def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI()
    
    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 开发环境下允许所有来源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 添加错误处理中间件
    app.middleware("http")(error_handler_middleware)
    
    # 注册路由
    app.include_router(api_router, prefix="/api/v1")
    
    return app

app = create_app()
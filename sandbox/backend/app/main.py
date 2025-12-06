from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.api import api_router
from .core.config import Settings, settings  # 修改这里，正确导入 Settings 和 settings
from .core.logging import setup_logging
from .core.middleware import error_handler_middleware

# 初始化日志
setup_logging()

# 不需要再创建 settings 实例，直接使用导入的 settings
# settings = Settings()  # 删除这一行
app = FastAPI(title=settings.APP_NAME)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保路由前缀正确
app.include_router(api_router, prefix="/api/sandbox/v1")

@app.get("/")
async def root():
    return {"message": "欢迎使用数据分析沙箱"}

# 添加错误处理中间件
app.middleware("http")(error_handler_middleware)
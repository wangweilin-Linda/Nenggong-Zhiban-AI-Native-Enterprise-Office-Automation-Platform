import os
from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    # 基础配置
    PROJECT_NAME: str = "OA系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 安全配置
    SECRET_KEY: str = "your_secret_key_here"  # 添加类型注解
    ALGORITHM: str = "HS256"  # 添加类型注解
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///oa.db"
    
    # 模型配置
    MODEL_NAME: str = "deepseek-r1"
    API_HOST: str = "localhost"
    API_PORT: str = "8000"
    TRANSFORMERS_OFFLINE: str = "1"
    HF_DATASETS_OFFLINE: str = "1"
    
    # 跨域配置
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "doc", "docx", "xls", "xlsx", "jpg", "png"]
    
    # 邮件配置
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    
    # 缓存配置
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_PASSWORD: Optional[str] = None
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FILE: str = "logs/app.log"
    
    # 工作流配置
    WORKFLOW_CONFIG_FILE: str = "workflow.json"
    
    # 沙盒服务配置
    SANDBOX_URL: Optional[str] = None
    
    # 应用配置
    APP_NAME: str = "OA系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # CORS配置
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:8080"
    
    @property
    def allowed_origins(self) -> List[str]:
        """获取允许的源列表"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# 创建全局配置实例
settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.LOG_DIR, exist_ok=True)
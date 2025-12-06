from pydantic_settings import BaseSettings
import os
from loguru import logger

class Settings(BaseSettings):
    APP_NAME: str = "数据分析沙箱"
    DEBUG: bool = False
    SANDBOX_BASE: str = os.path.abspath("sandboxes")
    SANDBOX_RETENTION_HOURS: int = 24
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保沙盒目录存在
        os.makedirs(self.SANDBOX_BASE, exist_ok=True)
        logger.info(f"沙盒基础目录: {self.SANDBOX_BASE}")

settings = Settings()
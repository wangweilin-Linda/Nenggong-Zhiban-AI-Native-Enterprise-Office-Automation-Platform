from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "数据分析沙箱"
    DEBUG: bool = False
    SANDBOX_RETENTION_HOURS: int = 24
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"
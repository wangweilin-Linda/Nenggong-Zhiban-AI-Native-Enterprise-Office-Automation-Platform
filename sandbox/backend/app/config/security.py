from pathlib import Path
import tempfile
import os

class SecurityConfig:
    # 修改允许的文件类型
    ALLOWED_EXTENSIONS = {'.csv'}  # 改为只允许 CSV 文件
    
    # 最大文件大小 (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # 临时文件目录
    TEMP_DIR = os.getenv('TEMP_DIR', '/app/temp')
    
    # 文件保留最长时间（秒）
    FILE_RETENTION_TIME = 300
    
    @classmethod
    def is_file_allowed(cls, filename: str) -> bool:
        return Path(filename).suffix.lower() in cls.ALLOWED_EXTENSIONS
    
    @classmethod
    def get_temp_dir(cls) -> str:
        return cls.TEMP_DIR
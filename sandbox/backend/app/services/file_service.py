import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from ..config.security import SecurityConfig

class FileService:
    @staticmethod
    async def save_upload_file(file_content: bytes, original_filename: str) -> Optional[str]:
        if not SecurityConfig.is_file_allowed(original_filename):
            return None
            
        if len(file_content) > SecurityConfig.MAX_FILE_SIZE:
            return None
            
        # 生成安全的文件名
        safe_filename = f"{uuid.uuid4()}{Path(original_filename).suffix}"
        file_path = os.path.join(SecurityConfig.get_temp_dir(), safe_filename)
        
        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(file_content)
            
        return file_path
    
    @staticmethod
    async def cleanup_old_files():
        """清理超过保留时间的临时文件"""
        retention_time = datetime.now() - timedelta(seconds=SecurityConfig.FILE_RETENTION_TIME)
        
        for file in Path(SecurityConfig.get_temp_dir()).glob('*'):
            if file.stat().st_mtime < retention_time.timestamp():
                try:
                    file.unlink()
                except Exception:
                    pass
import os
import shutil
from pathlib import Path
from typing import Optional
import hashlib
from datetime import datetime
import secrets

class SecurityManager:
    def __init__(self):
        self.data_dir = Path("/app/data")
        self.data_dir.mkdir(exist_ok=True, mode=0o700)

    def create_secure_workspace(self) -> Path:
        """创建安全的临时工作目录"""
        workspace_id = secrets.token_hex(16)
        workspace = self.data_dir / workspace_id
        workspace.mkdir(mode=0o700)
        return workspace

    def secure_save_file(self, file_content: bytes, workspace: Path) -> Path:
        """安全地保存文件"""
        file_hash = hashlib.sha256(file_content).hexdigest()
        file_path = workspace / f"{file_hash}.xlsx"
        file_path.write_bytes(file_content)
        file_path.chmod(0o600)
        return file_path

    def cleanup_workspace(self, workspace: Path):
        """安全清理工作目录"""
        if workspace.exists() and workspace.is_relative_to(self.data_dir):
            shutil.rmtree(workspace, ignore_errors=True)
from fastapi import HTTPException
from typing import Any, Dict, Optional

class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        message: str,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.data = data

class FileProcessError(AppException):
    def __init__(self, message: str, data: Optional[Any] = None):
        super().__init__(status_code=400, message=message, data=data)

class AnalysisError(AppException):
    def __init__(self, message: str, data: Optional[Any] = None):
        super().__init__(status_code=400, message=message, data=data)

class ValidationError(AppException):
    def __init__(self, message: str, data: Optional[Any] = None):
        super().__init__(status_code=422, message=message, data=data)

class SecurityError(AppException):
    def __init__(self, message: str, data: Optional[Any] = None):
        super().__init__(status_code=403, message=message, data=data)
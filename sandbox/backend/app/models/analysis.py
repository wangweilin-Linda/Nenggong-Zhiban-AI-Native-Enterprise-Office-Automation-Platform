from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AnalysisResult(BaseModel):
    summary: Dict[str, Any]
    charts: Dict[str, Any]
    created_at: datetime = datetime.now()

class AnalysisTask(BaseModel):
    task_id: str = str(uuid.uuid4())
    name: str
    status: AnalysisStatus = AnalysisStatus.PENDING
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    result: Optional[AnalysisResult] = None
    parameters: Dict[str, Any] = {}
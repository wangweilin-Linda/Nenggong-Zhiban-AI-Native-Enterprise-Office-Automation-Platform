from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TimestampModel(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
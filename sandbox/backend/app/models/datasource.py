from typing import Optional
from .base import TimestampModel
from pydantic import Field, HttpUrl

class DataSource(TimestampModel):
    source_id: str = Field(..., description="数据源ID")
    name: str = Field(..., description="数据源名称")
    type: str = Field(..., description="数据源类型")
    connection_string: str = Field(..., description="连接字符串")
    description: Optional[str] = Field(default=None, description="数据源描述")
    metadata: dict = Field(default_factory=dict, description="元数据")
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from pydantic import BaseModel, field_validator


class ModelConfig(SQLModel, table=True):
    """模型配置表"""
    
    __tablename__ = "model_config"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # 配置类型: chat（聊天模型）或 embedding（向量化模型）
    config_type: str = Field(index=True)
    # 模型名称，如 qwen-turbo, text-embedding-v3
    model_name: str
    # API Key
    api_key: str
    # API Base URL
    base_url: str
    # 是否启用（每种类型只能有一个启用）
    is_active: bool = Field(default=False)
    # 备注
    remark: Optional[str] = None
    # 创建时间
    created_at: datetime = Field(default_factory=datetime.now)
    # 更新时间
    updated_at: datetime = Field(default_factory=datetime.now)


class ModelConfigCreate(SQLModel):
    """创建模型配置"""
    config_type: str
    model_name: str
    api_key: str
    base_url: str
    is_active: bool = False
    remark: Optional[str] = None


class ModelConfigUpdate(SQLModel):
    """更新模型配置"""
    config_type: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None
    remark: Optional[str] = None


class ModelConfigFormat(SQLModel):
    """模型配置（格式化日期）"""
    
    id: uuid.UUID
    config_type: str
    model_name: str
    api_key: str
    base_url: str
    is_active: bool
    remark: Optional[str] = None
    created_at: str
    updated_at: str
    
    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def format_date(cls, value):
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value


class ModelConfigResponse(BaseModel):
    """响应体"""
    code: int
    message: str
    data: Optional[ModelConfigFormat] = None


class ModelConfigListResponse(BaseModel):
    """列表响应体"""
    code: int
    message: str
    data: list[ModelConfigFormat]

import uuid
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from sqlmodel import Session, select
from models.model_config_model import (
    ModelConfig,
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigFormat,
)
from .base import engine


class ModelConfigCrud:
    """模型配置 CRUD 操作"""
    
    def get_all(self) -> list[ModelConfigFormat]:
        """获取所有模型配置"""
        with Session(engine) as session:
            query = select(ModelConfig)
            configs = session.exec(query).all()
            return [ModelConfigFormat.model_validate(c) for c in configs]
    
    def get_by_type(self, config_type: str) -> list[ModelConfigFormat]:
        """根据类型获取模型配置"""
        with Session(engine) as session:
            query = select(ModelConfig).where(ModelConfig.config_type == config_type)
            configs = session.exec(query).all()
            return [ModelConfigFormat.model_validate(c) for c in configs]
    
    def get_active(self, config_type: str) -> Optional[ModelConfig]:
        """获取当前启用的模型配置"""
        with Session(engine) as session:
            query = select(ModelConfig).where(
                ModelConfig.config_type == config_type,
                ModelConfig.is_active == True
            )
            return session.exec(query).first()
    
    def get_by_id(self, config_id: uuid.UUID) -> ModelConfig:
        """根据 ID 获取模型配置"""
        with Session(engine) as session:
            config = session.get(ModelConfig, config_id)
            if not config:
                raise HTTPException(status_code=404, detail="模型配置未找到")
            return config
    
    def create(self, data: ModelConfigCreate) -> ModelConfigFormat:
        """创建模型配置"""
        with Session(engine) as session:
            # 如果设置为启用，则禁用同类型的其他配置
            if data.is_active:
                self._deactivate_others(session, data.config_type, None)
            
            config = ModelConfig.model_validate(data)
            session.add(config)
            session.commit()
            session.refresh(config)
            return ModelConfigFormat.model_validate(config)
    
    def update(self, config_id: uuid.UUID, data: ModelConfigUpdate) -> ModelConfigFormat:
        """更新模型配置"""
        with Session(engine) as session:
            config = session.get(ModelConfig, config_id)
            if not config:
                raise HTTPException(status_code=404, detail="模型配置未找到")
            
            # 如果设置为启用，则禁用同类型的其他配置
            if data.is_active:
                config_type = data.config_type or config.config_type
                self._deactivate_others(session, config_type, config_id)
            
            update_data = data.model_dump(exclude_unset=True)
            update_data["updated_at"] = datetime.now()
            config.sqlmodel_update(update_data)
            session.add(config)
            session.commit()
            session.refresh(config)
            return ModelConfigFormat.model_validate(config)
    
    def delete(self, config_id: uuid.UUID) -> None:
        """删除模型配置"""
        with Session(engine) as session:
            config = session.get(ModelConfig, config_id)
            if not config:
                raise HTTPException(status_code=404, detail="模型配置未找到")
            session.delete(config)
            session.commit()
    
    def set_active(self, config_id: uuid.UUID) -> ModelConfigFormat:
        """设置为当前启用的配置"""
        with Session(engine) as session:
            config = session.get(ModelConfig, config_id)
            if not config:
                raise HTTPException(status_code=404, detail="模型配置未找到")
            
            # 禁用同类型的其他配置
            self._deactivate_others(session, config.config_type, config_id)
            
            # 启用当前配置
            config.is_active = True
            config.updated_at = datetime.now()
            session.add(config)
            session.commit()
            session.refresh(config)
            return ModelConfigFormat.model_validate(config)
    
    def _deactivate_others(self, session: Session, config_type: str, exclude_id: Optional[uuid.UUID]):
        """禁用同类型的其他配置"""
        query = select(ModelConfig).where(
            ModelConfig.config_type == config_type,
            ModelConfig.is_active == True
        )
        if exclude_id:
            query = query.where(ModelConfig.id != exclude_id)
        
        for config in session.exec(query).all():
            config.is_active = False
            config.updated_at = datetime.now()
            session.add(config)
    
    def init_default_configs(self):
        """初始化默认的阿里千问配置"""
        with Session(engine) as session:
            # 检查是否已有配置
            existing = session.exec(select(ModelConfig)).first()
            if existing:
                return  # 已有配置，不再初始化
            
            # 阿里千问默认配置
            qwen_api_key = "sk-f71c126cb6754e3cbdbc382815ff5d96"
            qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            
            # 创建聊天模型配置
            chat_config = ModelConfig(
                config_type="chat",
                model_name="qwen-turbo",
                api_key=qwen_api_key,
                base_url=qwen_base_url,
                is_active=True,
                remark="阿里千问聊天模型"
            )
            session.add(chat_config)
            
            # 创建向量化模型配置
            embedding_config = ModelConfig(
                config_type="embedding",
                model_name="text-embedding-v3",
                api_key=qwen_api_key,
                base_url=qwen_base_url,
                is_active=True,
                remark="阿里千问向量化模型"
            )
            session.add(embedding_config)
            
            session.commit()


# 单例
model_config_crud = ModelConfigCrud()

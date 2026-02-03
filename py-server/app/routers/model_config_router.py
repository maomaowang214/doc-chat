import uuid
from fastapi import APIRouter
from crud.model_config_crud import model_config_crud
from models.model_config_model import (
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse,
    ModelConfigListResponse,
)

router = APIRouter(prefix="/model-config", tags=["模型配置"])


@router.get("/list", response_model=ModelConfigListResponse, summary="获取所有模型配置")
def get_all_configs():
    """获取所有模型配置列表"""
    configs = model_config_crud.get_all()
    return ModelConfigListResponse(code=200, message="获取成功", data=configs)


@router.get("/list/{config_type}", response_model=ModelConfigListResponse, summary="根据类型获取模型配置")
def get_configs_by_type(config_type: str):
    """根据类型获取模型配置列表（chat 或 embedding）"""
    configs = model_config_crud.get_by_type(config_type)
    return ModelConfigListResponse(code=200, message="获取成功", data=configs)


@router.post("/add", response_model=ModelConfigResponse, summary="添加模型配置")
def add_config(data: ModelConfigCreate):
    """添加新的模型配置"""
    config = model_config_crud.create(data)
    return ModelConfigResponse(code=200, message="添加成功", data=config)


@router.put("/update/{config_id}", response_model=ModelConfigResponse, summary="更新模型配置")
def update_config(config_id: uuid.UUID, data: ModelConfigUpdate):
    """更新模型配置"""
    config = model_config_crud.update(config_id, data)
    return ModelConfigResponse(code=200, message="更新成功", data=config)


@router.delete("/delete/{config_id}", summary="删除模型配置")
def delete_config(config_id: uuid.UUID):
    """删除模型配置"""
    model_config_crud.delete(config_id)
    return {"code": 200, "message": "删除成功"}


@router.put("/set-active/{config_id}", response_model=ModelConfigResponse, summary="设置为启用")
def set_active(config_id: uuid.UUID):
    """设置指定配置为当前启用的配置"""
    config = model_config_crud.set_active(config_id)
    return ModelConfigResponse(code=200, message="设置成功", data=config)


@router.post("/init-default", summary="初始化默认配置")
def init_default():
    """初始化默认的阿里千问配置"""
    model_config_crud.init_default_configs()
    return {"code": 200, "message": "初始化成功"}

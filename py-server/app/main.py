import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from crud.base import create_db_and_tables

from routers.base import failure

# 导入 fastApi 子模块
from routers import chat_router
from routers import chat_session_router
from routers import document_router
from routers import model_config_router

# API 标签元数据
tags_metadata = [
    {
        "name": "chat",
        "description": "智能对话接口，基于 RAG 检索增强生成的问答功能",
    },
    {
        "name": "session",
        "description": "会话管理接口，包括会话的创建、查询、更新和删除",
    },
    {
        "name": "documents",
        "description": "文档管理接口，支持文档上传、解析、向量化存储和查询",
    },
    {
        "name": "模型配置",
        "description": "模型配置接口，管理聊天模型和向量化模型的配置",
    },
]

# FastAPI 主入口
app = FastAPI(
    title="文档问答系统 API",
    description="""
## 基于 LangChain + DeepSeek 的智能文档问答系统

### 功能模块

* **聊天对话** - 基于 RAG 的智能问答
* **会话管理** - 聊天会话的创建和管理
* **文档管理** - 文档上传、解析和向量化存储

### 技术栈

- FastAPI + SQLModel
- LangChain + Ollama
- ChromaDB 向量数据库
- DeepSeek / 本地大模型
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",           # Swagger UI 路径
    redoc_url="/redoc",         # ReDoc 路径
    openapi_url="/openapi.json" # OpenAPI schema 路径
)

# 将 fastApi 子模块整合到 app 中
app.include_router(chat_router.router)
app.include_router(chat_session_router.router)
app.include_router(document_router.router)
app.include_router(model_config_router.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """
    重写 fastApi 错误信息
    """
    return JSONResponse(
        failure(exc.status_code, exc.detail), status_code=exc.status_code
    )


@app.get("/")
def read_root():
    return {"code": 200, "message": "已启动服务。"}


if __name__ == "__main__":
    # 创建或启动数据库
    create_db_and_tables()
    # 启动 uvicorn 服务
    uvicorn.run("main:app", port=8082, log_level="info", reload=True)

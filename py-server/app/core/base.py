import os
from pathlib import Path
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.callbacks import StreamingStdOutCallbackHandler
from langchain_core.embeddings import Embeddings


"""
基本设置
"""

# 获取项目根目录（app 的父目录）
_BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOAD_PATH = str(_BASE_DIR / "fileStorage")
"""指定加载文档的目录"""

VECTOR_DIR = str(_BASE_DIR / "vector_store")
"""指定持久化向量数据库的存储路径"""

# 自动创建目录（如果不存在）
os.makedirs(LOAD_PATH, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)

COLLECTION_NAME = "documents_qa"
"""向量数据库的集合名"""


def _get_model_config(config_type: str) -> Optional[dict]:
    """从数据库获取模型配置"""
    try:
        from crud.model_config_crud import model_config_crud
        config = model_config_crud.get_active(config_type)
        if config:
            return {
                "model_name": config.model_name,
                "api_key": config.api_key,
                "base_url": config.base_url,
            }
    except Exception as e:
        print(f"获取模型配置失败: {e}")
    return None


def chat_llm():
    """LLM 聊天模型 - 使用阿里千问或其他 OpenAI 兼容 API"""
    from langchain_openai import ChatOpenAI
    
    # 从数据库获取聊天模型配置
    config = _get_model_config("chat")
    
    if config:
        llm = ChatOpenAI(
            model=config["model_name"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )
    else:
        # 默认配置（阿里千问）
        llm = ChatOpenAI(
            model="qwen-turbo",
            api_key="sk-f71c126cb6754e3cbdbc382815ff5d96",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )
    
    return llm


def chroma_vector_store():
    """Chroma 向量数据库"""

    return Chroma(
        persist_directory=VECTOR_DIR,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings_model(),
    )


def embeddings_model():
    """Embedding 模型 - 使用阿里千问 DashScope"""
    from langchain_community.embeddings import DashScopeEmbeddings
    
    # 从数据库获取向量化模型配置
    config = _get_model_config("embedding")
    
    if config:
        embeddings = DashScopeEmbeddings(
            model=config["model_name"],
            dashscope_api_key=config["api_key"],
        )
    else:
        # 默认配置（阿里千问）
        embeddings = DashScopeEmbeddings(
            model="text-embedding-v3",
            dashscope_api_key="sk-f71c126cb6754e3cbdbc382815ff5d96",
        )
    
    return embeddings

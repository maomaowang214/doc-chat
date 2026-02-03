from typing import Optional
import uuid
from pydantic import BaseModel


class Chatting(BaseModel):
    """对话内容"""

    role: str
    content: str


class ChatParams(BaseModel):
    """对话聊天请求数据"""

    model: Optional[str] = None
    stream: Optional[bool] = None
    messages: Optional[Chatting] = None
    chat_session_id: Optional[uuid.UUID] = None
    use_knowledge: Optional[bool] = True  # 是否使用知识库，默认为 True


class ChatStreamResponse(BaseModel):
    """流式响应"""

    model: str
    created_at: int
    message: Chatting
    done: bool
    done_reason: Optional[str] = None

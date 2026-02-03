from typing import Annotated
import uuid
import asyncio
import json
from fastapi import APIRouter, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from core.langchain_vector import (
    vector_documents, 
    vector_documents_async,
    get_vector_progress,
    vector_progress
)
from crud.document_crud import DocumentCrud
from models.document_model import (
    DocumentParams,
    DocumentResponse,
    UpdateFormData,
    UploadFormData,
)
from urllib.parse import quote
from routers.base import success


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={404: {"message": "您所访问的资源不存在！"}},
)

document_crud = DocumentCrud()


# 向量化任务锁，防止重复执行
vectorizing_lock = asyncio.Lock()


@router.post("/add")
async def add_doc(data: Annotated[UploadFormData, Form()]):
    await document_crud.add(data)
    return success(None, "添加成功！")


@router.put("/update")
async def update_doc(data: Annotated[UpdateFormData, Form()]):
    await document_crud.update(data)
    return success(None, "更新成功！")


@router.get("/page", response_model=DocumentResponse)
async def page_doc(params: Annotated[DocumentParams, Query()]):
    result = document_crud.page(params)
    return success(result)


@router.delete("/delete")
async def del_doc(data: DocumentParams):
    await document_crud.delete(data.id)
    return success(None, "删除成功！")


@router.get("/read/{item_id}")
async def read_doc_file(item_id: uuid.UUID):
    file_path, real_name = document_crud.download(item_id)
    header_file_name = quote(real_name, encoding="utf-8")
    headers = {"Content-Disposition": f"inline; filename*=UTF-8''{header_file_name}"}
    return FileResponse(path=file_path, headers=headers, media_type=None)


@router.get("/vector-all")
async def vector_docs():
    """同步向量化（阻塞式，用于简单场景）"""
    vector_documents()
    document_crud.vector_all_docs()
    return success(None, "已全部向量化。")


async def vectorize_task():
    """后台向量化任务"""
    try:
        await vector_documents_async()
        document_crud.vector_all_docs()
    except Exception as e:
        print(f"向量化任务失败: {e}")


async def progress_event_generator():
    """SSE 进度事件生成器"""
    global vector_progress
    
    last_status = None
    retry_count = 0
    max_idle_retries = 300  # 最多等待 5 分钟
    
    while True:
        progress_data = get_vector_progress()
        current_status = progress_data.get("status")
        
        # 发送进度数据
        yield f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"
        
        # 检查是否完成或出错
        if current_status in ["completed", "error"]:
            # 发送最终状态后退出
            await asyncio.sleep(0.5)
            yield f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"
            break
        
        # 检查是否空闲太久
        if current_status == "idle":
            retry_count += 1
            if retry_count > max_idle_retries:
                yield f"data: {json.dumps({'status': 'timeout', 'message': '等待超时'}, ensure_ascii=False)}\n\n"
                break
        else:
            retry_count = 0
        
        last_status = current_status
        await asyncio.sleep(0.5)  # 每 500ms 更新一次


@router.get("/vector-all-stream")
async def vector_docs_stream(background_tasks: BackgroundTasks):
    """
    流式向量化（SSE 推送进度）
    返回 Server-Sent Events 格式的进度信息
    """
    global vectorizing_lock, vector_progress
    
    # 检查是否正在向量化
    if vector_progress.status not in ["idle", "completed", "error"]:
        return StreamingResponse(
            progress_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    # 重置进度并启动后台任务
    vector_progress.reset()
    background_tasks.add_task(vectorize_task)
    
    # 返回 SSE 流
    return StreamingResponse(
        progress_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/vector-progress")
async def get_progress():
    """获取当前向量化进度"""
    return success(get_vector_progress())

import unicodedata
import os
import json
import asyncio
from typing import Callable, Optional, Generator, Any
from fastapi import HTTPException
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    JSONLoader,
    CSVLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import time

from .base import LOAD_PATH, VECTOR_DIR, chroma_vector_store


# 全局进度状态
class VectorProgress:
    """向量化进度管理"""
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.status = "idle"  # idle, loading, splitting, vectorizing, completed, error
        self.current = 0
        self.total = 0
        self.message = ""
        self.error = None
        self.start_time = None
        self.batch_current = 0
        self.batch_total = 0
    
    def to_dict(self):
        elapsed = 0
        if self.start_time:
            elapsed = round(time.time() - self.start_time, 1)
        return {
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "error": self.error,
            "elapsed": elapsed,
            "batch_current": self.batch_current,
            "batch_total": self.batch_total,
            "progress": round(self.current / self.total * 100, 1) if self.total > 0 else 0
        }


# 全局进度实例
vector_progress = VectorProgress()


def clean_text(text: str) -> str:
    """统一文本清洗函数"""

    cleaned = ""
    if not text.strip():
        return cleaned
    # 1. 标准化全角字符（字母、数字、标点）为半角
    normalized = unicodedata.normalize("NFKC", text)
    # 2. 删除所有空格（包括全角空格\u3000和普通空格）
    cleaned = normalized.replace("\u3000", "").replace(" ", "")
    # 3. 中文标点替换为英文标点（按需扩展）
    replacements = {
        "，": ",",
        "。": ".",
        "（": "(",
        "）": ")",
        "；": ";",
        "：": ":",
        "！": "!",
        "？": "?",
    }
    for cn, en in replacements.items():
        cleaned = cleaned.replace(cn, en)
    return cleaned


def is_alpaca_format(item: dict) -> bool:
    """检测是否是 Alpaca 数据集格式"""
    alpaca_keys = {"instruction", "input", "output"}
    return alpaca_keys.issubset(set(item.keys()))


def convert_alpaca_to_text(item: dict) -> str:
    """将 Alpaca 格式数据转换为适合向量化的文本"""
    parts = []
    
    # 处理 instruction
    if item.get("instruction"):
        parts.append(f"指令：{item['instruction']}")
    
    # 处理 input (问题)
    if item.get("input"):
        parts.append(f"问题：{item['input']}")
    
    # 处理 output (答案)
    if item.get("output"):
        # 对于很长的输出，保留关键内容
        output = item["output"]
        parts.append(f"回答：{output}")
    
    # 处理 system
    if item.get("system"):
        parts.append(f"系统提示：{item['system']}")
    
    return "\n\n".join(parts)


def load_json_files(source_dir: str) -> list[Document]:
    """
    加载 JSON 文件
    支持格式：
    1. Alpaca 数据集格式 (instruction, input, output)
    2. 标准 JSON 对象或数组
    3. JSON Lines 格式（每行一个 JSON 对象）
    """
    global vector_progress
    docs = []
    json_files = []
    
    # 递归查找所有 JSON 文件
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    
    for file_path in json_files:
        try:
            vector_progress.message = f"正在加载: {os.path.basename(file_path)}"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析 JSON
            try:
                data = json.loads(content)
                
                if isinstance(data, list):
                    total_items = len(data)
                    print(f"JSON 文件包含 {total_items} 条数据")
                    
                    # 检测是否是 Alpaca 格式
                    is_alpaca = total_items > 0 and is_alpaca_format(data[0])
                    if is_alpaca:
                        print(f"检测到 Alpaca 数据集格式")
                    
                    for idx, item in enumerate(data):
                        if isinstance(item, dict):
                            if is_alpaca:
                                # Alpaca 格式：智能转换为问答文本
                                text = convert_alpaca_to_text(item)
                            else:
                                text = json.dumps(item, ensure_ascii=False, indent=2)
                            
                            if text.strip():
                                docs.append(Document(
                                    page_content=text,
                                    metadata={
                                        "source": file_path,
                                        "type": "alpaca" if is_alpaca else "json",
                                        "index": idx
                                    }
                                ))
                        
                        # 每 100 条更新一次进度
                        if (idx + 1) % 100 == 0:
                            vector_progress.message = f"加载 JSON: {idx + 1}/{total_items}"
                            print(f"已加载 {idx + 1}/{total_items} 条数据")
                            
                elif isinstance(data, dict):
                    if is_alpaca_format(data):
                        text = convert_alpaca_to_text(data)
                    else:
                        text = json.dumps(data, ensure_ascii=False, indent=2)
                    docs.append(Document(
                        page_content=text,
                        metadata={"source": file_path, "type": "json"}
                    ))
                    
            except json.JSONDecodeError:
                # JSON Lines 格式
                lines = content.strip().split('\n')
                for line in lines:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            if is_alpaca_format(item):
                                text = convert_alpaca_to_text(item)
                            else:
                                text = json.dumps(item, ensure_ascii=False, indent=2)
                            docs.append(Document(
                                page_content=text,
                                metadata={"source": file_path, "type": "jsonl"}
                            ))
                        except json.JSONDecodeError:
                            continue
            
            print(f"成功加载 JSON 文件: {file_path}, 共 {len(docs)} 条记录")
        except Exception as e:
            print(f"加载 JSON 文件失败 {file_path}: {str(e)}")
    
    return docs


def load_csv_files(source_dir: str) -> list[Document]:
    """
    加载 CSV 文件
    每行数据作为一个文档
    """
    docs = []
    csv_files = []
    
    # 递归查找所有 CSV 文件
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(os.path.join(root, file))
    
    for file_path in csv_files:
        try:
            loader = CSVLoader(
                file_path=file_path,
                encoding='utf-8',
            )
            csv_docs = loader.load()
            docs.extend(csv_docs)
            print(f"成功加载 CSV 文件: {file_path}, 共 {len(csv_docs)} 条记录")
        except Exception as e:
            # 尝试其他编码
            try:
                loader = CSVLoader(
                    file_path=file_path,
                    encoding='gbk',
                )
                csv_docs = loader.load()
                docs.extend(csv_docs)
                print(f"成功加载 CSV 文件 (GBK编码): {file_path}, 共 {len(csv_docs)} 条记录")
            except Exception as e2:
                print(f"加载 CSV 文件失败 {file_path}: {str(e2)}")
    
    return docs


def load_documents(source_dir=LOAD_PATH):
    """
    加载指定目录下的所有文档
    支持格式：.txt, .pdf, .docx, .md, .json, .csv
    """

    try:
        # 分别加载不同格式
        text_loader = DirectoryLoader(
            path=source_dir,  # 指定读取文件的父目录
            glob=["**/*.txt", "**/*.md"],  # 指定读取文件的格式
            show_progress=True,  # 显示加载进度
            use_multithreading=True,  # 使用多线程
            loader_cls=TextLoader,  # 指定加载器
            loader_kwargs={"autodetect_encoding": True},  # 自动检测文件编码
        )

        pdf_loader = DirectoryLoader(
            path=source_dir,
            glob="**/*.pdf",
            show_progress=True,
            use_multithreading=True,
            loader_cls=PyPDFLoader,
        )

        docx_loader = DirectoryLoader(
            path=source_dir,
            glob="**/*.docx",
            show_progress=True,
            use_multithreading=True,
            loader_cls=Docx2txtLoader,
            loader_kwargs={"autodetect_encoding": True},
        )

        # 初步清洗 PDF 文档的文本，删除多余空格。
        pdf_docs = pdf_loader.load()
        for doc in pdf_docs:
            doc.page_content = clean_text(doc.page_content)

        # 加载 JSON 和 CSV 文件
        json_docs = load_json_files(source_dir)
        csv_docs = load_csv_files(source_dir)

        # 合并文档列表
        docs = []
        docs.extend(text_loader.load())
        docs.extend(pdf_docs)
        docs.extend(docx_loader.load())
        docs.extend(json_docs)
        docs.extend(csv_docs)
        
        print(f"成功加载 {len(docs)} 份文档")
        print(f"  - 文本/Markdown: {len(text_loader.load())} 份")
        print(f"  - PDF: {len(pdf_docs)} 份")
        print(f"  - JSON: {len(json_docs)} 份")
        print(f"  - CSV: {len(csv_docs)} 份")
        
        return docs
    except Exception as e:
        print(f"加载文档失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"加载文档失败：{str(e)}")


def split_documents(documents, chunk_size=800, chunk_overlap=150):
    """
    使用递归字符分割器处理文本
    参数说明：
    - chunk_size：每个文本块的最大字符数，推荐 500-1000
    - chunk_overlap：相邻块之间的重叠字符数（保持上下文连贯），推荐 100-200
    """
    # 过滤掉空文档
    valid_documents = [
        doc for doc in documents
        if doc.page_content and isinstance(doc.page_content, str) and doc.page_content.strip()
    ]
    
    if len(valid_documents) < len(documents):
        print(f"警告：过滤掉 {len(documents) - len(valid_documents)} 个空文档")
    
    if not valid_documents:
        print("警告：没有有效文档需要分割")
        return []
    
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", "。", "!", "?", "？", "！", "；", ";"],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,  # 保留原始文档中的位置信息
    )

    split_docs = text_splitter.split_documents(valid_documents)
    print(f"原始文档数：{len(documents)}（有效：{len(valid_documents)}）")
    print(f"分割后文本块数：{len(split_docs)}")

    return split_docs


def create_vector_store(split_docs, persist_dir=VECTOR_DIR, batch_size: int = 50):
    """
    创建持久化向量数据库（支持批量处理和进度更新）
    - split_docs: 经过分割的文档列表
    - persist_dir: 向量数据库存储路径
    - batch_size: 每批次处理的文档数量（默认50，适合大文件）
    """
    global vector_progress
    
    vector_progress.status = "vectorizing"
    vector_progress.message = "正在初始化向量数据库..."

    # 初始化 Chroma 向量数据库
    vector_store = chroma_vector_store()

    # 向量化文档之前，先把原来集合里的数据清空
    vector_progress.message = "正在清空旧数据..."
    ids = vector_store._collection.get()["ids"]
    if len(ids):
        vector_store.delete(ids=vector_store._collection.get()["ids"])

    # 如果分割文档为空，不做向量化操作
    if not split_docs or len(split_docs) == 0:
        vector_progress.status = "completed"
        vector_progress.message = "没有文档需要向量化"
        return

    # 过滤掉 page_content 为空或非字符串的文档块
    valid_docs = [
        doc for doc in split_docs
        if doc.page_content and isinstance(doc.page_content, str) and doc.page_content.strip()
    ]
    
    if not valid_docs:
        print("警告：所有文档块的内容为空，跳过向量化")
        vector_progress.status = "completed"
        vector_progress.message = "所有文档块内容为空"
        return
    
    print(f"过滤前文档块数：{len(split_docs)}，过滤后有效文档块数：{len(valid_docs)}")
    
    # 调试：打印前几个文档块的内容类型和长度
    for i, doc in enumerate(valid_docs[:3]):
        print(f"文档块{i}: type={type(doc.page_content)}, len={len(doc.page_content)}, content[:50]={repr(doc.page_content[:50])}")

    try:
        start_time = time.time()
        total_docs = len(valid_docs)
        
        # 设置进度
        vector_progress.total = total_docs
        vector_progress.current = 0
        vector_progress.batch_total = (total_docs + batch_size - 1) // batch_size
        vector_progress.batch_current = 0
        
        print(f"\n开始向量化====>")
        print(f"总文档数: {total_docs}, 批次大小: {batch_size}, 总批次: {vector_progress.batch_total}")

        # 批量处理文档
        for i in range(0, total_docs, batch_size):
            batch_end = min(i + batch_size, total_docs)
            batch_docs = valid_docs[i:batch_end]
            batch_num = i // batch_size + 1
            
            vector_progress.batch_current = batch_num
            vector_progress.current = i
            vector_progress.message = f"正在向量化: 批次 {batch_num}/{vector_progress.batch_total} ({i}/{total_docs})"
            
            print(f"处理批次 {batch_num}/{vector_progress.batch_total}: 文档 {i+1}-{batch_end}")
            
            # 向量化当前批次
            vector_store.add_documents(batch_docs)
            
            # 更新进度
            vector_progress.current = batch_end
            
            # 计算预估剩余时间
            elapsed = time.time() - start_time
            if batch_num > 0:
                avg_time_per_batch = elapsed / batch_num
                remaining_batches = vector_progress.batch_total - batch_num
                eta = avg_time_per_batch * remaining_batches
                print(f"  已完成 {batch_end}/{total_docs} ({(batch_end/total_docs*100):.1f}%), 预计剩余 {eta:.1f} 秒")

        # 完成
        vector_progress.current = total_docs
        vector_progress.status = "completed"
        vector_progress.message = f"向量化完成！共 {total_docs} 个文档块"
        
        elapsed_total = time.time() - start_time
        print(f"\n向量化完成！耗时 {elapsed_total:.2f} 秒")
        print(f"数据库存储路径：{persist_dir}")
        print(f"总文档块数：{vector_store._collection.count()}")
        print(f"平均每文档耗时：{(elapsed_total/total_docs*1000):.2f} 毫秒")

    except Exception as e:
        vector_progress.status = "error"
        vector_progress.error = str(e)
        vector_progress.message = f"向量化失败：{str(e)}"
        print(f"向量化失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"向量化失败：{str(e)}")


def vector_documents():
    """
    启动文档向量化，并保存数据库
    """
    global vector_progress
    
    try:
        vector_progress.reset()
        vector_progress.start_time = time.time()
        
        # 阶段1：加载文档
        vector_progress.status = "loading"
        vector_progress.message = "正在加载文档..."
        documents = load_documents()
        
        # 阶段2：分割文档
        vector_progress.status = "splitting"
        vector_progress.message = f"正在分割 {len(documents)} 个文档..."
        split_docs = split_documents(documents)
        
        # 阶段3：向量化（内部会更新进度）
        create_vector_store(split_docs)
        
    except Exception as e:
        vector_progress.status = "error"
        vector_progress.error = str(e)
        vector_progress.message = f"处理失败：{str(e)}"
        raise


def get_vector_progress() -> dict:
    """获取当前向量化进度"""
    global vector_progress
    return vector_progress.to_dict()


async def vector_documents_async():
    """
    异步执行向量化（用于 SSE 推送进度）
    """
    import asyncio
    
    # 在线程池中执行同步操作
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, vector_documents)

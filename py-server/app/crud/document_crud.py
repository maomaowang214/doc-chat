import os
from pathlib import Path
import uuid
import aiofiles
import aiofiles.os
from fastapi import File, HTTPException, UploadFile
from sqlmodel import Session, desc, func, select
from models.document_model import (
    Document,
    DocumentFormat,
    DocumentParams,
    DocumentUpdate,
    UpdateFormData,
    UploadFormData,
)
from .base import engine
from core.base import LOAD_PATH


class DocumentCrud:
    # 直接使用 LOAD_PATH 作为文件存储目录
    __STORAGE_PATH = Path(LOAD_PATH)

    async def __save_file(self, file: UploadFile = File()):
        """I/O操作，写入文件"""

        old_file_name = os.path.basename(file.filename)
        # 生成唯一文件名称
        new_file_name = f"{uuid.uuid4()}{Path(old_file_name).suffix}"
        save_path = self.__STORAGE_PATH / new_file_name
        # 数据库中存储相对文件名（不含目录路径）
        new_file_path = new_file_name
        new_suffix = Path(old_file_name).suffix

        # 利用 aiofiles 保存文件到指定目录
        async with aiofiles.open(save_path, "wb") as buffer:
            while content := await file.read(1024000):  # 每次读取 1KB
                await buffer.write(content)
        return new_file_name, new_file_path, new_suffix

    async def __delete_file(self, path):
        """I/O操作，删除文件"""
        if await aiofiles.os.path.exists(str(path)):
            await aiofiles.os.remove(str(path))

    async def add(self, data: UploadFormData):
        """新增文档记录"""
        file = data.file
        new_file_name, new_file_path, new_suffix = await self.__save_file(file)
        doc = DocumentUpdate(
            name=data.name,
            file_name=new_file_name,
            file_path=new_file_path,
            suffix=new_suffix,
            vector="",
        )

        with Session(engine) as session:
            db_document = Document.model_validate(doc)
            session.add(db_document)
            session.commit()
            session.refresh(db_document)
            return db_document

    async def update(self, data: UpdateFormData):
        """修改文档记录"""
        file = data.file
        doc = DocumentUpdate(
            name=data.name,
            file_name=data.file_name,
            file_path=data.file_path,
            vector=data.vector,
        )

        with Session(engine) as session:
            db_document = session.get(Document, data.id)
            if not db_document:
                raise HTTPException(status_code=404, detail="找不到该记录。")

            if file:
                # 数据库查找旧的文件名，并删除文件
                old_path = self.__STORAGE_PATH / db_document.file_path
                await self.__delete_file(old_path)
                # 保存新的文件
                new_file_name, new_file_path, new_suffix = await self.__save_file(file)
                doc.file_name = new_file_name
                doc.file_path = new_file_path
                doc.suffix = new_suffix
                doc.vector = ""

            doc = doc.model_dump(exclude_unset=True)
            db_document.sqlmodel_update(doc)
            session.add(db_document)
            session.commit()
            session.refresh(db_document)
            return db_document

    async def delete(self, id: str):
        """删除文档记录，并删除文件"""
        with Session(engine) as session:
            document = session.get(Document, id)
            if not document:
                raise HTTPException(status_code=404, detail="文档未找到")

            file_path = self.__STORAGE_PATH / document.file_path
            await self.__delete_file(file_path)

            session.delete(document)
            session.commit()

    def page(self, params: DocumentParams):
        """查询文档记录，分页"""
        offset = params.page_num * params.page_size
        limit = params.page_size
        name = params.name
        with Session(engine) as session:
            count_query = select(func.count(Document.id))
            query = select(Document)

            # 根据 name 模糊查询，并查询总数
            if name:
                count_query = count_query.where(Document.name.contains(name))
                query = query.where(Document.name.contains(name))

            query.order_by(desc(Document.date)).offset(offset).limit(limit)

            total = session.exec(count_query).one()
            items = session.exec(query).all()
            list = [DocumentFormat.model_validate(d) for d in items]
            return {
                "total": total,
                "page_num": params.page_num,
                "page_size": params.page_size,
                "list": list,
            }

    def download(self, item_id: uuid.UUID):
        with Session(engine) as session:
            document = session.get(Document, item_id)
            if not document:
                raise HTTPException(status_code=404, detail="文档未找到")

            file_path = self.__STORAGE_PATH / document.file_path
            real_name = document.name + document.suffix

            return file_path, real_name

    def vector_all_docs(self):
        with Session(engine) as session:
            query = select(Document)
            doc_list = session.exec(query).all()
            for doc in doc_list:
                doc.vector = "yes"
                session.add(doc)
            session.commit()

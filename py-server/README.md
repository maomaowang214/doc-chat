# py-server

基于 [LangChain](https://github.com/langchain-ai/langchain) 的智能文档问答后端，支持 RAG 检索增强生成、流式对话、知识库向量化与模型配置管理。

**技术栈**：FastAPI + Uvicorn + SQLModel + SQLite + [Chroma](https://docs.trychroma.com/) + LangChain。  
默认使用阿里千问（DashScope）作为聊天与向量化模型，也可通过「模型配置」切换为其他 OpenAI 兼容 API。

---

## 功能概览

| 模块       | 说明 |
|------------|------|
| **聊天**   | 基于 RAG 的流式问答，支持会话历史、可选是否使用知识库 |
| **会话管理** | 会话的创建、列表、重命名、删除 |
| **文档/知识库** | 文档上传、分页查询、向量化构建；支持 PDF/TXT/DOC/DOCX/MD/JSON/CSV；大文件向量化支持 SSE 进度 |
| **模型配置** | 聊天模型与向量化模型的 API 配置管理（多套配置、启用切换） |

---

## 环境要求

- Python 3.10+
- 可选：已安装 [Ollama](https://ollama.com/) 并拉取模型（若使用本地模型）
- 或：阿里云 DashScope API Key（默认千问）

模型相关配置可在 `app/core/base.py` 中修改，或通过接口 `/model-config/*` 在运行时管理。

---

## 快速开始

```bash
# 进入项目目录
cd py-server

# 安装依赖
pip install -r requirements.txt

# 进入 app 目录并启动服务
cd app
python main.py
```

服务默认运行在 **http://127.0.0.1:8082**。  
- API 文档：http://127.0.0.1:8082/docs  
- ReDoc：http://127.0.0.1:8082/redoc  

首次启动会自动创建 SQLite 数据库 `document_qa.db` 及表结构，并可按需初始化默认模型配置。

---

## 项目结构

```
py-server/
├── app/
│   ├── core/                    # LangChain 与向量化核心
│   │   ├── base.py               # 路径、Chroma、LLM、Embedding 配置
│   │   ├── langchain_retrieval.py # RAG 检索链构建
│   │   └── langchain_vector.py   # 文档加载、分割、向量化（含批量与进度）
│   ├── crud/                     # 数据库 CRUD
│   │   ├── base.py               # 引擎与建表
│   │   ├── chat_history_crud.py
│   │   ├── chat_session_crud.py
│   │   ├── document_crud.py
│   │   └── model_config_crud.py
│   ├── models/                   # 数据模型
│   │   ├── chat_history_model.py
│   │   ├── chat_model.py
│   │   ├── chat_session_model.py
│   │   ├── document_model.py
│   │   └── model_config_model.py
│   ├── routers/                  # API 路由
│   │   ├── base.py               # 统一成功/失败响应
│   │   ├── chat_router.py        # 聊天与历史
│   │   ├── chat_session_router.py
│   │   ├── document_router.py    # 文档与向量化
│   │   └── model_config_router.py
│   ├── document_qa.db            # SQLite（运行后生成）
│   └── main.py                   # 应用入口
├── fileStorage/                  # 上传文档存储目录
├── vector_store/                 # Chroma 向量库持久化目录
├── requirements.txt
└── README.md
```

---

## 数据库表说明

### document

文档元信息与向量化状态。

| 字段       | 类型   | 说明         |
|------------|--------|--------------|
| id         | UUID   | 主键         |
| name       | str    | 文档名称     |
| file_name  | str    | 文件名       |
| file_path  | str    | 存储路径     |
| suffix     | str    | 后缀         |
| vector     | str    | 是否已向量化 yes/no |
| date       | datetime | 创建时间   |

### chatsession

会话表。

| 字段 | 类型     | 说明   |
|------|----------|--------|
| id   | UUID     | 主键   |
| title| str      | 标题   |
| date | datetime | 创建时间 |

### chathistory

单条聊天记录。

| 字段            | 类型     | 说明       |
|-----------------|----------|------------|
| id              | UUID     | 主键       |
| role            | str      | user/assistant |
| content         | str      | 内容       |
| think           | str      | 思考过程（可选） |
| chat_session_id | UUID     | 所属会话   |
| date            | datetime | 时间       |

### model_config

模型配置（聊天 / 向量化）。

| 字段        | 类型   | 说明           |
|-------------|--------|----------------|
| id          | UUID   | 主键           |
| config_type | str    | chat / embedding |
| model_name  | str    | 模型名         |
| api_key     | str    | API Key        |
| base_url    | str    | API 地址       |
| is_active   | bool   | 是否启用       |
| remark      | str    | 备注           |
| created_at  | datetime | 创建时间     |
| updated_at  | datetime | 更新时间     |

---

## API 接口概览

### 1. 聊天

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 流式对话，请求体含 `messages`、可选 `chat_session_id`、`use_knowledge`；响应 `application/x-ndjson` |
| GET  | `/chat/history` | 按会话 id 查询历史消息，Query: `id` |

**POST /chat 请求体示例：**

```json
{
  "model": "qwen-turbo",
  "stream": true,
  "messages": { "role": "user", "content": "你好" },
  "chat_session_id": "uuid-可选，用于关联会话与保存历史",
  "use_knowledge": true
}
```

### 2. 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | `/session/list`   | 会话列表 |
| POST   | `/session/add`    | 新增会话，body: `{ "title": "标题" }` |
| PUT    | `/session/update` | 更新会话，body: `{ "id", "title" }` |
| DELETE | `/session/delete` | 删除会话，body: `{ "id" }` |

### 3. 文档 / 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | `/documents/page`        | 分页列表，Query: `page_num`, `page_size`, 可选筛选 |
| POST   | `/documents/add`        | 上传文档，FormData: `name`, `file` |
| PUT    | `/documents/update`     | 更新文档信息，FormData |
| DELETE | `/documents/delete`     | 删除文档，Query: `id` |
| GET    | `/documents/read/{item_id}` | 下载/预览文件 |
| GET    | `/documents/vector-all`      | 同步执行全量向量化（阻塞） |
| GET    | `/documents/vector-all-stream` | 异步向量化，SSE 推送进度 |
| GET    | `/documents/vector-progress`   | 查询当前向量化进度 |

支持格式：`.pdf`, `.txt`, `.doc`, `.docx`, `.md`, `.json`, `.csv`。大文件向量化时建议使用 `vector-all-stream` 并配合前端进度条。

### 4. 模型配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | `/model-config/list`           | 全部配置列表 |
| GET    | `/model-config/list/{config_type}` | 按类型：`chat` / `embedding` |
| POST   | `/model-config/add`            | 新增配置 |
| PUT    | `/model-config/update/{config_id}` | 更新配置 |
| DELETE | `/model-config/delete/{config_id}` | 删除配置 |
| PUT    | `/model-config/set-active/{config_id}` | 设为当前启用 |
| POST   | `/model-config/init-default`   | 初始化默认千问配置 |

---

## 统一响应格式

- 成功：`{ "code": 200, "message": "响应成功！", "data": ... }`
- 失败：`{ "code": status_code, "message": "错误信息" }`

流式聊天响应为 NDJSON，每行一个 JSON 对象，包含 `model`、`created_at`、`message`、`done`、`done_reason` 等字段。

---

## 前端搭配

可与同仓库下的 **vue-doc-qa-chat** 前端配合使用，实现文档上传、知识库构建、对话与历史管理、模型配置等完整流程。前端需将接口 baseURL 指向本服务（如 `http://127.0.0.1:8082`）。

---

## 许可证

见项目根目录 [LICENSE](./LICENSE) 文件。

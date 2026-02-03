# doc-chat

基于 LangChain 的智能文档问答系统：**py-server** 后端 + **vue-doc-qa-chat** 前端。

## 仓库结构

- **py-server/** — FastAPI 后端：RAG、流式对话、知识库向量化、模型配置
- **vue-doc-qa-chat/** — Vue 3 + TypeScript + Element Plus 前端

## 快速开始

1. **后端**（需 Python 3.10+）  
   ```bash
   cd py-server && pip install -r requirements.txt && cd app && python main.py
   ```  
   默认端口：http://127.0.0.1:8082

2. **前端**  
   ```bash
   cd vue-doc-qa-chat && pnpm install && pnpm dev
   ```  
   将前端接口 baseURL 指向后端（如 `http://127.0.0.1:8082`）。

详见各子目录下的 README。

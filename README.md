# doc-chat

基于 LangChain 的智能文档问答系统：**py-server** 后端 + **vue-doc-qa-chat** 前端。

## 仓库结构

| 目录 | 说明 |
|------|------|
| **py-server/** | FastAPI 后端：RAG、流式对话、知识库向量化、模型配置 |
| **vue-doc-qa-chat/** | Vue 3 + TypeScript + Element Plus 前端（聊天、知识库、历史对话等） |

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

---

## 同步到 GitHub（含 py-server 与 vue-doc-qa-chat）

在**本仓库根目录**执行，可把后端和前端一起提交并推送：

```bash
cd /d d:\work\ai_work\03_doc-chat

git add .
git status
git commit -m "chore: 同步 py-server 与 vue-doc-qa-chat"
git push origin main
```

首次未初始化时，可先执行：

```bash
git init
git add .
git commit -m "chore: 初始提交 - py-server + vue-doc-qa-chat"
git branch -M main
git remote add origin https://github.com/maomaowang214/doc-chat.git
git push -u origin main
```

`.gitignore` 已配置为忽略 `node_modules`、`dist`、`__pycache__`、大文件等，**不会**忽略 `vue-doc-qa-chat` 和 `py-server` 的源码。

**若 GitHub 上看不到 vue-doc-qa-chat 的源码**（目录为空或只有一条子模块记录），多半是 vue-doc-qa-chat 内有自己的 `.git`。请按 **[GIT_SYNC.md](./GIT_SYNC.md)** 里的步骤操作：先删除 `vue-doc-qa-chat/.git`，再在仓库根目录执行 `git add .` 和 `git push`。

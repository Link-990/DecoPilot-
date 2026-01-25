# DecoPilot (智装领航)

**DecoPilot** 是您的智能装修顾问（原名：装修智能顾问）。它基于 RAG (Retrieval-Augmented Generation) 技术，采用 **FastAPI + React** 前后端分离架构，使用 LangChain、ChromaDB 和 DashScope (通义千问) 构建。

项目不仅支持本地知识库问答，还集成了 **DuckDuckGo 联网搜索**，能够在本地知识不足时自动寻求网络资源，为您提供最全面的装修建议。

## 核心功能

- **混合检索 (Hybrid RAG)**: 优先检索本地向量数据库，当匹配度不足（L2 距离 > 0.8）时自动触发 DuckDuckGo 联网搜索，兼顾私有知识与实时信息。
- **深度思考 (Deep Thinking)**: 模拟 AI 思考过程，在返回最终答案前实时展示检索路径、匹配分数与推理逻辑，提升回答的可解释性。
- **流式响应 (Streaming)**: 基于 FastAPI `StreamingResponse` 的 NDJSON 流式对话（`application/x-ndjson`），前端通过 `fetch + ReadableStream` 实现打字机效果。
- **UI 交互**: 
  - **深度定制**: 仿对话产品形态的 React 前端界面（侧边栏会话、多轮对话）。
  - **功能开关**: 界面提供“联网搜索”与“深度思考”的实时开关，用户可按需控制。
  - **历史记录**: 侧边栏支持多会话管理与历史记录回溯。
- **知识库管理**: 提供 Streamlit 界面支持 TXT 文件上传，内置 MD5 校验防止重复入库。

## 项目结构

```
P4_RAG项目案例/
├── server.py               # FastAPI 后端入口，处理 /chat_stream 请求
├── rag.py                  # RAG 核心逻辑 (混合检索、Prompt 构建、LangChain 链)
├── knowledge_base.py       # 知识库服务 (ChromaDB 管理、文本切分、去重)
├── vector_stores.py        # 向量数据库封装 (Chroma 初始化与操作)
├── file_history_store.py   # 聊天历史记录存储管理
├── ingest_data.py          # 知识库初始化脚本 (CLI)
├── app_file_uploader.py    # 知识库上传工具 (Streamlit UI)
├── config_data.py          # 全局配置文件 (模型参数、阈值设置)
├── data/                   # 原始知识库文件存放目录
└── frontend/               # React 前端项目源码
    ├── src/
    │   ├── App.jsx         # 主界面逻辑
    │   └── ...
    └── ...
```

## 环境要求

- Python 3.8+
- Node.js 18+ (前端构建)
- 阿里云 DashScope API Key (用于 LLM 和 Embedding)

## 快速开始

### 1. 环境准备

克隆项目并进入目录：
```bash
git clone <your-repo-url>
cd P4_RAG项目案例
```

### 2. 后端配置

安装 Python 依赖：
```bash
pip install fastapi uvicorn langchain langchain-core langchain-community langchain-chroma langchain-text-splitters dashscope streamlit duckduckgo-search python-dotenv
```

配置环境变量：
复制 `.env.example` 为 `.env` 并填入 API Key：
```bash
cp .env.example .env
```
Windows PowerShell：
```powershell
Copy-Item .env.example .env
```
在 `.env` 中设置：
```ini
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. 前端配置

安装 Node.js 依赖：
```bash
cd frontend
npm install
cd ..
```

### 4. 初始化知识库

将 `data/` 目录下所有 `.txt` 文件导入向量数据库：
```bash
python ingest_data.py
```

### 5. 启动服务

**启动后端 API:**
```bash
python server.py
# 服务默认运行在 http://localhost:8000
```

**启动前端界面:**
新开一个终端窗口：
```bash
cd frontend
npm run dev
# 访问控制台输出的本地地址 (如 http://localhost:5173)
```
前端开发服务器已在 `vite.config.js` 中配置了 `/chat_stream -> http://localhost:8000` 的代理。

## 知识库管理

如果需要添加新的装修知识文档（TXT 格式），可运行独立的上传工具：
```bash
streamlit run app_file_uploader.py
```

## 技术栈详细

| 组件 | 技术选型 | 说明 |
| --- | --- | --- |
| **LLM** | Qwen3-Max | 通义千问最新旗舰模型 |
| **Embedding** | Text-Embedding-V4 | 阿里云文本向量模型 |
| **Vector Store** | Chroma | 本地轻量级向量数据库 |
| **Orchestration** | LangChain | RAG 流程编排 |
| **Web Search** | DuckDuckGo | 联网搜索补充 |
| **Backend** | FastAPI | 高性能 Python Web 框架 |
| **Frontend** | React + Vite + Tailwind | 现代化响应式前端 |
| **UI Libs** | Lucide React + React Markdown | 图标与 Markdown 渲染 |

## 配置说明 (`config_data.py`)

您可以在 `config_data.py` 中调整核心参数：
- `chunk_size`: 文本切分大小 (默认 1000)
- `chunk_overlap`: 文本切分重叠大小 (默认 100)
- `similarity_threshold`: 本地检索返回文档数量 k (默认 4)
- `search_score_threshold`: 联网搜索触发阈值 (L2 距离，默认 0.8；越小越相关)

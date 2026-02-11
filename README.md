# DecoPilot 项目深度指南

## 1. 项目简介
DecoPilot 是一个垂直于家居装修行业的智能体系统，旨在通过 AI 技术连接业主（C端）与商家（B端）。系统内置了基于 RAG（检索增强生成）的混合检索机制和阶段感知专家系统，能够根据用户所处的不同阶段提供个性化的咨询、推荐和决策支持。

## 2. 系统架构

### 2.1 技术栈
- **后端**: Python 3.10+, FastAPI, LangChain, Uvicorn
- **AI/LLM**: 阿里云通义千问 (Qwen-Plus), DashScope Embeddings
- **向量数据库**: ChromaDB (本地持久化)
- **知识图谱**: 自研轻量级图谱结构
- **前端**: React, Vite, TailwindCSS
- **搜索**: DuckDuckGo (联网搜索补足)

### 2.2 目录结构
```
d:\demo1\DecoPilot-\
├── backend/                  # 后端核心代码
│   ├── agents/               # 智能体实现 (Base, C-End, B-End)
│   ├── api/                  # FastAPI 路由与中间件
│   ├── config/               # 业务规则与配置
│   ├── core/                 # 核心组件 (记忆, 推理, 工具, 多模态)
│   ├── framework/            # 框架层抽象
│   ├── knowledge/            # 知识库与知识图谱管理
│   └── rag.py                # RAG 服务入口
├── frontend/                 # React 前端项目
├── data/                     # 数据存储 (SQLite, txt语料)
├── docs/                     # 项目文档
├── server.py                 # 后端启动入口
└── requirements.txt          # 后端依赖
```

## 3. 核心功能模块

### 3.1 双端智能体 (Dual-End Agents)
系统针对不同用户群体设计了专用的智能体：

*   **C端智能体 (业主顾问)**
    *   **代号**: 小洞
    *   **核心能力**: 装修全流程咨询、装修补贴计算、风格推荐、避坑指南。
    *   **阶段感知**: 自动识别用户处于 **[准备 -> 设计 -> 施工 -> 软装 -> 入住]** 的哪个阶段，并动态切换专家角色（如从“规划师”切换为“工程监理”）。
    
*   **B端智能体 (商家助手)**
    *   **代号**: 洞掌柜
    *   **核心能力**: 商家入驻指引、ROI 投产比分析、获客话术生成、经营数据分析。
    *   **阶段感知**: 覆盖 **[入驻 -> 获客 -> 经营分析 -> 核销结算]** 全生命周期。

### 3.2 混合 RAG 检索 (Hybrid RAG)
系统采用多层级的检索策略以确保回答的准确性：
1.  **多集合检索**: 根据用户类型（B端/C端）优先检索对应的知识库集合。
2.  **向量检索**: 使用 ChromaDB 进行语义相似度匹配。
3.  **联网搜索**: 当本地知识库无法满足（匹配分低于阈值）时，自动调用 DuckDuckGo 进行联网搜索。

### 3.3 业务规则引擎
核心业务逻辑配置在 `backend/config/business_rules.py` 中，支持热更新：
- **补贴规则**: 不同品类（家具、建材、家电）的补贴比例和上限。
- **商家画像**: 不同行业（全屋定制、瓷砖卫浴）的特征定义。
- **风格定义**: 现代简约、北欧等风格的配色与关键词。

## 4. 快速启动指南

### 4.1 环境准备
1.  确保已安装 Python 3.10+ 和 Node.js 18+。
2.  复制环境变量文件：
    ```bash
    copy .env.template .env
    ```
3.  **关键配置**: 打开 `.env` 文件，填入你的 `DASHSCOPE_API_KEY`（阿里云百炼控制台获取）。

### 4.2 安装依赖
**后端**:
```bash
pip install -r requirements.txt
```

**前端**:
```bash
cd frontend
npm install
```

### 4.3 启动服务
建议开启两个终端窗口分别运行：

**终端 1 (后端 API)**:
```bash
# 运行在 http://localhost:8000
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 (前端界面)**:
```bash
# 运行在 http://localhost:5173
cd frontend
npm run dev
```

## 5. API 接口说明
启动后端后，访问 `http://localhost:8000/docs` 查看完整 Swagger 文档。

### 主要接口
-   `POST /chat/stream`: 通用流式对话接口
    -   参数: `message` (内容), `user_type` (c_end/b_end), `session_id`
    -   功能: 自动路由到对应 Agent，支持上下文记忆。
-   `GET /health`: 健康检查

## 6. 常见问题
-   **Q: 为什么 AI 回答“无法回答”？**
    -   A: 检查 `.env` 中的 API Key 是否正确；检查相关知识库文件是否已通过 `ingest_all.py` 脚本导入。
-   **Q: 如何修改补贴规则？**
    -   A: 直接修改 `backend/config/business_rules.py` 中的 `SUBSIDY_RULES` 字典即可生效。

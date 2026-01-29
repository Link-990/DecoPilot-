# DecoPilot (智装领航)

<p align="center">
  <strong>家居行业智能体平台 | 千万级知识库 | 企业级架构</strong>
</p>

**DecoPilot** 是一个面向家居装修行业的垂直领域智能体平台，为 C 端业主和 B 端商家提供专业的智能服务。基于 RAG (Retrieval-Augmented Generation) 技术，集成记忆系统、推理引擎、工具系统和多模态能力，能够真正解决用户的装修问题。

## 核心能力

### 智能体能力矩阵

| 能力 | 描述 | 状态 |
|------|------|------|
| **多集合知识库** | 支持按用户类型差异化检索，千万级数据支持 | ✅ |
| **三层记忆系统** | 短期记忆 + 长期记忆 + 工作记忆 | ✅ |
| **用户画像** | 兴趣追踪、偏好学习、个性化推荐 | ✅ |
| **思维链推理** | CoT、多步推理、自我反思 | ✅ |
| **工具系统** | 动态注册、链式调用、参数验证 | ✅ |
| **多模态支持** | 图片理解、文档解析、表格识别 | ✅ |
| **结构化输出** | 补贴卡片、商家列表、流程步骤 | ✅ |

### C 端服务 (业主用户)

- **装修知识问答** - 风格选择、材料对比、施工工艺
- **补贴政策咨询** - 补贴计算、领取流程、使用规则
- **商家推荐** - 基于需求、预算、位置的智能匹配
- **价格评估** - 判断报价是否合理
- **工期估算** - 根据面积和风格估算装修周期
- **图片分析** - 装修风格识别、材料识别

### B 端服务 (商家用户)

- **入驻指导** - 流程说明、资质要求、费用标准
- **数据产品咨询** - 选品推荐、客户画像、竞品分析
- **获客策略** - 话术生成、最佳触达时机
- **ROI 分析** - 投入产出比计算、经营建议
- **核销结算** - 结算规则、对账流程

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        DecoPilot 架构                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   React     │  │   FastAPI   │  │   Streamlit │   Frontend   │
│  │   Frontend  │  │   REST API  │  │   (Legacy)  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
├─────────┴────────────────┴────────────────┴─────────────────────┤
│                         API Layer                                │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  /api/v1/chat/*  │  /api/v1/knowledge/*  │  /api/v1/merchant/*│
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│                        Agent Layer                               │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐        │
│  │  C-End Agent  │  │  B-End Agent  │  │ Enhanced Agent│        │
│  │   (业主服务)   │  │   (商家服务)   │  │   (增强基类)   │        │
│  └───────────────┘  └───────────────┘  └───────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│                        Core Layer                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │  Memory  │ │Reasoning │ │  Tools   │ │Multimodal│            │
│  │  记忆系统 │ │ 推理引擎  │ │ 工具系统  │ │ 多模态   │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
├─────────────────────────────────────────────────────────────────┤
│                      Knowledge Layer                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Multi-Collection Knowledge Base                 ││
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            ││
│  │  │ General │ │ C-End   │ │ B-End   │ │Merchant │            ││
│  │  │ 通用知识 │ │ 业主专属 │ │ 商家专属 │ │ 商家信息 │            ││
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘            ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│                      Infrastructure                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ ChromaDB │ │ DashScope│ │  Qwen    │ │  Redis   │            │
│  │ 向量数据库 │ │ Embedding│ │   LLM   │ │  (可选)  │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 项目结构

```
DecoPilot/
├── backend/
│   ├── agents/                    # 智能体模块
│   │   ├── base_agent.py          # 基础智能体
│   │   ├── enhanced_agent.py      # 增强版智能体 (新)
│   │   ├── c_end_agent.py         # C端智能体
│   │   ├── b_end_agent.py         # B端智能体
│   │   └── prompts/               # 提示词模板
│   │       ├── c_end_prompts.py
│   │       └── b_end_prompts.py
│   │
│   ├── core/                      # 核心模块 (新)
│   │   ├── memory.py              # 记忆系统
│   │   ├── reasoning.py           # 推理引擎
│   │   ├── tools.py               # 工具系统
│   │   ├── multimodal.py          # 多模态处理
│   │   ├── output_formatter.py    # 输出格式化
│   │   ├── singleton.py           # 单例管理
│   │   ├── container.py           # 依赖注入
│   │   └── security.py            # 安全模块
│   │
│   ├── knowledge/                 # 知识库模块
│   │   └── multi_collection_kb.py # 多集合知识库
│   │
│   ├── api/                       # API模块
│   │   ├── routes/
│   │   │   ├── chat.py            # 聊天接口
│   │   │   ├── knowledge.py       # 知识库接口
│   │   │   └── merchant.py        # 商家服务接口
│   │   └── middleware/
│   │       ├── auth.py            # 认证中间件
│   │       └── rate_limit.py      # 限流中间件
│   │
│   ├── config/                    # 配置模块
│   │   └── business_rules.py      # 业务规则配置
│   │
│   ├── crawlers/                  # 爬虫模块
│   │   ├── base_crawler.py
│   │   └── decoration_crawler.py
│   │
│   └── scripts/                   # 脚本
│       └── ingest_all.py          # 数据导入脚本
│
├── frontend/                      # React前端
│   ├── src/
│   │   ├── App.jsx                # 主应用
│   │   ├── components/
│   │   │   └── StructuredData.jsx # 结构化数据组件
│   │   └── utils/
│   │       └── responseParser.js  # 响应解析器
│   └── package.json
│
├── data/                          # 知识库数据
│   ├── c_end/                     # C端数据
│   │   ├── 补贴政策详解.txt
│   │   └── 装修全流程指南.txt
│   └── b_end/                     # B端数据
│       ├── 商家入驻指南.txt
│       └── 获客转化指南.txt
│
├── server.py                      # FastAPI服务器
├── rag.py                         # RAG服务
├── config_data.py                 # 全局配置
├── requirements.txt               # Python依赖
└── README.md
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+ (前端开发)
- 阿里云 DashScope API Key

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/your-repo/DecoPilot.git
   cd DecoPilot
   ```

2. **安装 Python 依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   # 创建 .env 文件
   echo "DASHSCOPE_API_KEY=sk-your-api-key" > .env
   ```

4. **初始化知识库**
   ```bash
   python -m backend.scripts.ingest_all --data-dir ./data
   ```

5. **启动后端服务**
   ```bash
   python -m uvicorn server:app --host 0.0.0.0 --port 8000
   ```

6. **启动前端 (可选)**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### 访问服务

- **API 文档**: http://localhost:8000/docs
- **前端界面**: http://localhost:5173
- **健康检查**: http://localhost:8000/health

## API 文档

### 聊天接口

#### C 端聊天
```bash
POST /api/v1/chat/c-end
Content-Type: application/json

{
  "message": "我想买一套家具，大概2万元，能拿多少补贴？",
  "session_id": "user_001",
  "enable_search": true,
  "show_thinking": true
}
```

#### B 端聊天
```bash
POST /api/v1/chat/b-end
Content-Type: application/json

{
  "message": "如何提高客户转化率？",
  "session_id": "merchant_001"
}
```

### 商家服务接口

#### 补贴计算
```bash
POST /api/v1/merchant/subsidy/calc
Content-Type: application/json

{
  "order_amount": 20000,
  "category": "家具"
}
```

**响应示例:**
```json
{
  "order_amount": 20000,
  "category": "家具",
  "subsidy_rate": 0.05,
  "calculated_subsidy": 1000,
  "max_subsidy": 2000,
  "actual_subsidy": 1000,
  "explanation": "家具补贴 = 20000 × 5% = 1000元"
}
```

#### ROI 分析
```bash
POST /api/v1/merchant/roi/analyze
Content-Type: application/json

{
  "investment": 5000,
  "revenue": 15000,
  "period_days": 30
}
```

### 流式响应格式

聊天接口返回 NDJSON 格式的流式响应：

```json
{"type": "stream_start", "data": {"session_id": "...", "request_id": "..."}}
{"type": "thinking", "data": {"logs": ["检索知识库...", "分析用户意图..."]}}
{"type": "sources", "data": [{"title": "...", "content": "...", "collection": "..."}]}
{"type": "answer", "data": {"content": "根据您的需求..."}}
{"type": "subsidy_calc", "data": {"category": "家具", "final_amount": 1000}}
{"type": "stream_end", "data": {"duration_ms": 1234}}
```

## 核心模块说明

### 记忆系统 (Memory)

```python
from backend.core.memory import get_memory_manager

memory = get_memory_manager()

# 用户画像
profile = memory.get_or_create_profile("user_001", "c_end")
profile.update_interest("现代简约", 0.2)

# 短期记忆
memory.add_to_short_term("session_001", {"role": "user", "content": "..."})

# 工作记忆
memory.set_working_memory("session_001", "current_budget", 100000)

# 长期记忆
memory.add_to_long_term("user_001", {"topic": "装修风格", "preference": "北欧"})
```

### 推理引擎 (Reasoning)

```python
from backend.core.reasoning import get_reasoning_engine, TaskAnalyzer

engine = get_reasoning_engine()

# 分析任务复杂度
complexity = TaskAnalyzer.analyze_complexity("如何选择装修风格？")
# -> TaskComplexity.MODERATE

# 创建推理链
chain = engine.chain_of_thought("比较现代简约和北欧风格的区别")
engine.think(chain, "首先理解两种风格的特点...")
engine.act(chain, "检索知识库", tool="knowledge_search")
engine.observe(chain, "找到相关信息...")
engine.reflect(chain, "答案是否完整？")
```

### 工具系统 (Tools)

```python
from backend.core.tools import get_tool_registry

registry = get_tool_registry()

# 调用内置工具
result = registry.call("subsidy_calculator", amount=20000, category="家具")
print(result.data)  # {"final_amount": 1000, ...}

# 获取工具列表 (用于 LLM)
tools = registry.get_tools_for_llm()

# 查看统计
stats = registry.get_statistics()
```

### 多模态处理 (Multimodal)

```python
from backend.core.multimodal import get_multimodal_manager, MediaContent, MediaType

mm = get_multimodal_manager()

# 分析装修图片
result = mm.analyze_decoration_image("./images/living_room.jpg")
print(result.description)  # "现代简约风格客厅..."
print(result.style_tags)   # ["现代", "简约", "白色调"]

# 解析报价单
quotation = mm.parse_quotation("./docs/quotation.pdf")
print(quotation["tables"])  # 提取的表格数据
```

## 知识库管理

### 集合配置

| 集合名称 | 用途 | 目标用户 |
|---------|------|---------|
| decoration_general | 装修风格、材料、施工知识 | 全部 |
| smart_home | 智能家居选购配置 | 全部 |
| dongju_c_end | 补贴政策、使用流程 | C端 |
| dongju_b_end | 入驻指南、数据产品 | B端 |
| merchant_info | 商家信息、评价 | 全部 |

### 数据导入

```bash
# 导入所有数据
python -m backend.scripts.ingest_all --data-dir ./data

# 查看知识库状态
curl http://localhost:8000/api/v1/knowledge/collections
```

### 添加新知识

将文档放入对应目录：
- C端知识: `data/c_end/`
- B端知识: `data/b_end/`
- 通用知识: `data/`

支持的格式: TXT, PDF

## 补贴规则

| 品类 | 补贴比例 | 单笔上限 |
|------|---------|---------|
| 家具 | 5% | 2000元 |
| 建材 | 3% | 1500元 |
| 家电 | 4% | 1000元 |
| 软装 | 6% | 800元 |
| 智能家居 | 8% | 1500元 |

**月度上限**: 5000元

## 开发指南

### 添加新工具

```python
from backend.core.tools import get_tool_registry, ToolDefinition, ToolParameter, ToolCategory

def my_tool_handler(param1: str, param2: float) -> dict:
    return {"result": f"{param1}: {param2}"}

registry = get_tool_registry()
registry.register(ToolDefinition(
    name="my_tool",
    description="我的自定义工具",
    category=ToolCategory.UTILITY,
    parameters=[
        ToolParameter("param1", str, "参数1说明", required=True),
        ToolParameter("param2", float, "参数2说明", required=False, default=1.0),
    ],
    handler=my_tool_handler,
))
```

### 扩展智能体

```python
from backend.agents.enhanced_agent import EnhancedAgent

class MyAgent(EnhancedAgent):
    def __init__(self):
        super().__init__(user_type="c_end", agent_name="my_agent")

    def _get_system_prompt(self) -> str:
        return "你是一个专业的装修顾问..."

    async def custom_method(self, query: str):
        # 自定义逻辑
        pass
```

## 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| LLM | Qwen (通义千问) | qwen-plus |
| Embedding | DashScope | text-embedding-v4 |
| Vector DB | ChromaDB | 0.4+ |
| Framework | LangChain | 0.1+ |
| Backend | FastAPI | 0.100+ |
| Frontend | React + Vite | 18+ |
| Styling | Tailwind CSS | 3+ |

## 性能指标

- **知识库容量**: 支持千万级文档
- **检索延迟**: < 100ms (P99)
- **生成延迟**: 首 token < 500ms
- **并发支持**: 100+ QPS

## 路线图

- [x] 多集合知识库
- [x] C端/B端差异化服务
- [x] 记忆系统
- [x] 推理引擎
- [x] 工具系统
- [x] 多模态支持
- [x] 结构化输出
- [ ] 分布式向量数据库
- [ ] 知识图谱
- [ ] 语音交互
- [ ] 视频理解

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

MIT License

## 联系方式

- **项目主页**: https://github.com/your-repo/DecoPilot
- **问题反馈**: https://github.com/your-repo/DecoPilot/issues

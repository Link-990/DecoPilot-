# DecoPilot 系统架构设计：从装修智能体到用户智能伙伴

> 本文档是一份可落地的系统架构设计。它不是愿景文档的重复，而是回答一个工程问题：
> **如何把"一个懂你、陪你、替你管事的智能伙伴"这个产品理想，变成一套可运行、可演进、可度量的技术系统？**
>
> 每一个设计决策都指向同一个标准：这个用户用了之后，是否会觉得"这个东西真的帮到我了"。

---

## 一、架构哲学：三个不可妥协的原则

在进入任何技术细节之前，先确立三个架构级别的约束。它们不是"最好做到"，而是"必须做到"——违反任何一条，产品就不可能成功。

### 原则一：User Context File 是一等公民

所有数据流最终汇入 User Context File（UCF），所有智能行为从 UCF 出发。UCF 不是"附属于对话的用户画像"，它是系统的中心。

```
                       ┌─────────────────┐
    对话 ──提取──→     │                 │  ──注入──→ 对话回复
    笔记 ──沉淀──→     │  User Context   │  ──驱动──→ 主动提醒
    行为 ──推断──→     │     File        │  ──生成──→ 看板视图
    时间 ──触发──→     │                 │  ──支撑──→ 决策报告
                       └─────────────────┘
```

**工程含义**：UCF 必须有独立的存储层、版本历史、读写 API、变更事件总线。不能把它塞在 memory.py 的某个字段里。

### 原则二：智能行为必须可解释、可修正

智能体的每一个"理解"（从对话中提取的信息、推断的偏好、给出的建议），用户都必须能看到、能纠正。

**工程含义**：每次 UCF 更新都要记录 `source`（来源）、`confidence`（置信度）、`evidence`（证据）。前端必须有对应的展示和编辑界面。

### 原则三：主动性由事件驱动，不由轮询驱动

智能体的主动行为（提醒、分析、建议）不是定时轮询"该不该做点什么"，而是由 UCF 变更事件、时间事件、外部事件触发。

**工程含义**：需要一个事件总线（Event Bus），UCF 的每次写入都发出事件，订阅者（提醒引擎、分析引擎、看板引擎）响应事件。

---

## 二、系统全景

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              客户端层                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │   对话界面    │  │   笔记界面    │  │   看板界面    │  │   档案界面     │   │
│  │  Chat View   │  │  Note View   │  │  Board View  │  │ Profile View  │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘   │
│         │                  │                  │                   │          │
│  ┌──────┴──────────────────┴──────────────────┴───────────────────┴──────┐   │
│  │                      统一交互层 (Unified API)                         │   │
│  │         WebSocket (实时对话)  +  REST API (数据操作)                    │   │
│  └───────────────────────────────┬───────────────────────────────────────┘   │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                              网关层                                          │
│  ┌───────────────────────────────┴───────────────────────────────────────┐   │
│  │    FastAPI Gateway                                                    │   │
│  │    认证 (JWT) │ 限流 │ 安全过滤 │ 请求路由 │ 指标采集                    │   │
│  └───────────────────────────────┬───────────────────────────────────────┘   │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                           智能体核心层                                       │
│                                  │                                          │
│  ┌──────────────────── Agent Orchestrator ────────────────────────────┐     │
│  │                                                                    │     │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │     │
│  │  │  对话引擎   │  │  提取引擎   │  │  主动引擎   │  │  研究引擎   │  │     │
│  │  │ Dialogue   │  │ Extraction │  │ Proactive  │  │  Research  │  │     │
│  │  │  Engine    │  │  Engine    │  │  Engine    │  │  Engine    │  │     │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  │     │
│  │        │                │                │                │        │     │
│  │  ┌─────┴────────────────┴────────────────┴────────────────┴─────┐  │     │
│  │  │                   共享能力层                                   │  │     │
│  │  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │  │     │
│  │  │  │  LLM    │ │ 工具系统  │ │ 推理框架  │ │ 阶段感知专家系统  │ │  │     │
│  │  │  │ Router  │ │  Tools   │ │Reasoning │ │ Stage Reasoning  │ │  │     │
│  │  │  └─────────┘ └──────────┘ └──────────┘ └──────────────────┘ │  │     │
│  │  └────────────────────────────────────────────────────────────┘  │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                  │                                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                              数据层                                          │
│                                  │                                          │
│  ┌───────────────┐  ┌────────────┴──────┐  ┌──────────────────────────┐    │
│  │ User Context  │  │   Event Bus       │  │    领域知识层              │    │
│  │    File       │  │  (UCF变更事件)     │  │                          │    │
│  │   (SQLite)    │  │  (内存 + 持久化)   │  │  ChromaDB (向量知识库)    │    │
│  │               │  │                   │  │  DecisionTree (决策树)    │    │
│  │  用户档案      │  │  profile.updated  │  │  PitfallRules (避坑库)   │    │
│  │  笔记存储      │  │  note.created     │  │  StageKnowledge (阶段)   │    │
│  │  项目状态      │  │  decision.made    │  │                          │    │
│  │  对话记忆      │  │  stage.changed    │  │                          │    │
│  │  行为日志      │  │  reminder.due     │  │                          │    │
│  └───────────────┘  └───────────────────┘  └──────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、模型策略：不同任务用不同模型

### 3.1 模型选择矩阵

一个真正工作的产品不能把所有任务都丢给同一个模型。不同任务对延迟、质量、成本的要求完全不同。

| 任务 | 模型 | 原因 | 延迟要求 | 调用频率 |
|------|------|------|---------|---------|
| **日常对话** | `qwen-plus` | 性价比最优，回答质量够用，支持流式输出 | <3秒首token | 每轮对话 |
| **信息提取（从对话中提取结构化数据）** | `qwen-turbo` | 提取任务不需要强推理，需要快和便宜 | <1秒 | 每轮对话(后台) |
| **深度研究/复杂决策报告** | `qwen-max` | 需要强推理能力和长上下文理解 | <10秒 | 低频触发 |
| **图片理解（施工照片/灵感图）** | `qwen-vl-plus` | 多模态理解，识别施工阶段、材料、问题 | <5秒 | 用户上传时 |
| **向量嵌入** | `text-embedding-v4` | 知识检索、语义匹配 | <500ms | 每次检索 |
| **意图分类/情绪检测** | 规则引擎 + `qwen-turbo` | 关键词优先，兜底用小模型 | <200ms | 每轮对话 |
| **阶段推断** | 规则引擎 + `qwen-turbo` | 已有关键词规则，复杂case用LLM | <500ms | 每轮对话 |

### 3.2 LLM Router 实现

```python
# backend/core/llm_router.py

from enum import Enum
from langchain_community.chat_models import ChatTongyi

class TaskType(Enum):
    CONVERSATION = "conversation"        # 日常对话
    EXTRACTION = "extraction"            # 信息提取
    DEEP_RESEARCH = "deep_research"      # 深度研究
    IMAGE_UNDERSTANDING = "image"        # 图片理解
    CLASSIFICATION = "classification"    # 意图/情绪分类

# 模型配置：每种任务对应的模型和参数
MODEL_CONFIG = {
    TaskType.CONVERSATION: {
        "model": "qwen-plus",
        "temperature": 0.7,
        "max_tokens": 4096,
        "streaming": True,
    },
    TaskType.EXTRACTION: {
        "model": "qwen-turbo",
        "temperature": 0.1,       # 提取任务需要确定性
        "max_tokens": 2048,
        "streaming": False,        # 不需要流式
    },
    TaskType.DEEP_RESEARCH: {
        "model": "qwen-max",
        "temperature": 0.5,
        "max_tokens": 8192,
        "streaming": True,
    },
    TaskType.IMAGE_UNDERSTANDING: {
        "model": "qwen-vl-plus",
        "temperature": 0.3,
        "max_tokens": 2048,
        "streaming": False,
    },
    TaskType.CLASSIFICATION: {
        "model": "qwen-turbo",
        "temperature": 0.0,        # 分类需要确定性输出
        "max_tokens": 256,
        "streaming": False,
    },
}

class LLMRouter:
    """根据任务类型路由到合适的模型"""

    def __init__(self):
        self._clients = {}

    def get_llm(self, task_type: TaskType) -> ChatTongyi:
        if task_type not in self._clients:
            config = MODEL_CONFIG[task_type]
            self._clients[task_type] = ChatTongyi(
                model=config["model"],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"],
                streaming=config["streaming"],
            )
        return self._clients[task_type]
```

### 3.3 模型降级策略

生产环境必须考虑模型服务不可用的情况：

```python
MODEL_FALLBACK = {
    "qwen-max": ["qwen-plus", "qwen-turbo"],
    "qwen-plus": ["qwen-turbo"],
    "qwen-vl-plus": ["qwen-vl-max"],   # VL没有轻量降级，只能换大的
    "qwen-turbo": [],                    # 最底层，无法降级
}
```

当主模型返回 429/500/超时 时，自动切换到降级模型，并在日志中记录降级事件。

---

## 四、User Context File：系统的心脏

UCF 是整个系统的核心数据结构。它不是 memory.py 中 UserProfile 的简单扩展——它是一个独立的、有版本的、可订阅的数据存储。

### 4.1 完整数据模型

```python
# backend/core/user_context.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum
import time
import uuid

# ──────────────────────────────────────────
#  数据来源标记：每条数据都要知道"从哪来的"
# ──────────────────────────────────────────

class DataSource(Enum):
    USER_STATED = "user_stated"        # 用户明确说的
    EXTRACTED = "extracted"            # 从对话中提取的
    INFERRED = "inferred"             # AI 推断的
    SYSTEM = "system"                  # 系统生成的（如阶段自动推进）
    USER_EDITED = "user_edited"        # 用户在档案界面手动修改的

@dataclass
class Sourced:
    """所有 UCF 中的数据项都带来源"""
    value: any
    source: DataSource
    confidence: float = 1.0            # 0-1，用户明确说的=1.0，推断的可能<0.8
    evidence: str = ""                 # 证据（用户原话 / 推断依据）
    timestamp: float = field(default_factory=time.time)
    version: int = 1                   # 版本号，每次修改递增

# ──────────────────────────────────────────
#  身份信息
# ──────────────────────────────────────────

@dataclass
class Identity:
    name: Optional[Sourced] = None
    city: Optional[Sourced] = None
    district: Optional[Sourced] = None       # 区
    community: Optional[Sourced] = None      # 小区名

@dataclass
class HouseInfo:
    area: Optional[Sourced] = None               # 面积（平米）
    layout: Optional[Sourced] = None             # 户型 "三室两厅"
    floor: Optional[Sourced] = None              # 楼层
    has_elevator: Optional[Sourced] = None       # 是否有电梯
    has_floor_heating: Optional[Sourced] = None  # 是否有地暖
    orientation: Optional[Sourced] = None        # 朝向
    delivery_date: Optional[Sourced] = None      # 交房日期
    is_new_house: Optional[Sourced] = None       # 新房 or 二手房

@dataclass
class Family:
    structure: Optional[Sourced] = None          # "三口之家"
    has_children: Optional[Sourced] = None       # 是否有小孩
    children_ages: List[Sourced] = field(default_factory=list)
    has_elderly: Optional[Sourced] = None        # 是否有老人
    has_pets: Optional[Sourced] = None           # 是否有宠物
    pet_types: List[Sourced] = field(default_factory=list)
    special_needs: List[Sourced] = field(default_factory=list)  # 如"轮椅通行需求"

# ──────────────────────────────────────────
#  偏好模型
# ──────────────────────────────────────────

@dataclass
class StylePreference:
    style_name: str                              # "日式原木" / "现代简约"
    weight: float                                # 0-1 偏好权重
    source: DataSource
    evidence: str = ""                           # "用户说喜欢那种咖啡店的感觉"

@dataclass
class Preferences:
    styles: List[StylePreference] = field(default_factory=list)
    budget_range: Optional[Sourced] = None       # (min, max) 元
    budget_priority: Optional[Sourced] = None    # "性价比优先" / "品质优先"
    price_sensitivity: Optional[Sourced] = None  # 0-1
    eco_sensitivity: Optional[Sourced] = None    # 0-1, 环保敏感度
    brand_preference: Optional[Sourced] = None   # "重视品牌" / "不在意品牌"
    decision_style: Optional[Sourced] = None     # "果断型" / "谨慎型（多方比较）"
    info_source_trust: Dict[str, float] = field(default_factory=dict)  # {"邻居口碑": 0.9, "测评": 0.6}
    communication_style: Optional[Sourced] = None  # "简洁直接" / "希望详细解释"

# ──────────────────────────────────────────
#  项目状态（装修看板的数据源）
# ──────────────────────────────────────────

class ProjectStage(Enum):
    PREPARATION = "准备"
    DESIGN = "设计"
    CONSTRUCTION = "施工"
    SOFT_DECORATION = "软装"
    MOVE_IN = "入住"

@dataclass
class StageRecord:
    stage: ProjectStage
    entered_at: float
    exited_at: Optional[float] = None
    notes: List[str] = field(default_factory=list)

@dataclass
class Decision:
    """一个已做出的决策"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: str = ""                 # "地板" / "设计师" / "装修公司"
    decision: str = ""                 # "选了大自然三层实木"
    reason: str = ""                   # "性价比高，适合地暖"
    amount: Optional[float] = None     # 花费
    timestamp: float = field(default_factory=time.time)
    source: DataSource = DataSource.EXTRACTED

@dataclass
class TodoItem:
    """一个待办事项"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""                    # "确定橱柜品牌"
    reason: str = ""                   # "定制周期25天，再不定影响安装"
    priority: str = "medium"           # "critical" / "high" / "medium" / "low"
    due_stage: Optional[str] = None    # 最迟在哪个阶段前完成
    is_done: bool = False
    done_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    source: DataSource = DataSource.SYSTEM

@dataclass
class BudgetItem:
    """一项预算/支出"""
    category: str = ""                 # "水电改造" / "瓷砖" / "橱柜"
    planned: Optional[float] = None    # 计划预算
    actual: Optional[float] = None     # 实际支出
    vendor: Optional[str] = None       # 商家/品牌
    note: str = ""
    timestamp: float = field(default_factory=time.time)

@dataclass
class ProjectState:
    current_stage: Sourced = field(
        default_factory=lambda: Sourced(
            value=ProjectStage.PREPARATION,
            source=DataSource.SYSTEM
        )
    )
    progress_percent: float = 0.0
    stage_history: List[StageRecord] = field(default_factory=list)
    expected_completion: Optional[Sourced] = None
    start_date: Optional[Sourced] = None

    # 决策记录
    decisions: List[Decision] = field(default_factory=list)
    pending_decisions: List[str] = field(default_factory=list)  # 待决策项

    # 待办事项
    todos: List[TodoItem] = field(default_factory=list)

    # 预算追踪
    budget_items: List[BudgetItem] = field(default_factory=list)
    total_budget: Optional[Sourced] = None
    total_spent: float = 0.0

# ──────────────────────────────────────────
#  知识沉淀（智能笔记的数据源）
# ──────────────────────────────────────────

@dataclass
class KnowledgeEntry:
    """一条从对话/笔记中沉淀的知识"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""                  # 原始内容
    structured: Dict = field(default_factory=dict)  # 结构化提取
    # structured 示例:
    # {"type": "product_info", "brand": "马可波罗", "spec": "800x800",
    #  "price": 85, "unit": "元/片", "source_location": "红星美凯龙"}
    category: str = ""                 # "选材记录" / "施工经验" / "品牌印象"
    tags: List[str] = field(default_factory=list)
    source: DataSource = DataSource.EXTRACTED
    evidence: str = ""                 # 用户原话
    timestamp: float = field(default_factory=time.time)
    linked_decisions: List[str] = field(default_factory=list)  # 关联的决策ID

@dataclass
class BrandImpression:
    """对一个品牌的印象"""
    brand: str = ""
    sentiment: str = "neutral"         # "positive" / "negative" / "neutral"
    category: str = ""                 # "瓷砖" / "地板"
    evidence: str = ""                 # "邻居说不错"
    source_type: str = ""              # "口碑" / "自己体验" / "网上评价"
    timestamp: float = field(default_factory=time.time)

@dataclass
class KnowledgeBase:
    entries: List[KnowledgeEntry] = field(default_factory=list)
    brand_impressions: List[BrandImpression] = field(default_factory=list)

# ──────────────────────────────────────────
#  关系网络
# ──────────────────────────────────────────

@dataclass
class RelatedPerson:
    """装修过程中的关键人物"""
    role: str = ""                     # "工长" / "设计师" / "妻子" / "邻居"
    name: Optional[str] = None
    notes: List[str] = field(default_factory=list)  # "做事靠谱但沟通少"
    sentiment: str = "neutral"
    timestamp: float = field(default_factory=time.time)

# ──────────────────────────────────────────
#  行为模式（AI 推断）
# ──────────────────────────────────────────

@dataclass
class BehaviorPattern:
    active_hours: List[int] = field(default_factory=list)  # 活跃时段 [20, 21, 22]
    avg_session_length: float = 0.0    # 平均会话时长（分钟）
    question_depth: str = "medium"     # "surface" / "medium" / "deep"
    anxiety_level: float = 0.0         # 0-1, 当前焦虑水平
    engagement_trend: str = "stable"   # "rising" / "stable" / "declining"

# ──────────────────────────────────────────
#  提醒历史
# ──────────────────────────────────────────

@dataclass
class ReminderRecord:
    reminder_id: str = ""
    content: str = ""
    triggered_at: float = field(default_factory=time.time)
    was_useful: Optional[bool] = None  # 用户反馈

# ══════════════════════════════════════════
#  UCF 根结构
# ══════════════════════════════════════════

@dataclass
class UserContextFile:
    """
    用户上下文档案 —— 系统的心脏。
    每个用户一份，持续演进，贯穿产品全生命周期。
    """
    # 元数据
    user_id: str = ""
    user_type: str = "c_end"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 0                   # 每次更新递增

    # 六大模块
    identity: Identity = field(default_factory=Identity)
    house: HouseInfo = field(default_factory=HouseInfo)
    family: Family = field(default_factory=Family)
    preferences: Preferences = field(default_factory=Preferences)
    project: ProjectState = field(default_factory=ProjectState)
    knowledge: KnowledgeBase = field(default_factory=KnowledgeBase)

    # 辅助模块
    relationships: List[RelatedPerson] = field(default_factory=list)
    behavior: BehaviorPattern = field(default_factory=BehaviorPattern)
    reminder_history: List[ReminderRecord] = field(default_factory=list)

    # 统计
    total_sessions: int = 0
    total_messages: int = 0
    total_notes: int = 0

    def get_completeness(self) -> float:
        """档案完整度 0-1，用于引导用户补充信息"""
        fields = [
            self.house.area, self.preferences.budget_range,
            self.preferences.styles, self.family.structure,
            self.house.has_floor_heating, self.house.layout,
        ]
        filled = sum(1 for f in fields if f is not None)
        return filled / len(fields)
```

### 4.2 UCF 存储层

```python
# backend/core/ucf_store.py

import sqlite3
import json
from typing import Optional
from .user_context import UserContextFile, DataSource

class UCFStore:
    """
    UCF 持久化存储。
    设计原则：
    1. 每个用户一行，JSON 序列化（SQLite JSON1 扩展支持字段级查询）
    2. 每次写入发出变更事件
    3. 写入时自动递增版本号和 updated_at
    4. 支持字段级更新（不需要全量读写）
    """

    def __init__(self, db_path: str = "data/ucf.db"):
        self.db_path = db_path
        self._init_db()
        self._event_listeners = []

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_context (
                user_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                version INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL
            )
        """)
        # 变更日志表：记录每次 UCF 变更
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ucf_changelog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                field_path TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                source TEXT NOT NULL,
                evidence TEXT,
                timestamp REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get(self, user_id: str) -> Optional[UserContextFile]:
        """读取用户的 UCF"""
        ...

    def save(self, ucf: UserContextFile):
        """全量保存（用于新建或完整更新）"""
        ...

    def update_field(self, user_id: str, field_path: str, value, source: DataSource, evidence: str = ""):
        """
        字段级更新。
        field_path 示例: "house.area", "preferences.styles", "project.decisions"
        自动记录变更日志，自动发出事件。
        """
        ...
        # 发出变更事件
        self._emit_event("ucf.field_updated", {
            "user_id": user_id,
            "field_path": field_path,
            "new_value": value,
            "source": source.value,
        })

    def append_to_list(self, user_id: str, field_path: str, item, source: DataSource, evidence: str = ""):
        """向列表字段追加元素（如 decisions, todos, knowledge.entries）"""
        ...

    def on_change(self, callback):
        """注册变更监听器"""
        self._event_listeners.append(callback)

    def _emit_event(self, event_type: str, data: dict):
        for listener in self._event_listeners:
            listener(event_type, data)
```

### 4.3 从现有 UserProfile 到 UCF 的迁移

不需要推翻现有代码。迁移策略：

1. **UCFStore 作为新存储层**，与现有 SQLiteProfileStore 并行运行
2. **写入双写**：enhanced_agent.py 的 `_update_memory()` 同时写入旧 ProfileStore 和新 UCFStore
3. **读取切换**：`_build_prompt_parts()` 优先从 UCFStore 读取，读不到则 fallback 到旧 ProfileStore
4. **自动迁移**：首次读取某用户时，如果 UCFStore 无数据但旧 ProfileStore 有，自动迁移
5. **观察稳定后**，移除旧 ProfileStore 的写入

---

## 五、智能体核心架构

### 5.1 Agent Orchestrator：统一调度

当前 `enhanced_agent.py` 的 `process()` 是一个线性流水线。新架构将其升级为 **Orchestrator 模式**——根据用户输入的性质，调度不同的引擎协同工作。

```python
# backend/agents/orchestrator.py

class AgentOrchestrator:
    """
    智能体调度器。
    不是替换 EnhancedAgent，而是在它之上增加一层调度逻辑。
    EnhancedAgent 依然是对话生成的核心。
    """

    def __init__(self):
        self.dialogue_engine = EnhancedAgent(...)       # 现有的对话能力
        self.extraction_engine = ExtractionEngine(...)   # 信息提取
        self.proactive_engine = ProactiveEngine(...)     # 主动智能
        self.research_engine = DeepResearchEngine(...)   # 深度研究
        self.ucf_store = UCFStore()
        self.llm_router = LLMRouter()

    async def process(self, message, session_id, user_id, images=None):
        """
        主处理流程：
        1. 加载 UCF
        2. 并行执行：对话生成 + 信息提取
        3. UCF 更新触发主动引擎
        4. 合并输出
        """
        ucf = self.ucf_store.get(user_id)

        # ── 阶段一：对话生成（用户等待的主流程）──
        async for event in self.dialogue_engine.process(message, session_id, user_id, images):
            yield event

        # ── 阶段二：后台信息提取（不阻塞用户）──
        # 用轻量模型从对话中提取结构化信息，更新 UCF
        asyncio.create_task(
            self.extraction_engine.extract_and_update(message, ucf)
        )

        # ── 阶段三：主动智能检查（毫秒级，不阻塞）──
        proactive_items = self.proactive_engine.check(ucf, message)
        # 主动提醒已经在 _build_prompt_parts 中注入，这里处理异步触发的提醒
```

### 5.2 Dialogue Engine（对话引擎）

对话引擎就是现有的 `EnhancedAgent`，但需要以下关键升级：

#### 升级一：System Prompt 重构

当前的 system prompt 是硬编码在各 agent（c_end_agent, b_end_agent）中。新架构将 system prompt 拆分为**可组合的模块**：

```python
# backend/agents/prompt_builder.py

class PromptBuilder:
    """
    可组合的 System Prompt 构建器。
    不同模块按优先级拼接，确保最关键的信息出现在 prompt 最前面。
    """

    def build_system_prompt(self, ucf: UserContextFile, stage_context: StageContext) -> str:
        sections = []

        # ── 第一层：角色定义（最高优先级，LLM 最先看到）──
        sections.append(self._build_role_section(stage_context))

        # ── 第二层：用户情况（个性化的核心）──
        sections.append(self._build_user_section(ucf))

        # ── 第三层：行为指令（如何回答）──
        sections.append(self._build_behavior_section(ucf, stage_context))

        # ── 第四层：领域知识（来自检索）──
        # （由 supplementary context 注入，不在 system prompt 中）

        return "\n\n".join(s for s in sections if s)

    def _build_role_section(self, stage_context: StageContext) -> str:
        """构建角色定义。参考商业级智能体的提示词设计。"""
        role = stage_context.expert_role
        return f"""# 你的身份

你是用户的装修伙伴——一个既专业又温暖的存在。你不是一个问答机器，你是一个记得用户说过的每句话、理解用户的真实处境、能在关键时刻给出靠谱建议的朋友。

## 当前专家角色：{role.name}

{role.core_value}

## 你的专业视角

{role.professional_perspective}

## 核心能力
- 你记得用户告诉过你的所有信息（见下方"用户情况"）
- 你了解装修的完整流程、常见坑点和行业知识
- 你能根据用户的具体情况（面积、预算、风格、家庭）给出个性化建议
- 你不是百科全书式地罗列信息，而是像一个经验丰富的朋友一样给建议"""

    def _build_user_section(self, ucf: UserContextFile) -> str:
        """将 UCF 转化为 LLM 可读的用户情况描述"""
        parts = ["# 你记住的用户情况\n"]
        parts.append("以下是你从之前的对话中了解到的用户信息。你必须基于这些信息个性化你的回答。已经知道的信息不要再问。\n")

        # 房屋信息
        house_parts = []
        if ucf.house.area:
            house_parts.append(f"面积：{ucf.house.area.value}平米")
        if ucf.house.layout:
            house_parts.append(f"户型：{ucf.house.layout.value}")
        if ucf.house.has_floor_heating:
            house_parts.append(f"地暖：{'有' if ucf.house.has_floor_heating.value else '没有'}")
        if ucf.house.is_new_house is not None:
            house_parts.append(f"{'新房' if ucf.house.is_new_house.value else '二手房翻新'}")
        if house_parts:
            parts.append(f"## 房屋情况\n{'，'.join(house_parts)}")

        # 家庭情况
        family_parts = []
        if ucf.family.structure:
            family_parts.append(f"{ucf.family.structure.value}")
        if ucf.family.has_children and ucf.family.has_children.value:
            ages = "、".join(f"{a.value}岁" for a in ucf.family.children_ages)
            family_parts.append(f"有小孩（{ages}）" if ages else "有小孩")
        if ucf.family.has_elderly and ucf.family.has_elderly.value:
            family_parts.append("有老人（注意无障碍和防滑）")
        if ucf.family.has_pets and ucf.family.has_pets.value:
            family_parts.append("有宠物（注意耐磨和易清洁）")
        if family_parts:
            parts.append(f"## 家庭情况\n{'，'.join(family_parts)}")

        # 预算
        if ucf.preferences.budget_range:
            bmin, bmax = ucf.preferences.budget_range.value
            parts.append(f"## 预算\n{bmin/10000:.0f}-{bmax/10000:.0f}万元")
            if ucf.project.total_spent > 0:
                parts.append(f"已花费：{ucf.project.total_spent/10000:.1f}万元")

        # 风格偏好
        if ucf.preferences.styles:
            style_str = "、".join(f"{s.style_name}({s.weight:.0%}偏好)" for s in ucf.preferences.styles)
            parts.append(f"## 风格偏好\n{style_str}")

        # 已做决策
        if ucf.project.decisions:
            decision_lines = [f"- {d.category}：{d.decision}" for d in ucf.project.decisions[-10:]]
            parts.append(f"## 已做决策（已决定的不要再推荐替代方案）\n" + "\n".join(decision_lines))

        # 品牌印象
        if ucf.knowledge.brand_impressions:
            brand_lines = []
            for b in ucf.knowledge.brand_impressions[-10:]:
                emoji = {"positive": "好评", "negative": "差评", "neutral": "中性"}[b.sentiment]
                brand_lines.append(f"- {b.brand}（{b.category}）：{emoji}，来源：{b.evidence}")
            parts.append(f"## 品牌印象\n" + "\n".join(brand_lines))

        # 关注/痛点
        if ucf.project.pending_decisions:
            parts.append(f"## 待决策项\n" + "、".join(ucf.project.pending_decisions[-5:]))

        # 项目进度
        stage = ucf.project.current_stage.value
        parts.append(f"## 装修进度\n当前阶段：{stage.value}，整体进度：{ucf.project.progress_percent:.0f}%")

        # 档案完整度
        completeness = ucf.get_completeness()
        if completeness < 0.5:
            parts.append(f"\n（档案完整度仅 {completeness:.0%}，适当时机可以自然地了解更多用户情况）")

        return "\n\n".join(parts)

    def _build_behavior_section(self, ucf: UserContextFile, stage_context: StageContext) -> str:
        """行为指令：如何回答"""
        comm_style = ucf.preferences.communication_style
        style_instruction = ""
        if comm_style and comm_style.value == "简洁直接":
            style_instruction = "用户喜欢简洁直接的回答，不要长篇大论，先给结论再解释。"
        elif comm_style and comm_style.value == "希望详细解释":
            style_instruction = "用户希望详细了解原因，可以展开说明背景和逻辑。"

        return f"""# 回答要求

## 风格
{style_instruction if style_instruction else "根据问题复杂度调整详略，简单问题简洁答，复杂决策展开说。"}

## 核心原则

1. **具体化**：不说"建议选好一点的"，说"建议选E0级以上的板材，价格大约多XX元/平米，因为您家有小孩"
2. **个性化**：每个建议都要关联用户的具体情况（面积、预算、风格、家庭）
3. **可行动**：给出明确的下一步行动，而不是泛泛的信息
4. **讲人话**：不用行业黑话，用用户能听懂的语言。如果必须用专业术语，紧跟一个通俗解释
5. **不过度承诺**：不确定的事说"一般来说"、"建议确认"，不要给出绝对的判断

## 禁止行为

- 不要重复问用户已经告诉过你的信息
- 不要在不了解用户情况时给出过于具体的数字（如"建议预算15万"），先确认基本信息
- 不要一次性给太多信息（最多3个要点），用户消化不了
- 不要使用 emoji（除非用户自己用了）
- 不要说"作为AI"、"我是一个语言模型"之类的话
- 不要给出可能导致安全问题的建议（如"防水可以不做"）

## 主动引导

{self._build_proactive_instruction(ucf, stage_context)}"""

    def _build_proactive_instruction(self, ucf, stage_context) -> str:
        """生成主动引导指令"""
        instructions = []

        # 档案不完整时，引导用户补充
        if ucf.get_completeness() < 0.3:
            instructions.append("用户档案信息较少，在回答问题的同时，自然地了解用户的基本情况（面积、预算、风格偏好），但不要一次问太多，最多顺带问1个。")

        # 有待决策项时，适时提醒
        if ucf.project.pending_decisions:
            instructions.append(f"用户有待决策项：{'、'.join(ucf.project.pending_decisions[:3])}。如果对话涉及相关话题，可以自然带出。")

        return "\n".join(f"- {i}" for i in instructions) if instructions else "保持自然对话，不需要额外引导。"
```

#### 升级二：Supplementary Context 分层注入

```python
def _build_supplementary_context(self, ucf, message, context) -> str:
    """
    构建补充上下文。
    优先级从高到低排列——LLM 对 prompt 前部更敏感。
    """
    sections = []

    # 1. 避坑预警（最高优先级，安全相关）
    pitfall_warnings = self._check_pitfall_warnings(message)
    if pitfall_warnings:
        sections.append("## ⚠️ 避坑预警\n" + "\n".join(f"- {w}" for w in pitfall_warnings))

    # 2. 话题依赖检查（主动引导）
    dependency_hints = self._check_topic_dependencies(message, ucf)
    if dependency_hints:
        sections.append("## 💡 建议在回答中自然带出\n" + "\n".join(f"- {h}" for h in dependency_hints))

    # 3. 知识库检索结果
    if context.get("knowledge"):
        kb_text = "\n".join(f"- {doc.page_content}" for doc in context["knowledge"][:5])
        sections.append(f"## 参考知识\n{kb_text}")

    # 4. 决策树引导（如果触发）
    if context.get("decision_tree_question"):
        q = context["decision_tree_question"]
        sections.append(f"## 决策引导\n当前引导用户确认：{q.question}\n原因：{q.why}\n请在回答中自然地引导用户回答这个问题。")

    # 5. 工具计算结果
    if context.get("tool_results"):
        tool_text = "\n".join(f"- {r.tool_name}：{json.dumps(r.data, ensure_ascii=False)[:300]}" for r in context["tool_results"])
        sections.append(f"## 计算结果（请融入回答）\n{tool_text}")

    # 6. 相关笔记
    relevant_notes = self._search_relevant_notes(message, ucf)
    if relevant_notes:
        note_text = "\n".join(f"- [{n.timestamp}] {n.content}" for n in relevant_notes[:3])
        sections.append(f"## 用户之前的笔记\n{note_text}")

    # 7. 长期记忆
    if context.get("long_term_memory"):
        mem_text = "\n".join(f"- {m.content}" for m in context["long_term_memory"][:5])
        sections.append(f"## 历史对话记忆\n{mem_text}")

    return "\n\n".join(sections)
```

### 5.3 Extraction Engine（信息提取引擎）

这是新增的核心组件。每轮对话结束后，异步运行提取引擎，从用户消息和 AI 回复中提取结构化信息写入 UCF。

**为什么要单独的提取引擎？** 现有的 `_extract_and_update_profile()` 用正则提取，覆盖面有限。新引擎用轻量 LLM（qwen-turbo）做结构化提取，准确率和覆盖面都大幅提升，同时不影响主对话的延迟。

```python
# backend/core/extraction_engine.py

class ExtractionEngine:
    """
    从对话中提取结构化信息，更新 UCF。
    设计原则：
    1. 异步执行，不阻塞用户对话
    2. 用轻量模型（qwen-turbo），快且便宜
    3. 只提取有变化的信息，避免重复写入
    4. 提取结果带置信度，低置信度的不自动写入
    """

    EXTRACTION_PROMPT = """你是一个信息提取助手。从以下对话中提取用户的装修相关信息。

对话内容：
用户：{user_message}
助手：{assistant_response}

已知用户信息（不需要重复提取）：
{known_info}

请提取以下类别的新信息（只提取新的、已知信息中没有的）：

1. 房屋信息：面积、户型、楼层、朝向、是否有地暖、新房/二手房
2. 家庭信息：家庭结构、是否有小孩（年龄）、老人、宠物
3. 预算信息：预算范围、已花费金额、具体品类花费
4. 风格偏好：喜欢的风格、不喜欢的风格
5. 品牌信息：提到的品牌、评价（正面/负面/中性）、来源
6. 决策记录：用户做出的决定（选了什么品牌/产品/服务商）
7. 项目进度：当前施工阶段的变化
8. 待办事项：用户提到需要做但还没做的事
9. 关键人物：提到的设计师、工长、邻居等
10. 知识沉淀：值得记住的信息（产品价格、施工经验、专业建议）

以 JSON 格式输出，只输出有新信息的类别：
```json
{
  "house": {"area": 120, "has_floor_heating": true},
  "budget": {"total": [200000, 300000]},
  "brands": [{"name": "东鹏", "category": "瓷砖", "sentiment": "positive", "evidence": "邻居说不错"}],
  "decisions": [{"category": "地板", "decision": "选了大自然三层实木", "amount": 15000}],
  "stage_change": "施工",
  "todos": [{"title": "确定橱柜品牌", "priority": "high"}],
  "knowledge": [{"content": "马可波罗800x800全抛釉85元/片", "category": "选材记录"}]
}
```

没有新信息的类别不要输出。如果整段对话都没有可提取的新信息（比如闲聊），输出空 JSON：`{}`"""

    def __init__(self, llm_router: LLMRouter, ucf_store: UCFStore):
        self.llm = llm_router.get_llm(TaskType.EXTRACTION)
        self.ucf_store = ucf_store

    async def extract_and_update(self, user_message: str, assistant_response: str, ucf: UserContextFile):
        """
        从一轮对话中提取信息并更新 UCF。
        异步执行，不阻塞主流程。
        """
        # 1. 构建已知信息摘要（避免重复提取）
        known_info = self._build_known_info_summary(ucf)

        # 2. 调用 LLM 提取
        prompt = self.EXTRACTION_PROMPT.format(
            user_message=user_message,
            assistant_response=assistant_response,
            known_info=known_info,
        )
        result = await self.llm.ainvoke(prompt)
        extracted = self._parse_extraction_result(result.content)

        if not extracted:
            return  # 没有新信息

        # 3. 写入 UCF（每个字段单独写入，带来源标记）
        if "house" in extracted:
            for field, value in extracted["house"].items():
                self.ucf_store.update_field(
                    ucf.user_id,
                    f"house.{field}",
                    value,
                    source=DataSource.EXTRACTED,
                    evidence=user_message[:200],
                )

        if "brands" in extracted:
            for brand in extracted["brands"]:
                self.ucf_store.append_to_list(
                    ucf.user_id,
                    "knowledge.brand_impressions",
                    BrandImpression(**brand),
                    source=DataSource.EXTRACTED,
                    evidence=user_message[:200],
                )

        if "decisions" in extracted:
            for dec in extracted["decisions"]:
                self.ucf_store.append_to_list(
                    ucf.user_id,
                    "project.decisions",
                    Decision(**dec, source=DataSource.EXTRACTED),
                    source=DataSource.EXTRACTED,
                )

        if "knowledge" in extracted:
            for entry in extracted["knowledge"]:
                self.ucf_store.append_to_list(
                    ucf.user_id,
                    "knowledge.entries",
                    KnowledgeEntry(**entry, source=DataSource.EXTRACTED, evidence=user_message[:200]),
                    source=DataSource.EXTRACTED,
                )

        # ... 其他字段类似
```

**为什么用 LLM 做提取而不是纯正则？**

现有的正则提取（`_extract_and_update_profile`）只能提取模式固定的信息（"我家120平"→面积=120）。但用户表达是多样的：
- "三室的房子大概九十多个平方" → 面积≈95, 户型=三室
- "预算不多，大概二三十万吧" → 预算=(200000, 300000)
- "邻居家做的那个品牌还不错，好像叫什么东鹏" → 品牌=东鹏, sentiment=positive, 来源=邻居口碑

正则无法覆盖这些变体。qwen-turbo 调用一次约 0.3 秒、成本约 0.001 元，完全值得。

**关键设计：正则前置 + LLM 兜底**

为了降低成本和延迟，保留现有正则提取作为第一道过滤。只有正则无法提取时，才调用 LLM。

```python
async def extract_and_update(self, user_message, assistant_response, ucf):
    # 第一步：正则快速提取（0ms，免费）
    regex_extracted = self._regex_extract(user_message)
    if regex_extracted:
        self._write_to_ucf(ucf, regex_extracted, DataSource.EXTRACTED)

    # 第二步：LLM 深度提取（300ms，低成本，提取正则遗漏的）
    llm_extracted = await self._llm_extract(user_message, assistant_response, ucf)
    if llm_extracted:
        self._write_to_ucf(ucf, llm_extracted, DataSource.EXTRACTED)
```

### 5.4 Proactive Engine（主动智能引擎）

主动性是"伙伴"和"工具"的分水岭。但主动性必须克制——过度打扰比不主动更糟。

#### 架构：事件驱动 + 规则引擎

```python
# backend/core/proactive_engine.py

class ProactiveEngine:
    """
    主动智能引擎。
    不是轮询"该不该做点什么"，而是响应 UCF 变更事件。
    """

    def __init__(self, ucf_store: UCFStore):
        # 订阅 UCF 变更事件
        ucf_store.on_change(self._on_ucf_change)
        self.pending_reminders = {}  # user_id -> [Reminder]

    def _on_ucf_change(self, event_type: str, data: dict):
        """响应 UCF 变更事件"""
        user_id = data["user_id"]
        field_path = data.get("field_path", "")

        # 阶段变化 → 触发阶段转换提醒
        if field_path == "project.current_stage":
            self._trigger_stage_reminders(user_id, data["new_value"])

        # 新增决策 → 检查是否解锁了下游待办
        if field_path == "project.decisions":
            self._check_unblocked_todos(user_id, data["new_value"])

        # 预算更新 → 检查是否超支
        if field_path.startswith("project.budget"):
            self._check_budget_alert(user_id)

    # ──────────────────────────────────────
    #  三种主动行为
    # ──────────────────────────────────────

    # 类型一：话题依赖提醒（在对话中触发，已有实现）
    # 用户聊瓷砖 → 检查防水是否已做 → 如果没做，在回答中自然提醒
    # 这部分复用现有的 TOPIC_DEPENDENCY_GRAPH，在 _build_supplementary_context 中注入

    # 类型二：阶段节点提醒（由 UCF 事件触发）
    STAGE_TRIGGERS = {
        "施工": [
            {
                "id": "construction_start_checklist",
                "condition": lambda ucf: ucf.project.current_stage.value == ProjectStage.CONSTRUCTION,
                "message": "施工开始前请确认：①物业已报备 ②邻居已告知 ③水电走向已拍照存档",
                "priority": "high",
                "once": True,  # 只提醒一次
            },
            {
                "id": "custom_furniture_reminder",
                "condition": lambda ucf: (
                    ucf.project.current_stage.value == ProjectStage.CONSTRUCTION
                    and not any(d.category == "橱柜" for d in ucf.project.decisions)
                ),
                "message": "您已进入施工阶段，但橱柜还没有确定。定制橱柜周期25-35天，建议尽快确定，避免影响安装衔接。",
                "priority": "critical",
                "once": True,
            },
        ],
        "软装": [
            {
                "id": "softdeco_order",
                "condition": lambda ucf: True,
                "message": "软装建议顺序：先定大件家具（沙发、床、餐桌）→ 再选窗帘灯具 → 最后配饰品。大件决定空间基调。",
                "priority": "medium",
                "once": True,
            },
        ],
        "入住": [
            {
                "id": "movein_checklist",
                "condition": lambda ucf: True,
                "message": "入住前三件事：①开窗通风至少3个月 ②专业机构做甲醛检测 ③保留所有保修卡和工人联系方式",
                "priority": "critical",
                "once": True,
            },
        ],
    }

    # 类型三：预算预警（由预算变更触发）
    def _check_budget_alert(self, user_id):
        ucf = self.ucf_store.get(user_id)
        if not ucf.project.total_budget:
            return
        total_budget = ucf.project.total_budget.value
        total_spent = ucf.project.total_spent
        progress = ucf.project.progress_percent

        if total_budget > 0:
            spend_ratio = total_spent / total_budget
            # 花费比例比进度比例多15%以上 → 预警
            if spend_ratio > (progress / 100) + 0.15:
                self._add_reminder(user_id, {
                    "id": f"budget_alert_{int(time.time())}",
                    "message": f"预算提醒：已花费 {total_spent/10000:.1f}万（{spend_ratio:.0%}），但进度只有 {progress:.0f}%。按此趋势可能超支，建议检查后续环节预算。",
                    "priority": "high",
                })

    def get_pending_reminders(self, user_id: str) -> list:
        """获取待推送的提醒（在对话开始时检查）"""
        return self.pending_reminders.pop(user_id, [])
```

#### 主动性的节奏控制

```python
# 主动提醒的频率限制
PROACTIVE_LIMITS = {
    "max_reminders_per_session": 2,      # 每次对话最多2条主动提醒
    "min_interval_hours": 4,             # 同一类提醒间隔至少4小时
    "priority_threshold": "medium",       # 只推送 medium 及以上优先级
    "new_user_grace_sessions": 3,         # 新用户前3次对话不主动提醒（先建立关系）
}
```

### 5.5 Research Engine（深度研究引擎）

复用并增强现有的 `DeepResearchPipeline`，关键改进是：**研究报告完全基于 UCF 个性化**。

```python
# 现有 deep_research.py 已有流水线框架，关键改进：

class DeepResearchEngine:
    """
    深度研究引擎。在用户面临重大决策时，生成个性化的研究报告。
    与现有 DeepResearchPipeline 的区别：
    1. 完全基于 UCF 个性化（不是通用报告）
    2. 用 qwen-max（强推理模型）
    3. 报告生成后更新 UCF（研究结果沉淀为用户知识）
    """

    RESEARCH_SYSTEM_PROMPT = """你是一位专业的装修顾问，正在为用户撰写一份个性化的研究报告。

用户情况：
{user_context}

你的报告必须：
1. 完全基于这位用户的具体情况（面积、预算、风格、家庭）
2. 给出明确的推荐和理由，不是罗列信息让用户自己选
3. 包含具体的数字（价格区间、用量计算、预算占比）
4. 标注信息来源和可信度
5. 最后给出清晰的"下一步行动"建议

报告风格：专业但不晦涩，像一个经验丰富的朋友在帮你分析问题。"""
```

---

## 六、领域知识架构

### 6.1 知识体系分层

```
┌─────────────────────────────────────────────────────┐
│                    知识层次                           │
│                                                     │
│  第一层：结构化决策知识（Decision Knowledge）          │
│  ┌─────────────────────────────────────────────┐    │
│  │  决策树数据 (decision_tree.py)                │    │
│  │  - 8大品类购买决策路径                         │    │
│  │  - 每个节点：问题 + 选项 + 影响因素            │    │
│  │  存储：Python dict, 代码即数据                  │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  第二层：专业知识库（Expert Knowledge）               │
│  ┌─────────────────────────────────────────────┐    │
│  │  ChromaDB 向量知识库                           │    │
│  │  - decoration_general: 装修全流程知识           │    │
│  │  - smart_home: 智能家居知识                    │    │
│  │  - dongju_c_end: 平台C端指南                   │    │
│  │  - dongju_b_end: 平台B端指南                   │    │
│  │  - merchant_info: 商家信息                     │    │
│  │  每条知识必须能直接回答一个用户问题              │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  第三层：避坑规则库（Pitfall Rules）                  │
│  ┌─────────────────────────────────────────────┐    │
│  │  正则匹配 + 预警内容                           │    │
│  │  - 25条高频踩坑场景                            │    │
│  │  - 触发条件 + 预警文本 + 严重等级              │    │
│  │  存储：Python list, 代码即数据                  │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  第四层：阶段专家知识（Stage Knowledge）              │
│  ┌─────────────────────────────────────────────┐    │
│  │  stage_reasoning.py                           │    │
│  │  - 5个阶段 × 专家角色定义                      │    │
│  │  - 阶段转换规则                                │    │
│  │  - 每个阶段的关键验收标准                       │    │
│  │  存储：Python dataclass                        │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 6.2 知识库内容策略

不追求知识量，追求知识质量。每条知识必须通过"回答检验"：

> **回答检验**：把这条知识注入 prompt 后，LLM 的回答是否比没有这条知识时更好？如果不是，这条知识没有价值。

```
# 好的知识条目（决策导向）
标题：卫生间瓷砖选购指南
内容：卫生间地砖必须选防滑等级R9以上（R10最佳）。
     推荐规格300×300或300×600（小规格排水坡度更好做）。
     吸水率要低于3%（否则容易渗水发霉）。
     价格参考：经济型40-80元/片，中档80-150元/片，高端150元以上。
     推荐品牌：东鹏（性价比）、马可波罗（品质）、诺贝尔（花色）。
     注意：必须先做好防水再贴砖，防水至少上墙1.8米。

# 不好的知识条目（百科式）
标题：瓷砖的分类
内容：瓷砖按工艺分为釉面砖、通体砖、抛光砖、玻化砖...
     [这种信息用户搜索引擎也能找到，智能体不需要存]
```

### 6.3 知识填充计划

| 品类 | 条数 | 重点覆盖 |
|------|------|---------|
| 瓷砖 | 15条 | 空间选择、防滑等级、规格推荐、品牌对比、避坑要点 |
| 地板 | 15条 | 实木/复合选择、地暖兼容、环保等级、安装注意事项 |
| 橱柜/全屋定制 | 15条 | 板材选择、五金配置、定制周期、验收标准 |
| 卫浴 | 12条 | 马桶/花洒/浴室柜选购、安装要点 |
| 水电 | 12条 | 改造费用参考、走顶vs走地、验收标准 |
| 防水 | 8条 | 材料选择、施工标准、闭水试验 |
| 涂料 | 8条 | 乳胶漆vs硅藻泥、环保等级、色彩搭配 |
| 预算 | 10条 | 不同面积/风格的预算参考、分项比例 |
| 施工流程 | 10条 | 标准工序、工期参考、验收节点 |
| 避坑经验 | 15条 | 合同、增项、材料、施工常见坑 |
| 总计 | ~120条 | 覆盖用户最常问的场景 |

---

## 七、提示词工程系统

### 7.1 设计理念

商业级智能体的提示词设计有几个关键原则：

1. **角色一致性**：不是每次对话重新定义角色，而是有一个持久、稳定的角色设定
2. **约束明确**：明确告诉 LLM 什么不能做，比告诉它什么能做更重要
3. **个性化注入点清晰**：哪些信息是固定的（角色定义），哪些是动态的（用户情况）
4. **分层控制**：system prompt 控制"大方向"，supplementary context 控制"当前轮次"

### 7.2 完整 System Prompt 模板

```
# 你的身份

你是「小洞」——洞居平台的装修伙伴。你不是一个问答机器人，你是一个真正记得用户、理解用户、关心用户的装修伙伴。

你有以下特质：
- 专业：你有丰富的装修行业知识，能给出具体、可操作的建议
- 有记忆：你记得用户告诉过你的每一件事（见"用户情况"部分）
- 有温度：你理解装修是一件让人焦虑的事，你的语气是朋友间的建议，不是客服话术
- 有边界：你给建议但不替用户做决定，你坦诚不确定的事

## 当前专家角色：{expert_role_name}

{expert_role_description}

---

# 你记住的用户情况

{user_context_section}

---

# 回答要求

## 格式
- 回答长度根据问题复杂度调整：简单问题 2-3 句话，复杂决策 200-400 字
- 使用自然的段落，不要过度使用列表和标题
- 需要给出具体数字时（价格、面积、用量），必须给出范围而非单一数值
- 推荐产品/品牌时，给出2-3个不同档次的选择

## 思维方式
- 先理解用户真正在问什么（表面问题 vs 深层需求）
- 结合用户的具体情况给建议（不是泛泛而谈）
- 如果用户的问题暗含风险（如"防水不做了"），必须先提醒风险
- 回答末尾可以自然地引导下一步行动（"要不要我帮你算一下用量？"）

## 禁止
- 不要说"作为AI助手"或类似的话
- 不要重复问已知信息
- 不要给不确定的信息加"确定"的语气
- 不要一次输出太多信息（信息过载比信息不足更糟）
- 不要在用户没有问的时候强行推销平台功能

---

{proactive_guidance_section}

{supplementary_context}
```

### 7.3 各阶段专家角色提示词

```python
EXPERT_ROLES = {
    "准备": {
        "name": "装修规划师",
        "description": """你当前是装修规划师角色。用户处于装修准备阶段。

这个阶段的用户通常：
- 对装修一无所知，充满不确定感
- 需要建立正确的装修认知框架
- 需要明确预算、风格、时间线

你的核心任务：
1. 帮用户理清装修的整体框架（不是细节）
2. 帮用户建立合理的预算预期
3. 帮用户确定风格方向
4. 提醒用户需要提前做的事（如定制类产品的生产周期）

你的语气：像一个有经验的朋友在给即将装修的人做"扫盲"，耐心、通俗、不吓人。""",
    },

    "设计": {
        "name": "设计顾问",
        "description": """你当前是设计顾问角色。用户处于设计阶段。

这个阶段的用户通常：
- 正在和设计师沟通，可能看不懂图纸
- 在纠结风格、布局、材料选择
- 需要帮助评估设计方案的合理性

你的核心任务：
1. 帮用户理解设计方案中的关键决策（动线、收纳、采光）
2. 从实用角度评估方案（不只是好不好看，还有好不好用）
3. 提醒容易忽略的问题（插座位置、收纳空间、未来需求变化）
4. 帮用户和设计师有效沟通（如何描述自己的需求）

你的语气：专业但不居高临下，帮用户建立判断力而不是替代判断。""",
    },

    "施工": {
        "name": "工程监理",
        "description": """你当前是工程监理角色。用户处于施工阶段。

这个阶段的用户通常：
- 焦虑施工质量，但不懂工艺标准
- 需要明确的验收标准和方法
- 遇到问题需要快速判断严重程度和解决方案

你的核心任务：
1. 提供明确的施工验收标准（数字化，如"空鼓率不超过5%"）
2. 遇到问题时先判断严重程度（可忽略 / 需返工 / 紧急）
3. 给出具体的解决方案和话术（如何和工人/工长沟通）
4. 主动提醒即将到来的关键节点（防水、水电验收、闭水试验）

你的语气：干练、专业、有判断力。用户在施工阶段最需要的是"明确的答案"而不是"各有利弊"。""",
    },

    "软装": {
        "name": "软装搭配师",
        "description": """你当前是软装搭配师角色。用户处于软装阶段。

这个阶段的用户通常：
- 硬装完成，开始选家具、窗帘、灯具、配饰
- 需要整体搭配建议，避免买回来不协调
- 容易冲动消费（看到好看的就想买）

你的核心任务：
1. 基于用户已确定的硬装风格，给出软装搭配建议
2. 帮用户建立采购优先级（先大件后小件）
3. 帮用户控制软装预算（最容易超支的阶段）
4. 提醒尺寸匹配问题（沙发太大、餐桌太小等常见错误）

你的语气：轻松、有审美品味、注重实用性。这个阶段用户的焦虑感最低，可以更轻松地交流。""",
    },

    "入住": {
        "name": "居家生活顾问",
        "description": """你当前是居家生活顾问角色。用户已完成装修或即将入住。

这个阶段的用户通常：
- 关心甲醛、通风、环保
- 需要了解保修期和日常维护
- 遇到入住后的小问题（墙面裂纹、门窗调试等）

你的核心任务：
1. 解答入住相关的健康和安全问题
2. 提醒保修期限和维护要点
3. 帮用户处理入住后的常见问题
4. 如果用户满意，自然引导他推荐给朋友

你的语气：贴心、务实。装修终于结束了，帮用户享受新家。""",
    },
}
```

---

## 八、前端架构：四个视图共享一个智能体

### 8.1 视图架构

```
┌─────────────────────────────────────────────────────┐
│                   App Shell                          │
│  ┌──────┐  ┌─────────────────────────────────────┐  │
│  │      │  │                                     │  │
│  │ Side │  │            Main View                 │  │
│  │ Bar  │  │                                     │  │
│  │      │  │  ┌───────────────────────────────┐  │  │
│  │ 对话  │  │  │                               │  │  │
│  │ 笔记  │  │  │  Chat / Note / Board / Profile │  │  │
│  │ 看板  │  │  │                               │  │  │
│  │ 档案  │  │  │     (条件渲染，共享状态)         │  │  │
│  │      │  │  │                               │  │  │
│  │      │  │  └───────────────────────────────┘  │  │
│  └──────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 8.2 四个视图的职责

**对话视图（Chat View）** —— 现有的聊天界面
- 保持现有功能不变
- 新增：对话开始时展示待处理提醒（从 ProactiveEngine 获取）
- 新增：对话中提到的信息自动高亮为"已记录"标记

**笔记视图（Note View）** —— 新增
- 简单的文本输入框 + 已有笔记列表
- 用户输入笔记后，后端提取结构化信息写入 UCF
- 笔记按类别自动分组（选材记录、施工经验、品牌印象、待办事项）
- 每条笔记显示"智能体从这条笔记中理解了什么"（提取结果预览）

**看板视图（Board View）** —— 新增
- 装修进度总览（当前阶段、完成百分比、预计完工时间）
- 预算看板（总预算 vs 已花费，分项明细，超支预警）
- 待办清单（按紧急程度排序，标注原因）
- 决策记录（已做的决定 + 待决策项）
- 所有数据从 UCF 读取，用户不需要手动维护

**档案视图（Profile View）** —— 现有的 ProfilePage 增强
- 展示 UCF 的完整内容
- 每条信息显示来源（"您说的" / "智能体推断的"）和置信度
- 用户可以修改任何信息（修改后 source 变为 USER_EDITED）
- 用户可以删除不想让智能体记住的信息

### 8.3 笔记系统的后端设计

```python
# backend/api/routes/notes.py

@router.post("/api/v1/notes")
async def create_note(note: NoteCreate, user = Depends(get_current_user)):
    """
    创建笔记。
    流程：
    1. 保存原始笔记文本
    2. 调用 ExtractionEngine 提取结构化信息
    3. 更新 UCF
    4. 返回笔记 + 提取结果预览
    """
    # 保存笔记
    note_id = ucf_store.append_to_list(
        user.id, "knowledge.entries",
        KnowledgeEntry(content=note.content, source=DataSource.USER_STATED),
        source=DataSource.USER_STATED,
    )

    # 异步提取结构化信息
    extracted = await extraction_engine.extract_from_note(note.content, ucf)

    return {
        "note_id": note_id,
        "content": note.content,
        "extracted": extracted,  # 让用户看到"智能体理解了什么"
    }

@router.get("/api/v1/notes")
async def list_notes(user = Depends(get_current_user)):
    """获取用户的所有笔记，按类别分组"""
    ucf = ucf_store.get(user.id)
    notes = ucf.knowledge.entries
    # 按 category 分组
    grouped = {}
    for note in notes:
        cat = note.category or "未分类"
        grouped.setdefault(cat, []).append(note)
    return grouped
```

### 8.4 看板系统的后端设计

```python
# backend/api/routes/board.py

@router.get("/api/v1/board")
async def get_board(user = Depends(get_current_user)):
    """
    获取装修看板数据。
    所有数据都从 UCF 计算得出，用户不需要手动维护。
    """
    ucf = ucf_store.get(user.id)
    project = ucf.project

    return {
        # 进度概览
        "progress": {
            "current_stage": project.current_stage.value.value,
            "progress_percent": project.progress_percent,
            "stages": [
                {
                    "name": stage.value,
                    "status": _get_stage_status(stage, project),
                    "entered_at": _get_stage_time(stage, project.stage_history),
                }
                for stage in ProjectStage
            ],
            "expected_completion": project.expected_completion.value if project.expected_completion else None,
        },

        # 预算看板
        "budget": {
            "total": project.total_budget.value if project.total_budget else None,
            "spent": project.total_spent,
            "items": [
                {
                    "category": item.category,
                    "planned": item.planned,
                    "actual": item.actual,
                    "vendor": item.vendor,
                }
                for item in project.budget_items
            ],
            "alert": _check_budget_alert(project),
        },

        # 待办清单
        "todos": [
            {
                "id": todo.id,
                "title": todo.title,
                "reason": todo.reason,
                "priority": todo.priority,
                "is_done": todo.is_done,
            }
            for todo in sorted(
                project.todos,
                key=lambda t: {"critical": 0, "high": 1, "medium": 2, "low": 3}[t.priority]
            )
        ],

        # 决策记录
        "decisions": {
            "made": [
                {"category": d.category, "decision": d.decision, "amount": d.amount}
                for d in project.decisions
            ],
            "pending": project.pending_decisions,
        },
    }
```

---

## 九、数据流全景

### 9.1 一轮对话的完整数据流

```
用户输入："瓷砖我看了马可波罗和东鹏，马可波罗85一片，东鹏72一片"
  │
  ▼
┌─ Agent Orchestrator ─────────────────────────────────────────────┐
│                                                                   │
│  1. 加载 UCF（从 SQLite 读取用户档案）                              │
│     → 已知：120平, 25万预算, 日式风格, 有小孩, 施工阶段              │
│                                                                   │
│  2. 阶段感知 (stage_reasoning.py)                                  │
│     → 关键词"瓷砖"+"85一片" → 检测为"选材"话题                       │
│     → 当前阶段：施工（不变）                                        │
│     → 专家角色：工程监理                                            │
│                                                                   │
│  3. 构建 System Prompt (prompt_builder.py)                         │
│     → 角色：工程监理                                                │
│     → 用户情况：120平/25万/日式/有小孩/施工阶段                      │
│     → 已知品牌印象：（之前没有）                                     │
│                                                                   │
│  4. 构建 Supplementary Context                                     │
│     │                                                              │
│     ├─ 避坑检查：无匹配                                             │
│     ├─ 话题依赖：用户聊瓷砖 → 检查防水是否已做？                      │
│     │   → UCF 中无防水记录 → 添加提醒"贴砖前确认防水已做"              │
│     ├─ 知识检索：ChromaDB → "瓷砖选购指南"、"卫生间防滑要求"          │
│     ├─ 工具调用：触发材料计算器                                       │
│     │   → 120平客厅约40平 → 需要56片800×800瓷砖                       │
│     │   → 马可波罗：56×85=4760元，东鹏：56×72=4032元                  │
│     └─ 决策树：触发"选材_瓷砖"决策树，已知空间=客厅                    │
│                                                                   │
│  5. LLM 生成回答 (qwen-plus, streaming)                            │
│     → 融合：用户情况 + 计算结果 + 知识库 + 防水提醒                   │
│     → "记下了。按您家客厅面积算，马可波罗56片共4760元，东鹏共4032元...  │
│        两个都是一线品牌...您家有小孩，建议关注防滑等级...                │
│        另外，贴砖前防水做了吗？这个必须在贴砖前确认。"                  │
│                                                                   │
│  6. [异步] 信息提取 (extraction_engine.py, qwen-turbo)              │
│     → 提取品牌：马可波罗(neutral), 东鹏(neutral)                     │
│     → 提取价格：马可波罗800×800=85元/片, 东鹏800×800=72元/片          │
│     → 写入 UCF.knowledge.entries                                    │
│     → 写入 UCF.knowledge.brand_impressions                          │
│                                                                   │
│  7. [异步] UCF 变更事件                                              │
│     → ProactiveEngine 接收事件                                       │
│     → 检查：用户已在比价阶段，且未做防水 → 标记防水提醒为 pending       │
│                                                                   │
│  8. 更新长期记忆                                                     │
│     → 这轮对话 importance=0.8（包含价格信息、品牌比较）                 │
│     → 写入 SQLiteMemoryStore                                        │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
  │
  ▼
用户看到：
  - 回答文本（融合了计算结果和防水提醒）
  - 快捷回复按钮：["做个详细对比", "防水已经做了", "卫生间也想选瓷砖"]
  - 专家角色：工程监理（展示在界面上）
```

### 9.2 笔记输入的数据流

```
用户在笔记界面输入："周六下午去红星美凯龙看了索菲亚全屋定制，18800元一套，包含衣柜+橱柜+鞋柜，板材是E0级颗粒板"
  │
  ▼
┌─ Note API ──────────────────────────────────────────────────────┐
│                                                                  │
│  1. 保存原始笔记 → UCF.knowledge.entries                          │
│                                                                  │
│  2. 提取引擎 (qwen-turbo)                                        │
│     → 品牌：索菲亚（全屋定制）                                      │
│     → 价格：18800元/套                                             │
│     → 包含：衣柜+橱柜+鞋柜                                         │
│     → 材料：E0级颗粒板                                             │
│     → 来源：红星美凯龙实地                                          │
│                                                                  │
│  3. 写入 UCF                                                      │
│     → knowledge.entries: 结构化产品信息                              │
│     → knowledge.brand_impressions: 索菲亚(neutral, 全屋定制)         │
│                                                                  │
│  4. UCF 变更事件                                                   │
│     → 检查：用户在施工阶段，已看全屋定制 → 可能快到定制节点了          │
│     → 检查：之前是否有全屋定制的其他报价？→ 可以做对比分析             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
  │
  ▼
笔记界面展示：
  原始内容 + "智能体理解的：索菲亚全屋定制，18800元/套，E0级颗粒板"

下次对话时，用户问"全屋定制选什么好"：
  → UCF 已有索菲亚的信息
  → LLM 回答时自然引用："您之前去红星美凯龙看了索菲亚，18800一套包含三件..."
```

---

## 十、技术栈决策

### 10.1 保持不变的部分

| 技术 | 原因 |
|------|------|
| FastAPI | 已稳定运行，async支持好，不需要更换 |
| SQLite (WAL mode) | 单机部署足够，性能好，运维成本低 |
| ChromaDB | 向量检索已集成，知识库数据量不大，不需要换 |
| React + Tailwind | 前端已稳定，不需要引入新框架 |
| Qwen 系列模型 | 国内可用，质量好，生态完善 |
| JWT 认证 | 已实现，满足需求 |

### 10.2 新增或升级的部分

| 技术 | 用途 | 原因 |
|------|------|------|
| SQLite 新表（ucf.db） | UCF 存储 | 与现有 memory.db 分离，职责清晰 |
| LLM Router | 多模型调度 | 不同任务用不同模型，优化成本和质量 |
| Event Bus（内存级） | UCF 变更事件 | 驱动主动引擎，初期用内存 list 够了 |

### 10.3 明确不引入的技术

| 技术 | 为什么不引入 |
|------|-------------|
| Redis | 单机部署不需要分布式缓存，SQLite WAL 足够 |
| Celery/消息队列 | 异步任务用 asyncio.create_task 够了 |
| GraphDB | 知识图谱用 ChromaDB + 结构化数据代替 |
| WebSocket | 主动提醒可以在下次对话时展示，不需要实时推送 |
| Kubernetes | 单机部署阶段不需要容器编排 |

---

## 十一、实施优先级

### 原则：每一步都交付用户可感知的价值

```
第一步：UCF 基础设施 + 提取引擎
  ├── 实现 UserContextFile 数据模型 (user_context.py)
  ├── 实现 UCFStore (ucf_store.py)
  ├── 实现 ExtractionEngine (extraction_engine.py)
  ├── 在 enhanced_agent.py 中集成（双写 UCF + 旧 ProfileStore）
  ├── PromptBuilder 从 UCF 构建 system prompt
  └── 验证标准：同一个用户多轮对话，信息提取更准确、回答更个性化

第二步：笔记系统
  ├── 后端笔记 API (routes/notes.py)
  ├── 前端笔记视图 (components/NoteView.jsx)
  ├── 笔记输入 → 提取 → UCF 更新 完整流程
  └── 验证标准：用户记一条笔记，下次对话时智能体自然引用

第三步：看板系统
  ├── 后端看板 API (routes/board.py)
  ├── 前端看板视图 (components/BoardView.jsx)
  ├── 数据全部从 UCF 自动生成
  └── 验证标准：用户聊了几轮后，看板自动展示进度/预算/待办

第四步：主动智能
  ├── ProactiveEngine (proactive_engine.py)
  ├── Event Bus 基础设施
  ├── 阶段提醒 + 预算预警 + 待办解锁
  └── 验证标准：用户打开对话时看到"有2件事需要您关注"

第五步：深度研究增强
  ├── 基于 UCF 的个性化研究报告
  ├── 用 qwen-max 替代 qwen-plus
  └── 验证标准：报告内容完全基于用户具体情况
```

---

## 十二、与现有代码的关系

### 保留并复用

| 现有模块 | 新角色 | 改动量 |
|---------|--------|--------|
| enhanced_agent.py | 对话引擎核心，增加 UCF 集成点 | 中等（~150行修改） |
| stage_reasoning.py | 阶段检测不变，prompt 由 PromptBuilder 接管 | 少量（接口适配） |
| decision_tree.py | 不变，继续用 | 无 |
| tools.py | 不变，继续用 | 无 |
| output_formatter.py | 新增 note/board 输出类型 | 少量 |
| memory.py SQLiteProfileStore | 过渡期双写，稳定后移除 | 标记为 deprecated |
| memory.py SQLiteMemoryStore | 长期记忆继续用 | 无 |
| 前端 App.jsx | 新增视图切换逻辑 | 中等 |
| 前端 ProfilePage.jsx | 增强为 UCF 展示/编辑 | 中等 |

### 新增模块

| 新模块 | 职责 | 预估行数 |
|--------|------|---------|
| user_context.py | UCF 数据模型 | ~400行 |
| ucf_store.py | UCF 持久化存储 | ~250行 |
| extraction_engine.py | 信息提取引擎 | ~300行 |
| proactive_engine.py | 主动智能引擎 | ~250行 |
| prompt_builder.py | System Prompt 构建器 | ~300行 |
| llm_router.py | 多模型路由 | ~100行 |
| routes/notes.py | 笔记 API | ~80行 |
| routes/board.py | 看板 API | ~120行 |
| NoteView.jsx | 笔记前端视图 | ~200行 |
| BoardView.jsx | 看板前端视图 | ~300行 |
| **总计** | | **~2300行** |

---

## 十三、度量标准

### 用户可感知的指标

| 指标 | 含义 | 目标 |
|------|------|------|
| UCF 字段填充率 | 智能体对用户的了解程度 | 5轮对话后 ≥40% |
| 个性化回答率 | 回答中引用用户信息的比例 | ≥70% |
| 提醒有用率 | 用户未忽略/点击的提醒比例 | ≥50% |
| 笔记转化率 | 笔记被后续对话引用的比例 | ≥30% |
| 回访率 | 7日内再次使用 | ≥30% |
| 推荐率 | 用户主动推荐 | 有即可（质的突破） |

### 技术健康指标

| 指标 | 含义 | 目标 |
|------|------|------|
| 对话首token延迟 | 用户等待时间 | <3秒 |
| 提取延迟 | 后台提取不影响体验 | <2秒 |
| UCF 读写延迟 | 数据层性能 | <50ms |
| LLM 调用成本/对话 | 成本控制 | <0.05元 |
| 提取准确率 | 结构化信息的准确性 | ≥85% |

---

> 这份架构不是终态，而是演进的起点。
> 它的核心判断是：**UCF 是心脏，提取是血管，主动性是灵魂**。
> 只要这三件事做对了，产品就会越用越懂用户，用户就会越来越离不开它。
> 而这，正是"智能体替代软件"这件事的本质。

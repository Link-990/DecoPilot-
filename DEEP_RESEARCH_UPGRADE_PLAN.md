# DecoPilot 产品升级计划

> 不是"如何做一个深度研究智能体"，而是"如何做一个真正帮到人的家居行业智能体"

---

## 一、我们到底在解决什么问题？

装修是绝大多数普通人一生中最大的非金融消费决策。一套100平的房子，装修预算15-30万，涉及50+品类、100+决策点、3-6个月工期。

但这个行业有一个根本性的结构问题：**信息不对称**。

### 业主（C端）的真实困境

不是"不知道选什么瓷砖"——而是**不知道自己不知道什么**。

| 阶段 | 表面问题 | 深层痛苦 |
|------|---------|---------|
| 准备期 | "预算多少合理？" | 完全没有参照系，怕被忽悠，又怕花冤枉钱 |
| 设计期 | "这个方案好不好？" | 看不懂图纸，无法判断设计师是否专业 |
| 选材期 | "瓷砖选哪个牌子？" | 品牌太多，参数看不懂，导购说的都是好话 |
| 施工期 | "这个空鼓正常吗？" | 不懂工艺标准，被工人糊弄了也不知道 |
| 验收期 | "这个报价合理吗？" | 没有市场价参考，不敢砍价又怕被宰 |

核心痛苦是三个字：**不确定**。

每一个决策都伴随着焦虑：选错了怎么办？被坑了怎么办？花多了怎么办？而且装修不像买手机，错了可以换——装修错了，代价是几万块和几个月的返工。

### 商家（B端）的真实困境

不是"怎么获客"——而是**怎么在信任缺失的市场里高效成交**。

| 阶段 | 表面问题 | 深层痛苦 |
|------|---------|---------|
| 入驻期 | "平台费用多少？" | 不确定投入能否回本，怕又是一个烧钱渠道 |
| 获客期 | "转化率怎么提升？" | 客户被多家骚扰，信任度极低，话术不管用 |
| 成交期 | "客户比完价就走了" | 价格战内卷，不知道输在哪里 |
| 经营期 | "ROI到底怎么样？" | 数据看不懂，不知道该优化什么 |

核心痛苦也是三个字：**不确定**。

### 洞居平台的独特位置

语料/1.txt 里有一句话点明了本质：

> "C端是智能体数据资源流量入口，B端是智能体用户付费端"

这意味着：
- C端用户越信任平台 → 越愿意留下真实需求数据
- 真实需求数据越多 → B端商家越愿意付费购买
- B端付费越多 → 平台越有资源服务C端
- **这是一个飞轮，而智能体是这个飞轮的加速器**

所以我们的智能体不是一个"功能"，它是平台商业模式的核心引擎。

---

## 二、什么样的智能体才真正有价值？

### 不是"深度研究"，是"决策伙伴"

美团龙猫的"深度研究"是通用搜索场景——用户问一个开放问题，AI 去全网搜索、整合、生成报告。

但装修场景完全不同：
- 用户不需要一份20页的报告，他们需要**一个能帮他们做决定的人**
- 用户不需要"全面的信息"，他们需要**针对自己情况的具体建议**
- 用户不需要一次性的研究，他们需要**贯穿3-6个月装修全程的持续陪伴**

所以我们要做的不是 Deep Research Agent，而是 **Decision Partner Agent**——一个懂装修、记得住你家情况、能帮你在每个关键节点做出正确决策的伙伴。

### 价值公式

```
智能体价值 = 减少的决策焦虑 × 避免的经济损失 × 节省的时间精力
```

具体来说：
1. **减少决策焦虑**：不是给你100个选择，而是基于你的情况给你3个，并告诉你为什么
2. **避免经济损失**：报价是否合理？材料是否兼容？工艺是否达标？——帮你避坑
3. **节省时间精力**：不用自己去小红书、知乎、建材市场跑断腿，一个对话搞定

---

## 三、产品能力分层：从"能用"到"离不开"

### 第一层：可信赖的专业顾问（现有能力的深化）

**核心命题：让用户觉得"这个AI比我认识的任何人都懂装修"**

现状评估：
- ✅ 阶段感知专家系统已实现（5个C端角色 + 4个B端角色）
- ✅ 9个计算工具已实现（补贴/ROI/预算/材料/报价验证等）
- ✅ 知识图谱框架已搭建（50+ EntityType）
- ❌ 知识库数据量不足（ChromaDB 内容稀疏）
- ❌ 推理链未真正指导LLM生成（reasoning是装饰性的）
- ❌ 工具结果未深度融入回答（计算了但没用好）
- ❌ 用户画像未深度个性化回答（记了但没用）

**这一层不需要新架构，需要把现有架构用到极致。**

### 第二层：主动式决策支持（核心创新）

**核心命题：不等用户问，主动在关键节点提供决策支持**

这是和通用AI助手的本质区别。ChatGPT/DeepSeek 是被动的——你问什么它答什么。但装修场景中，用户最大的问题恰恰是**不知道该问什么**。

举例：
- 用户说"我家120平，准备装修"→ 普通AI回答装修流程
- 决策伙伴应该说："120平的话，建议先确认三件事：①预算上限（建议留15%机动）②是否有地暖需求（影响地板选择）③家里有没有老人小孩（影响安全标准）。您先告诉我这三个，我帮您做个初步规划。"

这不是"更聪明的回答"，这是**主动引导用户走正确的决策路径**。

### 第三层：深度研究报告（高价值场景）

**核心命题：在用户面临重大决策时，提供一份有数据支撑的专业报告**

这才是"深度研究"该出现的地方——不是每次对话都生成报告，而是在用户真正需要的时候：
- "我在A品牌和B品牌的瓷砖之间纠结" → 生成对比报告
- "全屋装修预算30万够不够" → 生成预算规划报告
- "施工队给的报价合理吗" → 生成报价审核报告

---

## 四、具体升级路径

### Phase 1：让现有能力真正发挥作用（第1-6周）

> 不写新代码，先让已有的代码真正work

这是最重要的一个阶段，也是之前所有计划都忽略的。DecoPilot 已经有 23000 行代码，架构完善，但很多能力是"搭好了架子没装内容"。

#### 1.1 知识库填充——智能体的"专业底气"（第1-3周）

现有 5 个 ChromaDB Collection 框架完好，但数据稀疏。没有数据的知识库就像没有书的图书馆。

**填充策略：不追求量，追求"能回答用户最常问的50个问题"**

| Collection | 当前状态 | 目标内容 | 数据来源 | 条数 |
|-----------|---------|---------|---------|------|
| decoration_general | 有少量 | 装修全流程知识（工序、工期、验收标准） | 行业规范+装修指南整理 | ≥60条 |
| smart_home | 有少量 | 智能家居选购指南（品类、品牌、兼容性） | 产品评测整理 | ≥30条 |
| dongju_c_end | 有少量 | 洞居C端完整使用指南（补贴规则、逛店流程） | 语料/1.txt C端部分结构化 | ≥40条 |
| dongju_b_end | 有少量 | 洞居B端完整运营指南（入驻、获客、结算） | 语料/1.txt B端部分结构化 | ≥40条 |
| merchant_info | 有少量 | 商家信息模板（品类、评价、服务范围） | 模拟数据+真实商家信息 | ≥30条 |

**关键原则：每条数据都要能直接回答一个真实用户问题。**

不是"瓷砖的分类有釉面砖、抛光砖..."这种百科式内容，而是"卫生间选瓷砖，防滑等级至少R9，推荐哑光面或拉槽面，300×300规格最常用，预算参考60-120元/片"这种能直接指导决策的内容。

实现方式：编写 `scripts/seed_knowledge.py`，从语料文件和整理好的知识文档批量导入。

#### 1.2 让推理链真正指导LLM——从"装饰性思考"到"真思考"（第2-4周）

当前问题：`reasoning.py` 有 1179 行代码，定义了 6 种推理类型（CoT/ToT/ReAct/MultiStep/Reflection/Direct），但这些推理链只是被记录在日志里，**并没有注入到 LLM 的 prompt 中**。

这意味着 LLM 实际上是在"裸奔"——没有被引导按照特定的思考框架来回答。

**修复方案：在 `enhanced_agent.py` 的 `_build_prompt_parts()` 中，将推理框架注入 system prompt**

```python
# enhanced_agent.py _build_prompt_parts() 修改
# 现有代码只返回 (system_prompt, supplementary_context)
# 修改为：将阶段思考框架注入 system_prompt

def _build_prompt_parts(self, context: dict) -> tuple:
    base_prompt = self._get_system_prompt()
    
    # 注入阶段思考框架（来自 stage_reasoning.py 已有的 THINKING_FRAMEWORKS）
    stage = context.get("stage_context", {})
    if stage:
        thinking_framework = stage.get("thinking_framework", "")
        if thinking_framework:
            base_prompt += f"\n\n## 思考框架\n{thinking_framework}"
    
    # 注入用户画像摘要（让LLM知道用户的情况）
    profile_summary = context.get("profile_summary", "")
    if profile_summary:
        base_prompt += f"\n\n## 用户情况\n{profile_summary}"
    
    return (base_prompt, context.get("supplementary", ""))
```

这不是重写，是在现有方法中加 ~20 行代码，但效果是质的飞跃——LLM 会真正按照"工程监理"的思维方式来回答施工问题，而不是泛泛而谈。

#### 1.3 让用户画像真正个性化回答（第3-5周）

当前问题：`memory.py` 的 UserProfile 记录了 budget_range、preferred_styles、house_area、decoration_stage、pain_points 等丰富信息，但在生成回答时几乎没有使用。

**修复方案：在 `_prepare_context()` 中生成用户画像摘要，注入到 prompt**

```python
# enhanced_agent.py _prepare_context() 中新增
def _build_profile_summary(self, profile) -> str:
    parts = []
    if profile.house_area:
        parts.append(f"房屋面积：{profile.house_area}平米")
    if profile.budget_range:
        parts.append(f"预算范围：{profile.budget_range[0]}-{profile.budget_range[1]}元")
    if profile.preferred_styles:
        parts.append(f"偏好风格：{'、'.join(profile.preferred_styles)}")
    if profile.decoration_stage:
        parts.append(f"当前阶段：{profile.decoration_stage}")
    if profile.pain_points:
        top_pains = sorted(profile.pain_points, key=lambda x: x.get('severity',0), reverse=True)[:3]
        parts.append(f"主要关注：{'、'.join(p['description'] for p in top_pains)}")
    
    # 家庭成员情况（影响安全标准推荐）
    family = profile.extra_info.get("family_members", {})
    if family.get("has_elderly"): parts.append("家有老人（注意无障碍和防滑）")
    if family.get("has_children"): parts.append("家有小孩（注意环保和安全）")
    
    return "\n".join(parts) if parts else "（新用户，尚未了解详细情况）"
```

效果：同样问"瓷砖怎么选"，
- 新用户 → 先问基本情况，给通用建议
- 已知120平/20万预算/现代简约/有小孩 → 直接推荐环保等级高、防滑性好、适合现代简约的瓷砖，并计算用量和预算占比

#### 1.4 让工具结果融入回答（第4-6周）

当前问题：`tools.py` 的 9 个工具都能正确计算，但计算结果只是作为结构化数据输出，没有被 LLM 用来生成更有说服力的回答。

**修复方案：将工具结果作为 context 注入 LLM prompt**

```python
# enhanced_agent.py _check_and_call_tools() 之后
# 现有代码：工具结果通过 OutputFormatter 直接输出给前端
# 新增：同时将工具结果摘要注入到 LLM 的 supplementary_context

tool_context = ""
for result in tool_results:
    if result.success:
        tool_context += f"\n【{result.tool_name}计算结果】\n{json.dumps(result.data, ensure_ascii=False)[:500]}\n"

# 在 _generate_response() 调用时传入
context["tool_context"] = tool_context
```

效果：用户问"30万预算够不够装120平"，
- 之前：LLM 泛泛回答"一般来说够的"，同时前端显示一个预算分配卡片
- 之后：LLM 说"根据计算，120平现代简约风格30万预算分配如下：硬装18万（60%）、软装7.5万（25%）、家电3万（10%）、机动1.5万（5%）。其中硬装部分，水电改造约2.4万、瓦工约3.6万...这个预算是够的，但建议在橱柜和卫浴上不要省，这两项直接影响日常使用体验。"

**Phase 1 不新增任何文件，只修改 3 个现有文件约 100 行代码 + 填充知识库数据。但这 100 行代码会让智能体的回答质量产生质变。**

---

### Phase 2：主动式决策引导（第5-10周）

> 从"你问我答"升级为"我引导你做对的决定"

这是 DecoPilot 和通用 AI 助手拉开差距的关键阶段。

#### 2.1 决策树引擎——装修不是一个问题，是一棵决策树

装修的本质是一系列有依赖关系的决策。选地板之前要先确定是否有地暖，选瓷砖之前要先确定空间用途，做预算之前要先确定风格和面积。

但用户不知道这个决策顺序。他们可能上来就问"瓷砖选什么牌子"，而实际上他们还没确定卫生间的防水方案。

**核心设计：为每个装修阶段建立决策树，智能体根据用户已知信息，自动判断下一个该问的问题。**

```python
# backend/core/decision_tree.py（新增，~200行）

DECISION_TREES = {
    "选材_瓷砖": {
        "root": "space_usage",
        "nodes": {
            "space_usage": {
                "question": "瓷砖用在哪个空间？",
                "options": ["客厅", "卫生间", "厨房", "阳台", "卧室"],
                "affects": ["防滑等级", "吸水率", "规格推荐"],
                "next": {"卫生间": "has_floor_heating", "厨房": "wall_or_floor", "_default": "budget_level"}
            },
            "has_floor_heating": {
                "question": "是否有地暖？",
                "options": ["有", "没有", "不确定"],
                "affects": ["材质推荐", "厚度限制"],
                "next": {"_all": "budget_level"}
            },
            "budget_level": {
                "question": "这个空间的瓷砖预算大概多少？",
                "options": ["经济型(30-80元/片)", "中档(80-200元/片)", "高端(200元以上)"],
                "affects": ["品牌推荐", "产品推荐"],
                "next": {"_all": "style_preference"}
            },
            "style_preference": {
                "question": "偏好什么风格？",
                "options": ["现代简约", "奶油风", "侘寂风", "中式", "不确定"],
                "affects": ["花色推荐", "铺贴方式"],
                "next": {"_all": "COMPLETE"}
            },
        }
    },
    "选材_地板": { ... },
    "全屋_预算规划": { ... },
    "施工_验收": { ... },
}

class DecisionTreeEngine:
    def get_next_question(self, tree_id: str, known_answers: dict) -> dict:
        """根据已知答案，返回下一个需要确认的问题"""
        tree = DECISION_TREES.get(tree_id)
        if not tree: return None
        
        current = tree["root"]
        while current != "COMPLETE":
            node = tree["nodes"][current]
            if current in known_answers:
                answer = known_answers[current]
                next_map = node["next"]
                current = next_map.get(answer, next_map.get("_default", next_map.get("_all", "COMPLETE")))
            else:
                return {
                    "node_id": current,
                    "question": node["question"],
                    "options": node["options"],
                    "why": f"这会影响：{'、'.join(node['affects'])}",
                }
        return None  # 所有信息已收集完毕
    
    def get_recommendation_context(self, tree_id: str, answers: dict) -> str:
        """将收集到的答案转化为推荐上下文"""
        ...
```

**与现有系统的集成点：**
- `StageAwareReasoning` 检测到用户处于"选材"阶段 → 激活对应决策树
- `UserProfile` 中已有的信息自动填充 known_answers（不重复问）
- 决策树的 `options` 通过 `OutputFormatter.quick_replies()` 渲染为前端快捷按钮

#### 2.2 主动提醒系统——在用户忘记之前提醒他

装修周期 3-6 个月，用户不可能每天都想着装修的事。但有些事情有时间窗口——错过了就要多花钱或返工。

```python
# backend/core/proactive_reminders.py（新增，~150行）

STAGE_REMINDERS = {
    "准备": [
        {"trigger": "budget_set", "delay_days": 0,
         "message": "预算定好了，建议先去建材市场逛一圈，感受一下实际价格。周末去人多但能看到更多促销。",
         "priority": "high"},
    ],
    "设计": [
        {"trigger": "design_confirmed", "delay_days": 0,
         "message": "设计方案确认后，有三样东西要提前订：①橱柜（定制周期25-35天）②室内门（定制周期20-30天）③窗户（如需更换，周期15-20天）。现在就可以开始看了。",
         "priority": "critical"},
    ],
    "施工": [
        {"trigger": "stage_enter", "delay_days": 0,
         "message": "施工开始前，请确认：①物业已报备 ②邻居已告知 ③水电走向已拍照存档。这三件事很多人忘记，后面会很麻烦。",
         "priority": "high"},
        {"trigger": "waterproof_done", "delay_days": 0,
         "message": "防水做完了吗？一定要做48小时闭水试验！这是最容易偷工减料的环节，漏水了楼下找你赔。",
         "priority": "critical"},
    ],
    "软装": [
        {"trigger": "stage_enter", "delay_days": 0,
         "message": "软装阶段建议顺序：先定大件家具（沙发、床、餐桌）→ 再选窗帘灯具 → 最后配饰品。大件决定了空间基调。",
         "priority": "medium"},
    ],
    "入住": [
        {"trigger": "stage_enter", "delay_days": 0,
         "message": "入住前三件事：①开窗通风至少3个月（夏天效果最好）②找专业机构做甲醛检测（别用网上买的试纸，不准）③保留所有保修卡和工人联系方式",
         "priority": "critical"},
    ],
}

class ProactiveReminderEngine:
    def get_reminders(self, profile, current_stage: str, last_visit_days: int) -> list:
        """根据用户状态返回应该推送的提醒"""
        reminders = []
        stage_reminders = STAGE_REMINDERS.get(current_stage, [])
        
        for r in stage_reminders:
            # 检查是否已经提醒过
            if not profile.has_seen_reminder(r["trigger"]):
                reminders.append(r)
        
        # 长时间未访问的回访提醒
        if last_visit_days > 7:
            reminders.append({
                "message": f"好久没见您了！您的装修进展到哪一步了？有什么需要帮忙的随时问我。",
                "priority": "low"
            })
        
        return reminders
```

**与现有系统的集成点：**
- `MemoryManager` 的 `UserProfile.decoration_stage` 触发阶段提醒
- `StageTransitionDetector` 检测到阶段变化时，推送转换提醒
- 前端通过现有的 `quick_replies` 组件渲染提醒内容

#### 2.3 避坑预警——在用户犯错之前拦住他

这是最能建立信任的功能。当用户描述的情况触发了已知的"坑"，智能体主动预警。

```python
# 集成在 enhanced_agent.py 的 process() 流程中
# 在 _generate_response() 之前，检查用户输入是否触发避坑规则

PITFALL_PATTERNS = [
    {"pattern": r"(全包|大包).*(装修公司|施工队)",
     "warning": "全包模式要特别注意：①确认主材品牌和型号写进合同 ②确认增项上限（建议不超过总价10%）③确认付款节点（建议3-4-2-1分期）。很多纠纷都出在全包合同不清晰。"},
    {"pattern": r"(熟人|朋友|亲戚).*(装修|施工)",
     "warning": "熟人装修要注意：①一样要签正式合同 ②一样要明确验收标准 ③出了问题更难开口。建议把'人情'和'生意'分开，合同该签还是要签。"},
    {"pattern": r"(最便宜|最低价|省钱).*(瓷砖|地板|涂料|防水)",
     "warning": "有些地方可以省，有些地方真不能省。防水、水电、五金件这三样，用差的后期维修成本是当初省下的10倍。建议在这三项上选中档以上。"},
    {"pattern": r"(不做|不需要|省掉).*(防水|闭水)",
     "warning": "⚠️ 强烈建议不要省防水！卫生间、厨房、阳台都必须做防水，墙面至少1.8米高。漏水不仅自己遭殃，楼下邻居找你赔偿更麻烦。"},
]
```

这些规则不需要 LLM，纯正则匹配就够了。但它们传递的信息是：**这个AI真的在替我着想，不是在敷衍我**。

#### Phase 2 交付物

| 新增文件 | 行数 | 作用 |
|---------|------|------|
| backend/core/decision_tree.py | ~200行 | 决策树引擎 + 8大品类决策树数据 |
| backend/core/proactive_reminders.py | ~150行 | 主动提醒引擎 + 5阶段提醒数据 |
| enhanced_agent.py 修改 | ~50行 | 集成决策树 + 避坑预警 |


---

### Phase 3：深度研究报告——在关键决策时刻提供重火力（第9-14周）

> 不是每次对话都生成报告，而是在用户真正需要的时候

前两个 Phase 让智能体成为一个可信赖的日常顾问。Phase 3 在此基础上，为用户面临重大决策时提供"深度研究"能力。

#### 3.1 什么时候触发深度研究？

不是用户点一个按钮，而是智能体判断"这个问题值得做深度研究"：

```python
# backend/agents/deep_research_agent.py

DEEP_RESEARCH_TRIGGERS = [
    # 选材对比：涉及具体品牌/产品对比
    {"pattern": r"(对比|比较|选哪个|哪个好).*(品牌|产品|型号)",
     "type": "product_comparison", "scope": "单品类选材对比"},
    # 预算规划：涉及整体预算分配
    {"pattern": r"(预算|花多少|够不够).*(装修|全屋|整体)",
     "type": "budget_planning", "scope": "全屋装修规划"},
    # 报价审核：用户拿到了报价单
    {"pattern": r"(报价|报价单|价格).*(合理|贵不贵|正常)",
     "type": "quote_review", "scope": "报价审核"},
    # 方案评估：用户拿到了设计方案
    {"pattern": r"(方案|设计图|效果图).*(怎么样|好不好|评价)",
     "type": "design_review", "scope": "方案评估"},
]
```

当触发时，智能体不是直接开始生成报告，而是先问用户：

> "这个问题我可以帮您做一份详细的对比分析报告，大概需要1-2分钟。需要我深入研究一下吗？"

用户确认后才启动。这个交互设计很重要——它让用户感觉到"这个AI在认真对待我的问题"，而不是机械地生成内容。

#### 3.2 DeepResearchAgent——继承 EnhancedAgent

```python
# backend/agents/deep_research_agent.py（新增，~400行）

class DeepResearchAgent(EnhancedAgent):
    """
    继承 EnhancedAgent 的全部能力，新增深度研究流水线。
    不是替代日常对话，而是在关键决策时刻提供深度支持。
    """
    
    async def run_research(self, query, session_id, user_id, research_type) -> AsyncGenerator:
        fmt = OutputFormatter(session_id, self.user_type)
        ctx = ResearchContext(raw_query=query, session_id=session_id, user_id=user_id)
        
        yield fmt.stream_start()
        
        # 1. 需求理解（复用 StageAwareReasoning + UserProfile）
        yield self._progress("clarify", "正在理解您的具体需求...")
        ctx.requirements = await self._clarify(ctx)
        
        if not ctx.requirements.get("is_complete"):
            yield self._clarification_needed(ctx.requirements.get("questions", []))
            yield fmt.stream_end()
            return
        
        # 2. 信息收集（复用 MultiCollectionKB + KnowledgeGraph + 工具）
        yield self._progress("search", "正在收集产品信息、用户评价、市场价格...")
        ctx.search_results = await self._search(ctx)
        
        # 3. 专业分析（兼容性检查 + 工具计算 + LLM分析）
        yield self._progress("analyze", "正在进行专业分析...")
        ctx.analysis = await self._analyze(ctx)
        
        # 4. 报告生成（大纲→逐章节→总结）
        yield self._progress("report", "正在撰写研究报告...")
        async for event in self._generate_report(ctx):
            yield event
        
        yield fmt.stream_end()
```

核心方法的实现思路与 v3 计划一致（_clarify 复用 StageAwareReasoning，_search 复用 MultiCollectionKB + 工具，_report 用大纲→逐章节递归生成），但有一个关键区别：

**报告不是独立的，它是对话的一部分。**

生成完报告后，用户可以继续在对话中追问报告的任何部分，智能体记得报告内容，可以深入解释。这比生成一个静态PDF有价值得多。

#### 3.3 四种报告模板

不同的决策场景需要不同的报告结构：

```python
REPORT_TEMPLATES = {
    "product_comparison": {
        "title_format": "{category}选购深度对比",
        "chapters": [
            {"title": "省流版结论", "type": "summary"},
            {"title": "产品参数对比", "type": "comparison_table",
             "columns": ["品名", "规格", "核心参数", "价格区间", "适用场景", "评分"]},
            {"title": "用户真实评价", "type": "reviews"},
            {"title": "您家的具体推荐", "type": "personalized",
             "note": "基于用户的面积、预算、风格、家庭成员情况给出个性化推荐"},
            {"title": "用量与预算计算", "type": "calculation"},
            {"title": "选购避坑提醒", "type": "pitfalls"},
            {"title": "采购建议", "type": "action_items"},
        ]
    },
    "budget_planning": {
        "title_format": "{area}平米{style}风格装修预算规划",
        "chapters": [
            {"title": "预算总览", "type": "summary"},
            {"title": "分项预算明细", "type": "budget_breakdown"},
            {"title": "省钱 vs 不能省的地方", "type": "priority_analysis"},
            {"title": "施工排期与采购时间线", "type": "timeline"},
            {"title": "风险预留建议", "type": "risk_buffer"},
        ]
    },
    "quote_review": {
        "title_format": "装修报价审核报告",
        "chapters": [
            {"title": "报价总评", "type": "summary"},
            {"title": "逐项价格合理性分析", "type": "price_check"},
            {"title": "常见增项预警", "type": "hidden_costs"},
            {"title": "建议砍价点", "type": "negotiation_tips"},
        ]
    },
    "design_review": {
        "title_format": "设计方案评估报告",
        "chapters": [
            {"title": "方案总评", "type": "summary"},
            {"title": "动线分析", "type": "flow_analysis"},
            {"title": "收纳空间评估", "type": "storage_check"},
            {"title": "潜在问题提醒", "type": "issues"},
        ]
    },
}
```

每种模板都是从真实用户需求出发设计的，不是为了"看起来专业"，而是为了**真正帮用户做决定**。

#### 3.4 前端报告渲染

在现有 App.jsx 中内联实现（不拆分组件），复用已有的 ReactMarkdown + StructuredData 组件：

- 进度条：5阶段步骤条（理解需求→收集信息→专业分析→撰写报告→完成）
- 报告页面：左侧内容 + 右侧目录导航
- 导出：Markdown 文件下载
- 追问：报告生成后可继续对话追问

前端新增约 200 行代码（内联在 App.jsx），复用现有的 markdownComponents 和 StructuredData 组件。

#### Phase 3 交付物

| 新增/修改 | 行数 | 作用 |
|---------|------|------|
| backend/agents/deep_research_agent.py | ~400行 | 深度研究Agent（继承EnhancedAgent） |
| backend/api/routes/deep_research.py | ~50行 | API路由 |
| App.jsx 新增 | ~200行 | 报告渲染 + 进度条 + 导出 |
| config_data.py 修改 | ~10行 | 新增3个Collection |
| scripts/seed_knowledge.py 扩展 | ~100行 | 品类数据填充 |


---

### Phase 4：B端价值闭环——让商家愿意付费（第13-18周）

> C端体验做好了，B端才有付费意愿

前三个 Phase 聚焦 C 端体验。但洞居的商业模式是 B 端付费，所以 Phase 4 要回答一个关键问题：**智能体能帮商家赚到钱吗？**

#### 4.1 商家视角的智能体价值

商家不关心"AI多聪明"，他们关心三件事：
1. **能不能帮我多成交？**（获客效率）
2. **能不能帮我少花冤枉钱？**（投入产出比）
3. **能不能帮我省时间？**（运营效率）

现有 B 端 Agent（b_end_agent.py）已经有 ROI 分析、话术生成、佣金计算等能力，但缺少一个关键环节：**将 C 端用户的真实需求数据转化为商家可用的洞察**。

#### 4.2 需求洞察报告——C端数据的B端价值

这是洞居平台的核心竞争力。C端用户在和智能体对话的过程中，自然地留下了大量真实需求数据：
- 装修阶段、预算范围、风格偏好
- 关注的品类、纠结的品牌
- 痛点和顾虑

这些数据经过脱敏和聚合后，对商家极有价值。

```python
# backend/core/demand_insights.py（新增，~200行）

class DemandInsightEngine:
    """将C端用户画像数据聚合为B端商家可用的市场洞察"""
    
    def generate_category_insight(self, category: str, city: str = None) -> dict:
        """生成品类需求洞察"""
        # 从 MemoryManager 聚合匿名用户画像数据
        profiles = self.memory.get_aggregated_profiles(
            filters={"interests": category, "city": city},
            anonymize=True  # 脱敏
        )
        
        return {
            "category": category,
            "demand_volume": len(profiles),
            "budget_distribution": self._calc_budget_distribution(profiles),
            "style_preferences": self._calc_style_distribution(profiles),
            "common_pain_points": self._extract_common_pains(profiles),
            "peak_inquiry_stages": self._calc_stage_distribution(profiles),
            "decision_factors": self._extract_decision_factors(profiles),
            # 对商家最有价值的信息：
            "actionable_insights": [
                f"该品类{len(profiles)}位潜在客户中，{budget_pct}%预算在{range}区间",
                f"最关注的问题是：{top_pain}",
                f"最常对比的品牌是：{top_brands}",
                f"{stage_pct}%的客户处于{stage}阶段，是最佳触达时机",
            ]
        }
```

#### 4.3 B端智能体增强

在现有 `b_end_agent.py` 的基础上，增强三个核心场景：

**场景一：智能获客建议**

不是泛泛的"提高转化率"建议，而是基于真实数据的具体策略：

```
商家问："最近转化率下降了，怎么办？"

之前的回答：
"建议优化话术，提高响应速度，做好客户分层..."（正确但无用的废话）

增强后的回答：
"根据平台数据，您所在品类（全屋定制）近30天的情况：
- 咨询量上升15%，但成交率下降8%，说明不是流量问题，是转化问题
- 同品类TOP商家的平均首次响应时间是3分钟，您的是12分钟——这可能是主因
- 当前咨询客户中，62%处于设计阶段，他们最关心的是'方案效果'和'价格透明度'
建议：①把首次响应压到5分钟内 ②首次沟通时主动发送3个同户型案例 ③报价时附上材料清单明细"
```

**场景二：竞争分析**

```
商家问："我的定价是不是太高了？"

增强后的回答：
"您的客单价8.5万，同品类平台均价7.2万，确实偏高18%。
但您的好评率92%高于均值85%，复购推荐率也高。
建议不降价，而是：①在报价时突出'用料明细'增加透明度 ②提供'同品质竞品对比表'让客户自己算账 ③增加售后保障条款降低客户决策风险"
```

**场景三：经营诊断**

复用现有的 `roi_calculator` 和 `conversion_rate_analyzer` 工具，但将结果转化为可执行的建议，而不是冷冰冰的数字。

#### 4.4 C端-B端数据飞轮

```
C端用户对话 → 需求数据沉淀（UserProfile）
    ↓
需求数据聚合 → 品类洞察报告（DemandInsightEngine）
    ↓
商家获取洞察 → 精准服务C端用户
    ↓
C端获得更好服务 → 更信任平台 → 留下更多数据
    ↓
（飞轮加速）
```

这个飞轮是洞居平台的护城河。通用AI助手（ChatGPT/DeepSeek）永远做不到这一点，因为它们没有平台的交易数据和用户画像数据。

#### Phase 4 交付物

| 新增/修改 | 行数 | 作用 |
|---------|------|------|
| backend/core/demand_insights.py | ~200行 | 需求洞察聚合引擎 |
| backend/agents/b_end_agent.py 增强 | ~100行 | 数据驱动的获客/竞争/诊断建议 |
| backend/core/memory.py 增强 | ~50行 | 聚合查询接口（脱敏） |

---

## 五、不做什么（同样重要）

| 不做的事 | 为什么不做 |
|---------|----------|
| 虚拟逛店/AR | 技术门槛极高，不是智能体的核心价值 |
| OCR票据识别 | 需要大量标注数据，当前阶段ROI低 |
| 语音交互 | Web Speech API兼容性差，文字交互已够用 |
| 多语言 | 只面向中文用户 |
| PWA离线 | 装修咨询需要实时数据，离线无意义 |
| 对话分支/版本树 | 复杂度极高，用户不需要 |
| 自动下单/支付 | 涉及资金安全，不在智能体范围内 |
| 替代设计师出图 | AI出图质量不稳定，且不是平台定位 |

**核心原则：只做"帮用户做更好的决策"这一件事，做到极致。**

---

## 六、成功指标——怎么知道我们做对了？

### 不用技术指标，用用户行为指标

| 指标 | 含义 | 目标 |
|------|------|------|
| 对话轮次/会话 | 用户愿意和AI深入交流 | ≥8轮（当前估计3-5轮） |
| 回访率 | 用户觉得有用，会回来 | 7日回访率 ≥ 30% |
| 主动提问率 | 用户开始主动问更深的问题 | ≥ 40%的会话有追问 |
| 工具触发率 | 用户的问题触发了计算工具 | ≥ 20%的会话 |
| 深度研究完成率 | 用户愿意等待报告生成 | ≥ 70%（触发后不中断） |
| 报告导出率 | 用户觉得报告值得保存 | ≥ 30% |
| "有用"反馈率 | 用户主动点赞 | ≥ 50% |

### B端指标

| 指标 | 含义 | 目标 |
|------|------|------|
| 商家咨询频次 | 商家觉得AI顾问有用 | ≥ 3次/周 |
| 洞察报告查看率 | 商家关注市场数据 | ≥ 60% |
| 建议采纳率 | 商家按建议调整策略 | ≥ 30% |

---

## 七、实施总览

```
Phase 1（第1-6周）：让现有能力真正发挥作用
  ├── 知识库填充（≥200条决策导向内容）
  ├── 推理链注入LLM prompt（~20行修改）
  ├── 用户画像个性化回答（~30行修改）
  └── 工具结果融入回答（~50行修改）
  → 修改3个文件，新增1个脚本，~100行代码改动

Phase 2（第5-10周）：主动式决策引导
  ├── 决策树引擎（8大品类决策树）
  ├── 主动提醒系统（5阶段提醒）
  └── 避坑预警（正则规则库）
  → 新增2个文件，修改1个文件，~400行新代码

Phase 3（第9-14周）：深度研究报告
  ├── DeepResearchAgent（继承EnhancedAgent）
  ├── 4种报告模板
  ├── 前端报告渲染
  └── 品类数据扩充
  → 新增2个文件，修改2个文件，~750行新代码

Phase 4（第13-18周）：B端价值闭环
  ├── 需求洞察聚合引擎
  ├── B端Agent增强
  └── C-B数据飞轮
  → 新增1个文件，修改2个文件，~350行新代码

总新增代码：~1600行
总修改代码：~200行（在现有23000行基础上）
```

---

## 八、为什么这个计划和之前不同？

之前的计划（v1/v2/v3）都是从技术出发：
- "龙猫有深度研究，我们也要做深度研究"
- "需要一个5阶段流水线"
- "需要兼容性规则引擎"

这个计划从人出发：
- **业主的核心痛苦是"不确定"** → 所以我们的核心价值是"帮你确定"
- **业主不知道该问什么** → 所以我们要主动引导，不是被动回答
- **业主需要的是持续陪伴，不是一次性报告** → 所以日常对话质量比深度研究更重要
- **商家需要的是能赚钱的工具** → 所以B端价值要建立在C端数据之上

技术是手段，不是目的。一个能在用户说"我想装修"的时候，主动问出正确问题、给出个性化建议、在关键节点提醒避坑的智能体，比一个能生成20页报告但不了解用户情况的智能体，有价值100倍。

**我们要做的不是最聪明的AI，而是最懂装修的朋友。**

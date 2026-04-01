"""
深度研究报告管道

当用户提出品牌对比、预算规划、报价审核、设计评审等复杂需求时，
通过多轮 LLM 调用生成有结构的深度分析报告。

设计决策：
- 不新建 endpoint，复用 /chat/stream
- 不新建 Agent 子类，在 EnhancedAgent 中作为钩子调用
- 多轮调用（大纲 + 每个章节独立生成），质量优于单轮大调用
- 报告是对话的一部分，生成完可以继续追问
"""

import re
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from dataclasses import dataclass

from backend.core.logging_config import get_logger

logger = get_logger("deep_research")


# === 触发规则 ===

@dataclass
class ResearchTrigger:
    """研究触发规则"""
    pattern: str
    research_type: str
    confirmation_msg: str


RESEARCH_TRIGGERS: List[ResearchTrigger] = [
    ResearchTrigger(
        # 限定为中文字符/英文/数字组成的词，排除标点和空格，减少误触发
        # 如 "客厅和卧室" 这类非产品对比不会被匹配（因为后续有品类白名单二次校验）
        pattern=r"([\u4e00-\u9fa5A-Za-z0-9]{2,10})[和与跟VS]([\u4e00-\u9fa5A-Za-z0-9]{2,10})(哪个好|怎么选|选哪个|对比|比较|区别)",
        research_type="product_comparison",
        confirmation_msg="我可以帮您做一份 **{brand_a} vs {brand_b}** 的详细对比分析报告，从参数、口碑、价格等多个维度深入比较。需要我深入研究一下吗？",
    ),
    ResearchTrigger(
        pattern=r"(\d+)\s*万.*(够不够|能不能|装得了|够装|能装)|预算.*(\d+)\s*万.*(怎么分|怎么花|如何分配|够不够)",
        research_type="budget_planning",
        confirmation_msg="我可以帮您做一份详细的 **预算规划报告**，包括分项明细、省钱策略和采购时间线。需要我深入研究一下吗？",
    ),
    ResearchTrigger(
        pattern=r"报价.*(合理|贵不贵|高不高|怎么样|看看)|帮我.*(看看|审|分析).*报价",
        research_type="quote_review",
        confirmation_msg="我可以帮您做一份 **报价审核报告**，逐项分析价格合理性并给出砍价建议。需要我深入研究一下吗？",
    ),
    ResearchTrigger(
        pattern=r"(方案|设计|布局|动线).*(怎么样|好不好|合理|看看|帮我看|评价)",
        research_type="design_review",
        confirmation_msg="我可以帮您做一份 **设计方案评审报告**，从动线、收纳、实用性等角度深入分析。需要我深入研究一下吗？",
    ),
]


# === 报告模板 ===

@dataclass
class ReportSection:
    """报告章节定义"""
    key: str
    title: str
    prompt_hint: str  # 给 LLM 的章节撰写提示


@dataclass
class ReportTemplate:
    """报告模板"""
    title_format: str
    sections: List[ReportSection]


REPORT_TEMPLATES: Dict[str, ReportTemplate] = {
    "product_comparison": ReportTemplate(
        title_format="{query}——深度对比分析",
        sections=[
            ReportSection("conclusion", "结论先行", "用2-3句话直接给出推荐结论和理由，不要含糊，要有明确立场。"),
            ReportSection("specs", "核心参数对比", "用表格形式对比两款产品的核心参数（材质、规格、环保等级、价格区间、适用场景等）。"),
            ReportSection("reputation", "口碑分析", "从用户真实反馈角度分析两款产品的优缺点，引用常见的好评和差评。"),
            ReportSection("recommendation", "个性化推荐", "根据用户的预算、面积、风格偏好给出针对性推荐，说明为什么这个选择最适合用户。"),
            ReportSection("budget_calc", "用量与预算估算", "根据用户房屋面积估算用量和总花费，给出性价比最优的采购方案。"),
            ReportSection("pitfalls", "避坑指南", "列出购买和施工中的常见坑点，给出具体的验收标准和注意事项。"),
        ],
    ),
    "budget_planning": ReportTemplate(
        title_format="装修预算规划报告",
        sections=[
            ReportSection("overview", "预算总览", "根据用户的总预算和面积，给出整体预算分配建议和每平米造价参考。"),
            ReportSection("breakdown", "分项明细", "用表格形式列出各项费用（设计费、拆改、水电、防水、瓷砖、木工、油漆、安装、家具、家电、软装等），给出每项的预算范围。"),
            ReportSection("save_or_not", "能省 vs 不能省", "明确告诉用户哪些钱可以省（附具体省法），哪些钱绝对不能省（附原因）。"),
            ReportSection("timeline", "采购时间线", "按施工阶段列出材料采购时间节点，避免耽误工期。"),
            ReportSection("risk_reserve", "风险预留", "建议预留的机动资金比例，列出常见的超预算场景和应对策略。"),
        ],
    ),
    "quote_review": ReportTemplate(
        title_format="装修报价审核报告",
        sections=[
            ReportSection("summary", "总评", "对这份报价给出整体评价：偏高/合理/偏低，以及主要问题点。"),
            ReportSection("item_analysis", "逐项价格分析", "用表格对比报价中各项目与市场参考价，标注偏高的项目。"),
            ReportSection("hidden_costs", "增项预警", "分析报价中可能故意遗漏的项目，提醒用户哪些地方后期可能加钱。"),
            ReportSection("negotiation", "砍价建议", "给出具体可操作的砍价策略和话术，标明每项可以砍掉多少。"),
        ],
    ),
    "design_review": ReportTemplate(
        title_format="设计方案评审报告",
        sections=[
            ReportSection("summary", "总评", "对设计方案给出整体评价，打分（1-10），列出主要优点和问题。"),
            ReportSection("circulation", "动线分析", "分析生活动线（起居、家务、访客）是否合理，有没有交叉或浪费。"),
            ReportSection("storage", "收纳评估", "评估各区域的收纳空间是否充足，给出优化建议。"),
            ReportSection("improvements", "问题与改进建议", "列出具体问题和对应的改进方案，按优先级排序。"),
        ],
    ),
}


# === 研究进度步骤 ===

PROGRESS_STEPS = [
    "理解需求",
    "收集信息",
    "专业分析",
    "撰写报告",
    "完成",
]


class DeepResearchPipeline:
    """深度研究管道"""

    def __init__(self, llm, kb=None):
        """
        Args:
            llm: ChatTongyi 实例（复用 Agent 的 LLM）
            kb: MultiCollectionKB 实例（可选，用于检索知识）
        """
        self.llm = llm
        self.kb = kb

    # 非产品/品牌实体——匹配到这些词时不触发产品对比研究
    _NON_PRODUCT_ENTITIES = {
        "客厅", "卧室", "厨房", "卫生间", "阳台", "书房", "玄关", "餐厅",  # 空间
        "全包", "半包", "清包",  # 装修方式
        "我", "你", "他", "她", "我们", "他们",  # 代词
    }

    def detect_trigger(self, message: str) -> Optional[Dict]:
        """
        检测消息是否触发深度研究

        Returns:
            {
                "research_type": str,
                "confirmation_msg": str,
                "original_query": str,
                "match_groups": tuple,
            } 或 None
        """
        for trigger in RESEARCH_TRIGGERS:
            m = re.search(trigger.pattern, message, re.IGNORECASE)
            if m:
                groups = m.groups()

                # 产品对比需要二次校验：排除非产品实体
                if trigger.research_type == "product_comparison" and len(groups) >= 2:
                    entity_a = groups[0].strip()
                    entity_b = groups[1].strip()
                    if entity_a in self._NON_PRODUCT_ENTITIES or entity_b in self._NON_PRODUCT_ENTITIES:
                        continue  # 跳过此触发规则，尝试下一个

                confirmation = trigger.confirmation_msg
                # 替换占位符
                if trigger.research_type == "product_comparison" and len(groups) >= 2:
                    confirmation = confirmation.format(
                        brand_a=groups[0].strip(),
                        brand_b=groups[1].strip(),
                    )
                return {
                    "research_type": trigger.research_type,
                    "confirmation_msg": confirmation,
                    "original_query": message,
                    "match_groups": groups,
                }
        return None

    async def run_research(
        self,
        query: str,
        research_type: str,
        context: Dict,
    ) -> AsyncGenerator[Dict, None]:
        """
        执行研究管道，yield SSE 事件

        每个 yield 的 dict 格式：
        {"event_type": "research_progress|research_report|answer", "data": ...}

        Args:
            query: 用户原始查询
            research_type: 报告类型
            context: Agent 上下文（含 profile、knowledge 等）
        """
        template = REPORT_TEMPLATES.get(research_type)
        if not template:
            yield {"event_type": "answer", "data": f"暂不支持该类型的研究报告。"}
            return

        # Step 1: 理解需求
        yield {"event_type": "research_progress", "data": {"step": 1, "total": len(PROGRESS_STEPS), "label": PROGRESS_STEPS[0]}}

        # 构建用户画像摘要
        profile_summary = self._build_profile_summary(context)

        # Step 2: 收集信息
        yield {"event_type": "research_progress", "data": {"step": 2, "total": len(PROGRESS_STEPS), "label": PROGRESS_STEPS[1]}}

        # 检索相关知识
        knowledge_text = ""
        if self.kb:
            try:
                results = self.kb.search_by_user_type(query=query, user_type="c_end", k=5)
                knowledge_text = "\n".join(
                    doc.page_content[:500] for doc, _ in results
                )
            except Exception as e:
                logger.debug(f"知识检索跳过: {e}")

        # Step 3: 专业分析 — 生成大纲
        yield {"event_type": "research_progress", "data": {"step": 3, "total": len(PROGRESS_STEPS), "label": PROGRESS_STEPS[2]}}

        outline = await self._generate_outline(query, research_type, template, profile_summary, knowledge_text)

        # 发送报告头部（标题+目录）
        report_title = template.title_format.format(query=query)
        section_titles = [s.title for s in template.sections]
        yield {
            "event_type": "research_report",
            "data": {
                "title": report_title,
                "research_type": research_type,
                "sections": section_titles,
            },
        }

        # Step 4: 撰写报告 — 逐章节生成
        yield {"event_type": "research_progress", "data": {"step": 4, "total": len(PROGRESS_STEPS), "label": PROGRESS_STEPS[3]}}

        for section in template.sections:
            section_content = await self._generate_section(
                query, section, outline, profile_summary, knowledge_text
            )
            # 以 answer 事件流式输出章节
            yield {"event_type": "answer", "data": section_content}

        # Step 5: 完成
        yield {"event_type": "research_progress", "data": {"step": 5, "total": len(PROGRESS_STEPS), "label": PROGRESS_STEPS[4]}}

    async def _generate_outline(
        self,
        query: str,
        research_type: str,
        template: ReportTemplate,
        profile_summary: str,
        knowledge_text: str,
    ) -> str:
        """生成报告大纲"""
        sections_desc = "\n".join(
            f"- {s.title}: {s.prompt_hint}" for s in template.sections
        )

        prompt = f"""你是一位资深的装修行业专家。用户问了以下问题：
"{query}"

请为一份"{template.title_format.format(query=query)}"拟一个简要的大纲（每个章节1-2句话概括要点）。

报告章节：
{sections_desc}

{f"用户信息：{profile_summary}" if profile_summary else ""}
{f"参考资料：{knowledge_text[:1000]}" if knowledge_text else ""}

只输出大纲，不要输出完整报告。"""

        try:
            result = await self.llm.ainvoke(prompt)
            return result.content
        except Exception as e:
            logger.warning(f"大纲生成失败: {e}")
            return ""

    async def _generate_section(
        self,
        query: str,
        section: ReportSection,
        outline: str,
        profile_summary: str,
        knowledge_text: str,
    ) -> str:
        """生成单个章节内容"""
        prompt = f"""你是一位资深的装修行业专家，正在为用户撰写深度研究报告的「{section.title}」章节。

用户问题："{query}"

章节要求：{section.prompt_hint}

{f"报告大纲（请基于大纲展开）：{outline[:800]}" if outline else ""}
{f"用户信息：{profile_summary}" if profile_summary else ""}
{f"参考资料（优先使用）：{knowledge_text[:800]}" if knowledge_text else ""}

写作要求：
1. 以 "### {section.title}" 作为章节标题开头
2. 内容详实、有数据支撑，不要空泛
3. 如果需要表格对比，用 Markdown 表格格式
4. 语言专业但易懂，像一位有经验的朋友在认真分析
5. 字数控制在 200-400 字
6. 不要重复其他章节的内容"""

        try:
            result = await self.llm.ainvoke(prompt)
            return result.content + "\n\n"
        except Exception as e:
            logger.warning(f"章节 {section.key} 生成失败: {e}")
            return f"### {section.title}\n\n（该章节生成失败，请重试）\n\n"

    def _build_profile_summary(self, context: Dict) -> str:
        """从 context 中提取用户画像摘要"""
        parts = []
        profile = context.get("_profile")
        if not profile:
            return ""

        if profile.house_area:
            parts.append(f"面积{profile.house_area}平米")
        if profile.budget_range:
            low, high = profile.budget_range
            if low and high:
                parts.append(f"预算{low/10000:.0f}-{high/10000:.0f}万")
        if profile.preferred_styles:
            parts.append(f"风格偏好{'、'.join(profile.preferred_styles[:3])}")
        if hasattr(profile, 'city') and profile.city:
            parts.append(f"城市{profile.city}")

        extra = getattr(profile, 'extra_info', None) or {}
        family = extra.get("family_members", {})
        if family.get("has_children"):
            parts.append("家有小孩")
        if family.get("has_elderly"):
            parts.append("家有老人")

        return "；".join(parts) if parts else ""

"""
增强版智能体基类
整合记忆系统、推理引擎、工具系统和多模态能力
"""
import os
import sys
import time
import json
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
from abc import ABC, abstractmethod

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSequence
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.core.singleton import get_knowledge_base
from backend.core.memory import get_memory_manager, MemoryType, UserProfile, DecorationJourney
from backend.core.reasoning import (
    get_reasoning_engine, ReasoningType, ReasoningChain,
    TaskAnalyzer, TaskComplexity, get_reasoning_prompt,
    get_adaptive_strategy, ReasoningFormatter
)
from backend.core.tools import get_tool_registry, ToolResult
from backend.core.multimodal import get_multimodal_manager, MediaContent, MediaType
from backend.core.output_formatter import OutputFormatter, OutputType
from backend.core.function_calling import get_function_calling_engine, FunctionCallingEngine
from backend.core.cache import get_knowledge_cache, get_llm_cache
from backend.knowledge.knowledge_graph import get_knowledge_graph
from backend.core.stage_reasoning import (
    get_stage_reasoning, StageAwareReasoning, StageContext, ExpertRole, StageTransition
)
from backend.core.decision_tree import (
    get_decision_tree_engine, TreeQuestion, TreeRecommendation,
    parse_decision_tree_payload,
)
from backend.core.deep_research import DeepResearchPipeline
from backend.core.logging_config import get_logger

logger = get_logger("enhanced_agent")


class EnhancedAgent(ABC):
    """增强版智能体基类"""

    def __init__(self, user_type: str = "both", agent_name: str = "assistant"):
        self.user_type = user_type
        self.agent_name = agent_name

        # 核心组件
        self.kb = get_knowledge_base()
        self.memory = get_memory_manager()
        self.reasoning = get_reasoning_engine()
        self.adaptive_strategy = get_adaptive_strategy()
        self.tools = get_tool_registry()
        self.multimodal = get_multimodal_manager()
        self.function_calling = get_function_calling_engine()
        self.knowledge_cache = get_knowledge_cache()
        self.llm_cache = get_llm_cache()
        self.knowledge_graph = get_knowledge_graph()
        self.decision_tree = get_decision_tree_engine()
        # LLM配置
        self.llm = ChatTongyi(
            model="qwen-plus",
            temperature=0.7,
            streaming=True,
        )

        self.stage_reasoning = get_stage_reasoning(llm=self.llm)  # 阶段感知推理引擎（传入LLM启用深度分析）
        self.deep_research = DeepResearchPipeline(llm=self.llm, kb=self.kb)  # 深度研究管道

        # 配置选项
        self.enable_search = True
        self.enable_reasoning = True
        self.enable_memory = True
        self.enable_llm_function_calling = True  # 启用 LLM 智能工具调用
        self.show_thinking = True
        self.max_tool_calls = 5

        # 记忆维护计数器（每 50 次请求触发一次维护）
        self._request_count = 0
        self._maintenance_interval = 50

        # 构建处理链
        self._build_chain()

    def _build_chain(self):
        """构建处理链"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            MessagesPlaceholder(variable_name="history"),
            MessagesPlaceholder(variable_name="context"),
            ("human", "{input}"),
        ])

        self.chain = prompt | self.llm | StrOutputParser()

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """获取系统提示词（子类实现）"""
        pass

    # === 核心处理流程 ===

    async def process(self, message: str, session_id: str,
                      user_id: str = None, images: List[str] = None) -> AsyncGenerator:
        """
        处理用户消息

        Args:
            message: 用户消息
            session_id: 会话ID
            user_id: 用户ID
            images: 图片路径列表

        Yields:
            输出事件
        """
        user_id = user_id or session_id
        raw_message = message
        dt_payload = parse_decision_tree_payload(message)
        if dt_payload:
            # payload 格式：dt:tree_id:node_id:answer -> LLM 使用回答文本
            message = dt_payload[2]
        formatter = OutputFormatter(session_id, self.user_type)
        process_success = True

        # 发送流开始
        yield formatter.stream_start()

        try:
            # 1. 获取用户画像和记忆上下文（用于自适应推理）
            context = await self._prepare_context(user_id, session_id, message)
            if dt_payload:
                context["_dt_payload"] = dt_payload
                context["_raw_message"] = raw_message

            # 2. 使用自适应策略选择推理类型
            reasoning_type = self.adaptive_strategy.select_strategy(message, context)

            # 3. 创建推理链
            chain = self.reasoning.create_chain(message, reasoning_type)

            # 4. 处理多模态输入
            if images:
                for img_path in images:
                    img_result = await self._process_image(img_path)
                    context["image_analysis"] = img_result
                    self.reasoning.observe(chain, f"图片分析: {img_result.get('description', '')}")

            # 5. 知识检索
            if self.enable_search:
                docs = await self._retrieve_knowledge(message, context)
                if docs:
                    self.reasoning.act(chain, "检索知识库", tool="knowledge_search")
                    self.reasoning.observe(chain, f"找到 {len(docs)} 条相关信息")
                    context["knowledge"] = docs

            # 6. 工具调用判断
            tool_results = await self._check_and_call_tools(message, context, chain)
            if tool_results:
                context["tool_results"] = tool_results

            # 6.5 决策树引导
            tree_question = None
            if self.user_type in ("c_end", "both"):
                tree_question = self._process_decision_tree(
                    message, user_id, context, chain
                )

            # 6.8 深度研究模式检查（仅 C 端用户）
            research_action = None
            if self.user_type in ("c_end", "both"):
                research_action = self._check_deep_research(message, session_id, context)
            if research_action:
                if research_action["action"] == "confirm":
                    # 触发确认：回复确认消息 + quick_replies，然后结束本轮
                    confirmation_msg = research_action["confirmation_msg"]
                    yield formatter.answer(confirmation_msg)
                    from backend.core.output_formatter import QuickReply
                    yield formatter.quick_replies([
                        QuickReply(text="好的，帮我研究一下"),
                        QuickReply(text="不用了，简单回答就行"),
                    ])
                    # 保存本轮对话到记忆（确保原始问题不丢失）
                    if self.enable_memory:
                        await self._update_memory(user_id, session_id, message, chain, confirmation_msg)
                        if self.memory._profile_store:
                            self.memory._profile_store.save_if_dirty()
                    yield formatter.stream_end()
                    return
                elif research_action["action"] == "run":
                    # 用户已确认，启动研究管道
                    report_chunks = []
                    async for event in self.deep_research.run_research(
                        query=research_action["original_query"],
                        research_type=research_action["research_type"],
                        context=context,
                    ):
                        evt = event["event_type"]
                        data = event["data"]
                        if evt == "research_progress":
                            yield formatter.research_progress(data["step"], data["total"], data["label"])
                        elif evt == "research_report":
                            yield formatter.research_report_header(data["title"], data["research_type"], data["sections"])
                        elif evt == "answer":
                            report_chunks.append(data)
                            yield formatter.answer(data)
                    # 研究完成后更新记忆（保存报告摘要而非占位符）
                    if self.enable_memory:
                        report_summary = "".join(report_chunks)
                        if len(report_summary) > 800:
                            report_summary = report_summary[:800] + "..."
                        await self._update_memory(
                            user_id, session_id,
                            research_action["original_query"],  # 保存原始问题而非确认消息
                            chain, report_summary,
                        )
                        if self.memory._profile_store:
                            self.memory._profile_store.save_if_dirty()
                    yield formatter.stream_end()
                    return
                elif research_action["action"] == "decline":
                    # 用户拒绝研究，用原始问题替换当前消息，走正常回答流程
                    original_query = research_action.get("original_query")
                    if original_query:
                        message = original_query

            # 7. 输出专家诊断信息（在思考过程之前）
            if "stage_context" in context:
                yield formatter.expert_debug(context)

            # 8. 输出思考过程（使用格式化器）
            if self.show_thinking:
                thinking_logs = chain.get_thinking_log()
                # 将专家角色信息追加到思考日志
                if "stage_context" in context:
                    stage_ctx = context["stage_context"]
                    expert_role = context.get("expert_role")
                    expert_name = expert_role.name if expert_role else "通用顾问"
                    thinking_logs.append(
                        f"阶段判断: {stage_ctx.stage}（置信度 {stage_ctx.stage_confidence:.0%}）→ 专家角色: {expert_name}"
                    )
                    if stage_ctx.emotional_state and stage_ctx.emotional_state != "平静":
                        thinking_logs.append(f"用户情绪: {stage_ctx.emotional_state}")
                if thinking_logs:
                    yield formatter.thinking(thinking_logs, reasoning_type.value)

            # 9. 生成回答（同时收集完整回复用于保存到记忆）
            full_response = []
            async for chunk in self._generate_response(message, context, chain):
                full_response.append(chunk)
                yield formatter.answer(chunk)

            # 10. 更新记忆（同时保存用户消息和助手回复）
            if self.enable_memory:
                assistant_response = "".join(full_response)
                await self._update_memory(user_id, session_id, message, chain, assistant_response)
                # 将 agent 学到的画像数据同步回用户数据库
                self._sync_profile_to_db(user_id, context.get("_profile"))
                # 持久化 profile 到磁盘（跨会话记忆的关键）
                if self.memory._profile_store:
                    self.memory._profile_store.save_if_dirty()

                # 定期触发记忆维护（遗忘曲线、记忆合并）
                self._request_count += 1
                if self._request_count % self._maintenance_interval == 0:
                    try:
                        self.memory.run_maintenance()
                    except Exception as e:
                        logger.debug(f"记忆维护跳过: {e}")

            # 10.5 决策树引导问题（在回答之后、流结束之前发送快捷回复）
            if tree_question:
                from backend.core.output_formatter import QuickReply
                replies = [QuickReply(text=opt, payload=f"dt:{tree_question.tree_id}:{tree_question.node_id}:{opt}")
                           for opt in tree_question.options]
                yield formatter.quick_replies(replies)

            # 11. 发送流结束
            yield formatter.stream_end()

            # 12. 记录推理结果（用于策略优化）
            self.adaptive_strategy.record_result(
                query=message,
                reasoning_type=reasoning_type,
                success=True
            )

        except Exception as e:
            process_success = False
            logger.error("处理流程异常", extra={
                "error": str(e),
                "user_id": user_id,
                "session_id": session_id,
                "query": message[:100],
            }, exc_info=True)
            yield formatter.error(str(e), "PROCESS_ERROR")
            yield formatter.stream_end()

            # 记录失败
            if 'reasoning_type' in locals():
                self.adaptive_strategy.record_result(
                    query=message,
                    reasoning_type=reasoning_type,
                    success=False
                )

    async def _prepare_context(self, user_id: str, session_id: str,
                                message: str) -> Dict:
        """准备上下文"""
        context = {
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "user_type": self.user_type,
            "_user_message": message,  # 传递原始消息，供避坑预警等模块使用
        }

        if self.enable_memory:
            # 获取用户画像
            profile = self.memory.get_or_create_profile(user_id, self.user_type)

            # 从用户数据库同步基础信息到 memory profile（双向：DB 优先填充空字段）
            try:
                from backend.core.user import get_user_store
                db_user = get_user_store().get_user_by_id(user_id)
                if db_user:
                    if db_user.house_area and not profile.house_area:
                        profile.house_area = db_user.house_area
                    if db_user.budget_min or db_user.budget_max:
                        if not profile.budget_range or profile.budget_range == (None, None):
                            profile.budget_range = (db_user.budget_min, db_user.budget_max)
                    if db_user.city and not profile.city:
                        profile.city = db_user.city
                    if db_user.nickname and not profile.name:
                        profile.name = db_user.nickname
            except Exception:
                pass

            context["user_profile"] = {
                "interests": profile.interests,
                "preferred_styles": profile.preferred_styles,
                "budget_range": profile.budget_range,
                "communication_style": profile.communication_style,
            }
            # 保存完整 profile 引用，供 _build_prompt_parts 深度使用
            context["_profile"] = profile

            # 获取装修阶段信息（新增）
            stage_info = self._get_stage_context(profile)
            if stage_info:
                context["decoration_stage"] = stage_info

            # 获取用户痛点（新增）
            if profile.pain_points:
                context["pain_points"] = profile.pain_points[-3:]  # 最近3个痛点

            # 推断下一个需求（新增）
            next_need = profile.infer_next_need()
            if next_need:
                context["inferred_need"] = next_need

            # 获取记忆上下文
            memory_context = self.memory.get_context_for_query(user_id, session_id, message)
            context["memory"] = memory_context

            # 获取工作记忆
            context["working_memory"] = self.memory.get_all_working_memory(session_id)

            # === 阶段感知专家系统 ===
            # 获取之前的阶段（用于检测阶段转换）
            previous_stage = profile.decoration_stage

            # 获取对话历史
            conversation_history = []
            if "short_term_memory" in memory_context:
                conversation_history = memory_context["short_term_memory"]

            # 深度阶段理解
            try:
                stage_context, expert_role, stage_transition = await self.stage_reasoning.analyze_and_get_expert(
                    query=message,
                    conversation_history=conversation_history,
                    user_profile=context["user_profile"],
                    previous_stage=previous_stage,
                    user_type=self.user_type,
                )

                # 保存阶段上下文
                context["stage_context"] = stage_context
                context["expert_role"] = expert_role

                # 记录阶段分析结果
                logger.info("阶段感知分析完成", extra={
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": message[:100],
                    "detected_stage": stage_context.stage,
                    "stage_confidence": stage_context.stage_confidence,
                    "expert_role": expert_role.name if expert_role else None,
                    "emotional_state": stage_context.emotional_state,
                    "focus_points": stage_context.focus_points,
                    "stage_transition": bool(stage_transition),
                })

                # 处理阶段转换
                if stage_transition:
                    context["stage_transition"] = stage_transition

                    logger.info("检测到阶段转换", extra={
                        "user_id": user_id,
                        "session_id": session_id,
                        "from_stage": stage_transition.from_stage,
                        "to_stage": stage_transition.to_stage,
                        "confidence": stage_transition.confidence,
                        "trigger": stage_transition.trigger,
                    })
                    # 更新用户画像中的阶段
                    profile.update_decoration_stage(
                        stage_transition.to_stage,
                        trigger=stage_transition.trigger,
                        confidence=stage_transition.confidence
                    )
                    # 记录阶段转换事件
                    if profile.decoration_journey:
                        profile.decoration_journey.record_stage_transition(
                            from_stage=stage_transition.from_stage,
                            to_stage=stage_transition.to_stage,
                            trigger=stage_transition.trigger,
                            confidence=stage_transition.confidence
                        )

            except Exception as e:
                # 阶段分析失败时使用默认行为，但记录警告
                logger.warning("阶段感知分析失败", extra={
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": message[:100],
                    "error": str(e),
                })

        return context

    def _get_stage_context(self, profile: UserProfile) -> Optional[Dict]:
        """
        获取装修阶段上下文

        根据用户当前装修阶段，提供相关的上下文信息和建议
        """
        if not profile.decoration_journey:
            # 如果没有装修旅程信息，尝试从decoration_stage推断
            if profile.decoration_stage:
                return {
                    "current_stage": profile.decoration_stage,
                    "stage_tips": self._get_stage_tips(profile.decoration_stage),
                    "recommended_topics": self._get_stage_topics(profile.decoration_stage),
                }
            return None

        journey = profile.decoration_journey
        stage_info = {
            "current_stage": journey.current_stage,
            "completed_stages": journey.completed_stages,
            "progress": journey.actual_progress,
            "stage_tips": self._get_stage_tips(journey.current_stage),
            "recommended_topics": self._get_stage_topics(journey.current_stage),
        }

        # 如果有阶段开始时间，计算已进行天数
        if journey.stage_start_date:
            import time
            days_in_stage = int((time.time() - journey.stage_start_date) / 86400)
            stage_info["days_in_current_stage"] = days_in_stage

        return stage_info

    def _get_stage_tips(self, stage: str) -> List[str]:
        """获取阶段相关提示"""
        stage_tips = {
            "准备": [
                "确定装修预算，建议留10%机动资金",
                "多看装修案例，明确自己喜欢的风格",
                "了解装修流程，做好时间规划",
            ],
            "设计": [
                "仔细审核设计方案，确认每个细节",
                "注意动线设计是否合理",
                "确认收纳空间是否充足",
            ],
            "施工": [
                "定期到现场检查施工质量",
                "水电改造后拍照留存管线走向",
                "防水必须做闭水试验",
            ],
            "软装": [
                "家具尺寸要提前确认",
                "注意家具与整体风格的搭配",
                "软装可以分批购买，不必一次到位",
            ],
            "入住": [
                "入住前做甲醛检测",
                "建议通风3个月以上",
                "保留好各项保修凭证",
            ],
        }
        return stage_tips.get(stage, [])

    def _get_stage_topics(self, stage: str) -> List[str]:
        """获取阶段推荐话题"""
        stage_topics = {
            "准备": ["预算规划", "风格选择", "装修公司选择", "设计师选择"],
            "设计": ["方案优化", "材料选择", "报价审核", "合同注意事项"],
            "施工": ["施工进度", "质量验收", "材料进场", "工艺标准"],
            "软装": ["家具选购", "软装搭配", "灯具选择", "窗帘布艺"],
            "入住": ["甲醛治理", "家电选购", "收纳整理", "维护保养"],
        }
        return stage_topics.get(stage, [])

    async def _retrieve_knowledge(self, query: str, context: Dict) -> List[Dict]:
        """检索知识（带缓存）"""
        try:
            # 尝试从缓存获取
            cached_results = self.knowledge_cache.find_similar(
                query=query,
                user_type=self.user_type,
                k=5
            )
            if cached_results is not None:
                return cached_results

            # 使用正确的 search_by_user_type 方法
            results = self.kb.search_by_user_type(
                query=query,
                user_type=self.user_type,
                k=5,
            )
            formatted_results = [
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "unknown"),
                    "collection": doc.metadata.get("collection", "unknown"),
                    "score": score,
                }
                for doc, score in results
            ]

            # 缓存结果
            if formatted_results:
                self.knowledge_cache.set(
                    query=query,
                    user_type=self.user_type,
                    k=5,
                    results=formatted_results
                )

            return formatted_results
        except Exception as e:
            return []

    async def _check_and_call_tools(self, message: str, context: Dict,
                                     chain: ReasoningChain) -> Dict:
        """检查并调用工具"""
        results = {}

        # 优先使用 LLM Function Calling（如果启用）
        if self.enable_llm_function_calling:
            try:
                fc_result = await self.function_calling.process_with_tools(
                    message=message,
                    context=context,
                )

                # 记录思考过程
                for thought in fc_result.thinking:
                    self.reasoning.observe(chain, thought)

                # 处理工具调用结果
                for call in fc_result.calls:
                    if call.result:
                        results[call.name] = call.result
                        self.reasoning.act(chain, f"调用工具 {call.name}", tool=call.name)
                        self.reasoning.observe(chain, f"工具结果: {json.dumps(call.result, ensure_ascii=False)[:200]}")

                if results:
                    return results
            except Exception as e:
                self.reasoning.observe(chain, f"LLM Function Calling 失败: {str(e)}")

        # 回退到规则匹配（兼容模式）
        return await self._check_and_call_tools_fallback(message, context, chain)

    async def _check_and_call_tools_fallback(self, message: str, context: Dict,
                                              chain: ReasoningChain) -> Dict:
        """使用规则匹配调用工具（回退方案）"""
        results = {}

        # 补贴计算检测
        if any(kw in message for kw in ["补贴", "能补多少", "返多少"]):
            # 尝试提取金额和品类
            amount = self._extract_amount(message)
            category = self._extract_category(message)
            if amount and category:
                self.reasoning.act(chain, f"计算{category}补贴", tool="subsidy_calculator")
                result = self.tools.call("subsidy_calculator", amount=amount, category=category)
                if result.success:
                    results["subsidy"] = result.data
                    self.reasoning.observe(chain, f"补贴计算结果: {result.data.get('final_amount', 0)}元")

        # ROI计算检测
        if any(kw in message for kw in ["ROI", "投入产出", "回报率"]):
            investment = self._extract_amount(message, "投入")
            revenue = self._extract_amount(message, "收入")
            if investment and revenue:
                self.reasoning.act(chain, "计算ROI", tool="roi_calculator")
                result = self.tools.call("roi_calculator", investment=investment, revenue=revenue)
                if result.success:
                    results["roi"] = result.data
                    self.reasoning.observe(chain, f"ROI: {result.data.get('roi_percent', 0)}%")

        # 价格评估检测
        if any(kw in message for kw in ["贵不贵", "价格合理", "值不值"]):
            price = self._extract_amount(message)
            category = self._extract_category(message)
            if price and category:
                self.reasoning.act(chain, "评估价格", tool="price_evaluator")
                result = self.tools.call("price_evaluator", category=category, price=price)
                if result.success:
                    results["price_eval"] = result.data

        # 工期估算检测
        if any(kw in message for kw in ["多久", "工期", "多长时间"]):
            area = self._extract_area(message)
            if area:
                self.reasoning.act(chain, "估算工期", tool="decoration_timeline")
                result = self.tools.call("decoration_timeline", house_area=area)
                if result.success:
                    results["timeline"] = result.data

        return results

    async def _process_image(self, image_path: str) -> Dict:
        """处理图片"""
        content = MediaContent(
            media_type=MediaType.IMAGE,
            content=image_path,
        )
        return self.multimodal.process(content)

    async def _generate_response(self, message: str, context: Dict,
                                  chain: ReasoningChain) -> AsyncGenerator[str, None]:
        """生成回答"""
        # 构建提示词的两个部分
        system_prompt, supplementary_context = self._build_prompt_parts(context)

        # supplementary_context 始终作为独立 system message 注入，不嵌入用户消息
        context_messages = []
        if supplementary_context:
            context_messages.append(SystemMessage(content=supplementary_context))

        # 构建用户输入
        if self.enable_reasoning and chain.reasoning_type != ReasoningType.DIRECT:
            # 推理模式：只传推理指令 + 用户问题，不再嵌入 context
            reasoning_prompt = get_reasoning_prompt(
                chain.reasoning_type,
                message,
                "",  # context 已通过 context_messages 独立注入
            )
            input_message = reasoning_prompt
        else:
            input_message = message

        # 构建消息历史
        history = self._get_message_history(context)

        chain_input = {
            "input": input_message,
            "system_prompt": system_prompt,
            "history": history,
            "context": context_messages,
        }

        logger.debug("开始生成回答", extra={
            "system_prompt_length": len(system_prompt),
            "context_messages_count": len(context_messages),
            "history_count": len(history),
        })

        # 流式生成（带重试）
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                async for chunk in self.chain.astream(chain_input):
                    yield chunk
                return  # 成功完成，退出
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries and ("prematurely" in error_msg or "ConnectionError" in error_msg or "timeout" in error_msg.lower()):
                    logger.warning(f"流式生成中断，重试 {attempt + 1}/{max_retries}", extra={
                        "error": error_msg,
                    })
                    continue
                else:
                    raise  # 非网络错误或重试耗尽，向上抛出

    def _process_decision_tree(self, message: str, user_id: str,
                                context: Dict, chain) -> Optional[TreeQuestion]:
        """
        决策树处理逻辑

        1. 检测是否应该激活决策树
        2. 尝试从消息中匹配答案
        3. 如果有未回答的问题，返回 TreeQuestion（后续发送为 quick_replies）
        4. 如果所有问题已回答，将推荐上下文注入 context

        Returns:
            TreeQuestion 如果有下一个问题要问，否则 None
        """
        try:
            profile = context.get("_profile")
            stage = None
            if "stage_context" in context:
                stage = context["stage_context"].stage

            payload = context.get("_dt_payload")
            session_id = context.get("session_id")

            # 检测是否触发决策树
            tree_id = None
            if payload:
                tree_id, node_id, answer = payload
                self.decision_tree.record_answer(user_id, tree_id, node_id, answer)
            else:
                tree_id = self.decision_tree.detect_tree(message, stage)
                if not tree_id:
                    # 优先尝试从工作记忆中恢复 active tree
                    working = context.get("working_memory", {})
                    tree_id = working.get("active_tree_id") or context.get("_active_tree_id")
                    if not tree_id:
                        return None

            # 尝试匹配当前消息为某个节点的答案
            tree = self.decision_tree.trees.get(tree_id)
            if tree and not payload:
                for node_id, node in tree["nodes"].items():
                    matched = self.decision_tree.try_match_answer(tree_id, node_id, message)
                    if matched:
                        self.decision_tree.record_answer(user_id, tree_id, node_id, matched)

            # 获取下一个问题
            next_q = self.decision_tree.get_next_question(
                tree_id=tree_id,
                user_id=user_id,
                profile=profile,
                message=message,
            )

            if next_q:
                # 还有问题要问——将问题信息注入思考链
                self.reasoning.observe(
                    chain,
                    f"决策树引导: {tree_id} → 下一个问题: {next_q.question}（进度 {next_q.progress:.0%}）"
                )
                # 将决策树问题注入 context，让 LLM 在回答中自然地引出这个问题
                context["decision_tree_question"] = {
                    "tree_id": tree_id,
                    "question": next_q.question,
                    "options": next_q.options,
                    "why": next_q.why,
                    "progress": next_q.progress,
                }
                context["_active_tree_id"] = tree_id
                if session_id:
                    self.memory.set_working_memory(session_id, "active_tree_id", tree_id)
                return next_q
            else:
                # 所有问题已回答——生成推荐上下文
                rec = self.decision_tree.get_recommendation_context(tree_id, user_id)
                if rec:
                    context["decision_tree_recommendation"] = rec.recommendation_context
                    self.reasoning.observe(
                        chain,
                        f"决策树完成: {tree_id}，已收集全部信息，生成个性化推荐"
                    )
                if session_id:
                    self.memory.set_working_memory(session_id, "active_tree_id", "")
                return None

        except Exception as e:
            logger.warning(f"决策树处理异常: {e}", exc_info=True)
            return None

    def _check_deep_research(self, message: str, session_id: str, context: Dict) -> Optional[Dict]:
        """
        检查是否触发深度研究模式

        Returns:
            {"action": "confirm", "confirmation_msg": str, ...} — 需要用户确认
            {"action": "run", "original_query": str, "research_type": str} — 用户已确认，执行研究
            {"action": "decline"} — 用户拒绝研究
            None — 不触发研究
        """
        try:
            working = context.get("working_memory", {})
            pending = working.get("pending_research")

            if pending:
                # 有待确认的研究请求，检查用户是否确认
                # 使用精确匹配（完整消息 strip 后比较），避免子串误匹配
                # 如 "行" 不应匹配 "银行", "可以" 不应匹配 "可以吗?"
                msg_stripped = message.strip().rstrip("。.！!~")
                confirm_exact = {"好的，帮我研究一下", "好的", "帮我研究一下", "帮我研究", "研究一下", "可以", "行", "嗯", "是的", "没问题", "好", "ok", "OK"}
                decline_exact = {"不用了，简单回答就行", "不用了", "不需要", "算了", "简单回答就行", "简单回答", "不用", "别了"}

                is_confirm = msg_stripped in confirm_exact
                is_decline = msg_stripped in decline_exact

                if is_confirm:
                    # 清除 pending
                    self.memory.set_working_memory(session_id, "pending_research", "")
                    if isinstance(pending, str):
                        try:
                            pending = json.loads(pending)
                        except Exception:
                            return None
                    return {
                        "action": "run",
                        "original_query": pending.get("original_query", message),
                        "research_type": pending.get("research_type", "product_comparison"),
                    }
                elif is_decline:
                    self.memory.set_working_memory(session_id, "pending_research", "")
                    # 解析 pending 获取原始问题，让正常流程回答它
                    original_query = message
                    if isinstance(pending, str):
                        try:
                            parsed = json.loads(pending)
                            original_query = parsed.get("original_query", message)
                        except Exception:
                            pass
                    elif isinstance(pending, dict):
                        original_query = pending.get("original_query", message)
                    return {"action": "decline", "original_query": original_query}
                else:
                    # 用户说了别的，清除 pending，正常处理
                    self.memory.set_working_memory(session_id, "pending_research", "")
                    return None

            # 没有 pending，检查当前消息是否触发新的研究
            trigger = self.deep_research.detect_trigger(message)
            if trigger:
                # 存入 working memory，等待用户确认
                pending_data = json.dumps({
                    "original_query": trigger["original_query"],
                    "research_type": trigger["research_type"],
                }, ensure_ascii=False)
                self.memory.set_working_memory(session_id, "pending_research", pending_data)
                return {
                    "action": "confirm",
                    "confirmation_msg": trigger["confirmation_msg"],
                }

            return None
        except Exception as e:
            logger.warning(f"深度研究检查异常: {e}", exc_info=True)
            return None

    def _build_profile_summary(self, profile) -> str:
        """
        构建用户画像摘要——让LLM真正了解用户的具体情况，实现个性化回答

        不是简单罗列字段，而是生成LLM能理解并据此调整回答的自然语言描述。
        """
        parts = []
        if profile.house_area:
            parts.append(f"房屋面积：{profile.house_area}平米（请用此面积计算，不要用100㎡等假设值）")
        if profile.budget_range:
            low, high = profile.budget_range
            if low and high:
                low_wan = low / 10000
                high_wan = high / 10000
                parts.append(f"预算范围：{low_wan:.0f}-{high_wan:.0f}万元（请基于此预算给建议）")
            elif high:
                high_wan = high / 10000
                parts.append(f"预算上限：{high_wan:.0f}万元")
        if profile.preferred_styles:
            parts.append(f"偏好风格：{'、'.join(profile.preferred_styles[:3])}")
        if profile.decoration_stage:
            parts.append(f"当前阶段：{profile.decoration_stage}")
        if hasattr(profile, 'city') and profile.city:
            parts.append(f"所在城市：{profile.city}")

        # 痛点——直接影响回答的侧重点
        if profile.pain_points:
            top_pains = sorted(profile.pain_points, key=lambda x: x.get('severity', 0), reverse=True)[:3]
            pain_descs = [p.get('description', p.get('type', '')) for p in top_pains]
            parts.append(f"主要关注：{'、'.join(pain_descs)}")

        # 家庭成员——影响安全标准和环保等级推荐
        extra = getattr(profile, 'extra_info', None) or {}
        family = extra.get("family_members", {})
        if family.get("has_elderly"):
            parts.append("家有老人（注意无障碍设计和防滑）")
        if family.get("has_children"):
            parts.append("家有小孩（注意环保等级和安全防护）")
        if family.get("has_pets"):
            parts.append("家有宠物（注意耐磨和易清洁材料）")

        # 兴趣——用户最近关注的品类
        if profile.interests:
            top_interests = sorted(profile.interests.items(), key=lambda x: x[1], reverse=True)[:5]
            parts.append(f"近期关注：{'、'.join(k for k, v in top_interests)}")

        # 品牌偏好——用户提到过的品牌及态度
        brand_mentions = extra.get("brand_mentions", [])
        if brand_mentions:
            brand_parts = []
            for b in brand_mentions[-5:]:  # 最近5个
                sentiment_label = {"positive": "好评", "negative": "差评", "neutral": "提及"}.get(b.get("sentiment"), "提及")
                brand_parts.append(f"{b['brand']}({sentiment_label})")
            parts.append(f"品牌印象：{'、'.join(brand_parts)}")

        # 已做决策——用户已经确定的事项
        decisions = extra.get("decisions", [])
        if decisions:
            decision_texts = [d["text"] for d in decisions[-5:]]
            parts.append(f"已做决策：{'；'.join(decision_texts)}（已决定的不要再推荐替代方案）")

        if not parts:
            return ""
        return "\n".join(parts)

    def _sync_profile_to_db(self, user_id: str, profile):
        """将 agent 学到的画像数据同步回用户数据库（双向同步）"""
        if not profile or not user_id or user_id.startswith("c_end_") or user_id.startswith("b_end_"):
            return  # 跳过非真实用户ID
        try:
            from backend.core.user import get_user_store
            store = get_user_store()
            db_user = store.get_user_by_id(user_id)
            if not db_user:
                return

            updates = {}
            if profile.house_area and not db_user.house_area:
                updates["house_area"] = profile.house_area
            if profile.budget_range:
                low, high = profile.budget_range
                if low and not db_user.budget_min:
                    updates["budget_min"] = low
                if high and not db_user.budget_max:
                    updates["budget_max"] = high
            if hasattr(profile, 'city') and profile.city and not db_user.city:
                updates["city"] = profile.city

            if updates:
                store.update_user(user_id, **updates)
                logger.debug("画像数据同步到用户DB", extra={"user_id": user_id, "updates": list(updates.keys())})
        except Exception as e:
            logger.debug(f"画像同步到DB跳过: {e}")

    def _format_tool_results(self, tool_results: Dict) -> str:
        """
        将工具计算结果转化为LLM可理解的自然语言摘要

        不是输出原始JSON，而是提取关键数据点，让LLM能自然地引用这些数据。
        """
        summaries = []
        for tool_name, result in tool_results.items():
            if not isinstance(result, dict):
                continue

            if tool_name == "subsidy" or "subsidy" in tool_name:
                amt = result.get("final_amount", result.get("calculated_amount", 0))
                rate = result.get("subsidy_rate", 0)
                cat = result.get("category", "")
                summaries.append(f"【补贴计算】{cat}补贴金额约{amt}元（补贴比例{rate*100 if rate < 1 else rate}%）")

            elif tool_name == "roi" or "roi" in tool_name:
                roi_pct = result.get("roi_percent", 0)
                assessment = result.get("assessment", "")
                summaries.append(f"【ROI分析】投资回报率{roi_pct}%，评估：{assessment}")

            elif tool_name == "price_eval" or "price" in tool_name:
                evaluation = result.get("evaluation", "")
                ref_range = result.get("reference_range", {})
                if ref_range:
                    summaries.append(f"【价格评估】{evaluation}，市场参考区间{ref_range.get('low', '')}-{ref_range.get('high', '')}元")
                else:
                    summaries.append(f"【价格评估】{evaluation}")

            elif tool_name == "timeline" or "timeline" in tool_name:
                total = result.get("total_days", 0)
                summaries.append(f"【工期估算】预计总工期约{total}天")

            elif "budget" in tool_name:
                total = result.get("total_budget", 0)
                breakdown = result.get("breakdown", result.get("allocation", {}))
                if isinstance(breakdown, dict) and breakdown:
                    items = [f"{k}{v}元" if isinstance(v, (int, float)) else f"{k}:{v}" for k, v in list(breakdown.items())[:5]]
                    summaries.append(f"【预算规划】总预算{total}元，分配：{'、'.join(items)}")
                else:
                    summaries.append(f"【预算规划】总预算{total}元")

            elif "material" in tool_name and "calc" in tool_name:
                qty = result.get("quantity", result.get("total_quantity", 0))
                unit = result.get("unit", "")
                summaries.append(f"【材料用量】需要约{qty}{unit}")

            else:
                # 通用格式：取前200字符的JSON
                summaries.append(f"【{tool_name}】{json.dumps(result, ensure_ascii=False)[:200]}")

        return "\n".join(summaries)

    # === 避坑预警规则 ===
    PITFALL_RULES = [
        # --- 合同与施工队 ---
        {"pattern": r"(全包|大包).*(装修公司|施工队)",
         "warning": "⚠️ 全包注意事项：①主材品牌和型号必须写进合同 ②增项上限建议不超过总价10% ③付款建议按3-4-2-1分期，不要一次付清。"},
        {"pattern": r"(熟人|朋友|亲戚).*(装修|施工|帮忙装)",
         "warning": "⚠️ 熟人装修提醒：①一样要签正式合同 ②一样要明确验收标准 ③出了问题更难开口，合同该签还是要签。"},
        {"pattern": r"(游击队|路边|没有资质|没有合同)",
         "warning": "⚠️ 没有资质的施工队风险很大：①出了质量问题无法追责 ②没有保修保障 ③安全事故责任不清。建议选有营业执照的正规公司或工长。"},
        {"pattern": r"(先施工|先开工).*(再签|不签|不用签).*(合同|协议)",
         "warning": "⚠️ 一定要先签合同再开工！合同要明确：①总价和付款节点 ②材料品牌型号 ③工期和违约责任 ④验收标准。口头承诺不算数。"},
        {"pattern": r"(口头|口头承诺|说好了).*(不用|不签).*(合同|协议|书面)",
         "warning": "⚠️ 口头承诺没有法律效力。所有约定必须写进书面合同，包括增项价格、工期延误赔偿、材料替换规则。"},
        {"pattern": r"(一次|全部|全款).*(付清|付完|打款|转账)",
         "warning": "⚠️ 千万不要一次付清全款！建议按进度分期付款（3-4-2-1），留5-10%尾款作为质保金，竣工验收合格后再付清。"},
        # --- 防水与水电 ---
        {"pattern": r"(不做|省掉|不需要|不用).*(防水|闭水)",
         "warning": "⚠️ 防水绝对不能省！卫生间、厨房、阳台都必须做防水，墙面至少1.8米高。漏水不仅自己遭殃，赔楼下更贵。"},
        {"pattern": r"(水电).*(走地|地面|地下).*省",
         "warning": "⚠️ 水电走地虽然省钱，但后期维修要撬地砖，成本更高。厨卫水管建议走顶，方便检修漏水。"},
        {"pattern": r"(水电).*(不用|不需要|没必要).*(换|改|重做)",
         "warning": "⚠️ 二手房/老房的水电建议全部重做。老旧电线承载力不够，老旧水管容易锈蚀漏水，这是安全隐患，不是省钱的地方。"},
        {"pattern": r"(电线).*(2\.5|两点五|细一点|小一点).*(够|行|可以)",
         "warning": "⚠️ 厨房、卫生间、空调回路建议用4平方电线，普通插座用2.5平方。用细了会发热跳闸，严重的会引发火灾。"},
        # --- 材料选择 ---
        {"pattern": r"(最便宜|最低价|越便宜越好).*(瓷砖|地板|涂料|防水|水管|电线)",
         "warning": "⚠️ 有些地方可以省，有些真不能省。防水、水电、五金件这三样用差的，后期维修成本是省下的10倍。建议这三项选中档以上。"},
        {"pattern": r"(不做|省掉|不需要).*(吊顶|石膏线).*厨房|厨房.*(不做|省掉).*(吊顶|铝扣板)",
         "warning": "⚠️ 厨房吊顶建议做铝扣板，方便后期检修水管和油烟机管道。不做吊顶后期维修很麻烦。"},
        {"pattern": r"(地板).*(泡水|不怕水|防水).*(没事|没关系|不怕)",
         "warning": "⚠️ 实木地板和强化地板都怕水！卫生间、厨房、阳台不建议铺木地板。如果一定要木纹效果，可以选木纹砖。"},
        {"pattern": r"(瓷砖).*(不用|不需要|没必要).*(留缝|美缝)",
         "warning": "⚠️ 瓷砖必须留缝！不留缝热胀冷缩会导致起拱、空鼓。普通砖留1.5-2mm，仿古砖留3-5mm。美缝建议做，防霉防黑好打理。"},
        {"pattern": r"(窗户|门窗|铝合金|断桥铝).*(不用换|不换|原来的就行)",
         "warning": "⚠️ 老旧门窗建议更换断桥铝。隔音隔热差距很大，尤其是临街或高层。窗户是住进去后最影响居住体验的项目之一。"},
        {"pattern": r"(插座|开关).*(够了|不用多|少装点)",
         "warning": "⚠️ 插座宁多勿少！厨房至少8-10个，卫生间4-6个，卧室床头两侧各2个。后期加插座要走明线，又丑又不安全。"},
        # --- 环保与健康 ---
        {"pattern": r"(甲醛).*(没事|没关系|不用管|通风几天就行)",
         "warning": "⚠️ 甲醛释放周期3-15年，不是通风几天就能解决的。建议：①通风至少3个月 ②找专业机构检测（别用网上买的试纸，不准）③有小孩老人的家庭更要重视。"},
        {"pattern": r"(板材|柜子|衣柜|橱柜).*(E2|颗粒板|密度板).*(便宜|省钱|够了)",
         "warning": "⚠️ 板材环保等级很重要！建议至少选E1级，有条件选ENF级。颗粒板不是不能用，但一定要看环保等级证书，别只看价格。"},
        # --- 验收与监理 ---
        {"pattern": r"(验收|检查).*(不用|不需要|算了|麻烦)",
         "warning": "⚠️ 每个节点的验收都很重要！特别是：①水电隐蔽工程验收（拍照留存）②防水闭水试验（48小时）③瓷砖空鼓检查。发现问题当场整改，过后再改代价翻倍。"},
        {"pattern": r"(隐蔽工程|水电完工).*(不用|不需要|没必要).*(拍照|留证|记录)",
         "warning": "⚠️ 隐蔽工程一定要拍照留存！水管走向、电线布局、防水涂刷，封起来之后看不到了。后期维修全靠这些照片定位。"},
        # --- 预算与增项 ---
        {"pattern": r"(增项|加钱|追加).*(正常|都这样|没办法)",
         "warning": "⚠️ 合理增项一般不超过总价10%。超过的要警惕是不是故意低价签约再加钱。每一项增项都要有书面报价单，签字确认后再施工。"},
        {"pattern": r"(预算|钱).*(不够|超了|超支).*(凑合|将就|先这样)",
         "warning": "⚠️ 预算不够时优先保硬装（水电、防水、墙面），软装可以后期慢慢添。千万别在隐蔽工程上省钱，这些后期改的成本是现在的5-10倍。"},
        {"pattern": r"(设计师|设计费).*(不用|不需要|浪费|省掉|免费的就行)",
         "warning": "⚠️ 好的设计师能帮你避免很多空间浪费和选材踩坑。免费设计往往靠带你买材料赚回扣。如果预算有限，至少花钱做个平面方案和水电点位图。"},
        # --- 工期与流程 ---
        {"pattern": r"(工期|工程).*(赶|快点|加快|催).*(入住|搬进去|住进去)",
         "warning": "⚠️ 赶工期是装修大忌！墙面没干透就刷漆会开裂，防水没干透就贴砖会脱落，通风不够就入住影响健康。该等的工序一定要等。"},
        {"pattern": r"(先装|先做).*(柜子|衣柜|橱柜).*(再|然后).*(贴砖|铺地板|刷墙)",
         "warning": "⚠️ 装修顺序很重要！正确顺序：拆改→水电→防水→贴砖→吊顶→墙面→地板→柜子→软装。顺序错了返工成本很高。"},
    ]

    def _check_pitfall_warnings(self, message: str) -> List[str]:
        """检查用户消息是否触发避坑预警"""
        import re
        warnings = []
        for rule in self.PITFALL_RULES:
            if re.search(rule["pattern"], message, re.IGNORECASE):
                warnings.append(rule["warning"])
        return warnings

    # === 话题-依赖关系图：用户聊到某个话题时，检查前置依赖是否完成 ===
    # 设计理念：装修决策之间有天然的依赖关系。用户可能跳着聊，
    # 但智能体要像有经验的朋友一样，听到你聊后面的事时自然提一句前面的。
    # 每条规则：当用户消息匹配 trigger 时，检查 requires 中的前置条件，
    # 未满足的就生成提醒。
    TOPIC_DEPENDENCY_GRAPH = [
        # --- 用户聊选材，但基础信息还没定 ---
        {
            "trigger": r"瓷砖|地砖|墙砖|地板|木地板",
            "requires": [
                {"check": "profile.budget_range", "missing_hint": "选材之前最好先定个大概预算范围，不然容易看花眼或者买贵了"},
                {"check": "profile.preferred_styles", "missing_hint": "风格还没定的话，建议先确定整体风格再选材，不然买回来容易不搭"},
            ],
        },
        {
            "trigger": r"瓷砖|地砖|贴砖|瓦工",
            "requires": [
                {"check": "decision:防水|闭水", "missing_hint": "贴砖之前防水一定要先做好并通过闭水试验（48小时），贴完砖再补防水代价很大"},
            ],
        },
        {
            "trigger": r"橱柜|厨房.*柜|定制.*柜",
            "requires": [
                {"check": "decision:水电.*点位|水电.*改", "missing_hint": "橱柜要在水电改造前做初步测量，确定水电点位。顺序反了后期改动成本很高"},
            ],
        },
        {
            "trigger": r"马桶|花洒|浴室柜|卫浴",
            "requires": [
                {"check": "decision:防水|闭水", "missing_hint": "卫浴安装前确认防水已经做好并验收通过，马桶坑距也要提前量好"},
            ],
        },
        # --- 用户聊施工，但设计还没定 ---
        {
            "trigger": r"开工|施工队|装修公司.*签|签.*合同",
            "requires": [
                {"check": "profile.budget_range", "missing_hint": "签合同前一定要先明确总预算，合同里要写清总价、付款节点和增项上限"},
                {"check": "decision:设计.*方案|平面.*图|设计师", "missing_hint": "建议至少有平面布局图和水电点位图再开工，边施工边改设计是最烧钱的"},
            ],
        },
        {
            "trigger": r"水电.*改|改.*水电|水电.*施工",
            "requires": [
                {"check": "decision:插座.*位置|开关.*位置|水电.*点位", "missing_hint": "水电改造前要把所有插座开关位置定好，封槽之后再改要砸墙。建议结合家具尺寸和生活习惯仔细规划"},
                {"check": "decision:橱柜.*测量|橱柜.*初测", "missing_hint": "厨房水电点位要等橱柜初步测量后再定，不然插座位置可能被柜子挡住"},
            ],
        },
        # --- 用户聊地板，但地暖还没确认 ---
        {
            "trigger": r"地板|木地板|实木|复合",
            "requires": [
                {"check": "decision:地暖|暖气|供暖", "missing_hint": "有没有地暖直接决定能选什么地板——有地暖的话纯实木基本排除，这个要先确认"},
            ],
        },
        # --- 用户聊软装，但硬装可能还没完 ---
        {
            "trigger": r"沙发|餐桌|窗帘|家具.*买|买.*家具",
            "requires": [
                {"check": "profile.preferred_styles", "missing_hint": "家具和软装最好跟整体风格统一，先定风格再选家具不容易翻车"},
            ],
        },
        {
            "trigger": r"窗帘|罗马杆|窗帘轨道",
            "requires": [
                {"check": "decision:吊顶|石膏线", "missing_hint": "窗帘的安装方式（轨道还是罗马杆）要在吊顶前确定，不然可能没有预留安装位置"},
            ],
        },
        # --- 用户聊入住，但关键验收可能没做 ---
        {
            "trigger": r"入住|搬家|搬进去|通风.*够",
            "requires": [
                {"check": "decision:验收|竣工.*检查", "missing_hint": "入住前建议做一次全屋验收，特别是水电、防水、门窗密封。搬进去之后再发现问题就很被动了"},
                {"check": "decision:甲醛.*检测|空气.*检测", "missing_hint": "入住前建议做一次甲醛检测，尤其是有小孩老人的家庭。通风至少3个月，别用网上的试纸，找专业机构"},
            ],
        },
        # --- 用户聊预算分配，但面积还不知道 ---
        {
            "trigger": r"预算.*分配|钱.*怎么分|花.*哪里|省.*哪里",
            "requires": [
                {"check": "profile.house_area", "missing_hint": "预算分配跟面积直接相关，知道面积才能算出合理的每平米造价"},
            ],
        },
        # --- 用户聊刷墙/油漆，但木工可能还没验收 ---
        {
            "trigger": r"刷墙|乳胶漆|墙漆|油漆工|腻子",
            "requires": [
                {"check": "decision:木工.*验收|吊顶.*验收", "missing_hint": "刷墙之前确认木工和吊顶已经验收合格，不然后期开裂很难分清是谁的问题"},
            ],
        },
    ]

    # === 阶段-待决策项映射（兜底：当话题依赖图没有触发时，按阶段提醒） ===
    STAGE_DECISION_CHECKLIST = {
        "准备": [
            {"item": "总预算", "profile_check": "budget_range", "hint": "确定总预算是第一步，后续所有选择都围绕预算展开"},
            {"item": "装修方式", "decision_keyword": "半包|全包|清包", "hint": "半包、全包还是清包？这决定了你需要操多少心"},
            {"item": "设计方案", "decision_keyword": "设计师|设计方案|平面图", "hint": "至少要有平面布局图和水电点位图再开工"},
        ],
        "设计": [
            {"item": "整体风格", "profile_check": "preferred_styles", "hint": "先定风格再选材料，否则容易买回来不搭"},
            {"item": "空间布局", "decision_keyword": "布局|格局|拆墙|改造", "hint": "布局改造要在水电之前确定，否则后期改动成本极高"},
            {"item": "水电点位", "decision_keyword": "水电点位|插座位置|开关位置", "hint": "水电点位要结合家具尺寸和生活习惯确定，这是最容易后悔的环节"},
        ],
        "施工": [
            {"item": "瓷砖选购", "decision_keyword": "瓷砖.*选|选.*瓷砖|瓷砖.*定|买.*瓷砖", "hint": "瓷砖要在瓦工进场前2周确定，否则耽误工期"},
            {"item": "地板选购", "decision_keyword": "地板.*选|选.*地板|地板.*定|买.*地板", "hint": "地板在油漆完工后铺设，但要提前选好预留安装时间"},
            {"item": "橱柜定制", "decision_keyword": "橱柜.*定|定.*橱柜|橱柜.*选", "hint": "橱柜需要在水电改造前初步测量，确定水电点位"},
            {"item": "卫浴选购", "decision_keyword": "马桶|花洒|浴室柜|卫浴.*选", "hint": "马桶坑距、花洒预埋要在贴砖前确认"},
        ],
        "软装": [
            {"item": "家具选购", "decision_keyword": "沙发|床|餐桌|家具.*选|买.*家具", "hint": "家具尺寸要和空间匹配，建议先量好再买"},
            {"item": "窗帘选购", "decision_keyword": "窗帘.*选|选.*窗帘|窗帘.*定", "hint": "窗帘轨道/罗马杆要在吊顶前确定安装方式"},
            {"item": "灯具选购", "decision_keyword": "灯.*选|选.*灯|吊灯|筒灯|灯具", "hint": "灯具要和整体风格统一，注意色温选择（3000-4000K居家最舒适）"},
        ],
    }

    def _build_proactive_guidance(self, profile, stage: str, user_message: str) -> Optional[str]:
        """
        基于用户当前消息内容 + profile 状态，主动提醒被忽略的前置依赖

        设计理念——冰山模型：
        - 平时不啰嗦（用户闲聊、打招呼时不触发）
        - 用户聊到具体话题时，检查该话题的前置依赖是否完成
        - 只提醒真正缺失的、跟当前话题直接相关的事项
        - 阶段 checklist 作为兜底，仅在话题依赖图未触发时使用

        触发优先级：
        1. 话题依赖图（用户聊什么 → 检查前置条件）—— 精准、自然
        2. 阶段 checklist（当前阶段有什么没做）—— 兜底、通用
        """
        import re
        if not user_message or len(user_message) < 2:
            return None

        extra = getattr(profile, 'extra_info', None) or {}
        decisions = extra.get("decisions", [])
        decision_texts = " ".join(d.get("text", "") for d in decisions)

        # === 第一优先级：话题依赖图 ===
        triggered_hints = []
        for rule in self.TOPIC_DEPENDENCY_GRAPH:
            if not re.search(rule["trigger"], user_message, re.IGNORECASE):
                continue
            # 话题命中，检查前置依赖
            for req in rule["requires"]:
                check = req["check"]
                satisfied = False

                if check.startswith("profile."):
                    # 检查 profile 字段
                    field_name = check.split(".", 1)[1]
                    value = getattr(profile, field_name, None)
                    if value:
                        satisfied = True
                elif check.startswith("decision:"):
                    # 检查已做决策记录
                    pattern = check.split(":", 1)[1]
                    if re.search(pattern, decision_texts, re.IGNORECASE):
                        satisfied = True

                if not satisfied:
                    triggered_hints.append(req["missing_hint"])

        if triggered_hints:
            # 去重并限制数量（最多2条，避免信息过载）
            seen = set()
            unique_hints = []
            for h in triggered_hints:
                if h not in seen:
                    seen.add(h)
                    unique_hints.append(h)
            unique_hints = unique_hints[:2]

            lines = ["【友情提醒——以下是跟用户当前话题相关的前置事项，如果用户还没做，请在回答中像朋友一样自然带一句，不要生硬罗列】"]
            for h in unique_hints:
                lines.append(f"- {h}")
            return "\n".join(lines)

        # === 第二优先级：阶段 checklist 兜底 ===
        if not stage or stage not in self.STAGE_DECISION_CHECKLIST:
            return None

        checklist = self.STAGE_DECISION_CHECKLIST[stage]
        pending_items = []
        for item_def in checklist:
            if "profile_check" in item_def:
                value = getattr(profile, item_def["profile_check"], None)
                if value:
                    continue
            if "decision_keyword" in item_def:
                if re.search(item_def["decision_keyword"], decision_texts, re.IGNORECASE):
                    continue
            pending_items.append(item_def)

        if not pending_items:
            return None

        top_pending = pending_items[:1]  # 兜底只提1个，保持克制
        lines = ["【阶段提醒——当前「" + stage + "」阶段有事项未确定，如果和用户话题相关可以自然提一句，不相关就不用提】"]
        for item in top_pending:
            lines.append(f"- {item['item']}：{item['hint']}")
        return "\n".join(lines)

    def _build_prompt_parts(self, context: Dict) -> tuple:
        """
        构建提示词的两个部分

        Returns:
            (system_prompt, supplementary_context)
            - system_prompt: 专家角色提示词 + 用户画像（直接写入system prompt确保LLM重视）
            - supplementary_context: 知识检索、工具结果等辅助信息（让LLM有数据可引用）
        """
        # === 确定系统身份提示词 ===
        if "expert_role" in context and context["expert_role"]:
            # 根据阶段上下文定制专家提示词
            if "stage_context" in context:
                stage_ctx = context["stage_context"]
                system_prompt = self.stage_reasoning.get_expert_system_prompt(
                    stage=stage_ctx.stage,
                    user_type=self.user_type,
                    context=stage_ctx,
                )
            else:
                system_prompt = context["expert_role"].system_prompt
        else:
            # 回退到子类的默认系统提示词
            system_prompt = self._get_system_prompt()
            if "{current_time}" in system_prompt:
                system_prompt = system_prompt.replace("{current_time}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            if "{context}" in system_prompt:
                system_prompt = system_prompt.split("{context}")[0]
            system_prompt = system_prompt.strip()

        # === 将用户画像直接注入 system prompt（确保 LLM 重视）===
        profile = context.get("_profile")
        if profile:
            profile_summary = self._build_profile_summary(profile)
            if profile_summary:
                system_prompt += (
                    f"\n\n## 当前用户信息（必须基于以下信息个性化回答，已知的不要再问）\n"
                    f"{profile_summary}"
                )

        # === 构建辅助上下文信息 ===
        parts = []

        # 避坑预警（匹配到危险模式时注入警告，让 LLM 在回答中自然提醒）
        user_message = context.get("_user_message", "")
        pitfall_warnings = self._check_pitfall_warnings(user_message)
        if pitfall_warnings:
            warnings_text = "\n".join(pitfall_warnings)
            parts.append(
                f"【避坑预警——请在回答中自然地融入以下提醒，语气像朋友善意提醒，不要生硬罗列】\n{warnings_text}"
            )

        # 主动引导未决策项（基于用户当前话题的依赖关系 + 阶段兜底）
        if profile:
            current_stage = None
            if "stage_context" in context:
                current_stage = context["stage_context"].stage
            elif profile.decoration_stage:
                current_stage = profile.decoration_stage
            proactive = self._build_proactive_guidance(profile, current_stage, user_message)
            if proactive:
                parts.append(proactive)

        # 阶段转换引导
        if "stage_transition" in context:
            transition = context["stage_transition"]
            if transition.transition_guidance:
                parts.append(f"【阶段转换提醒】\n{transition.transition_guidance}")

        # 阶段感知上下文
        if "stage_context" in context:
            stage_ctx = context["stage_context"]
            stage_parts = [f"当前装修阶段: {stage_ctx.stage}（置信度: {stage_ctx.stage_confidence:.0%}）"]
            if stage_ctx.deep_need:
                stage_parts.append(f"用户深层需求: {stage_ctx.deep_need}")
            if stage_ctx.potential_needs:
                stage_parts.append(f"潜在需求（用户没说但可能需要）: {', '.join(stage_ctx.potential_needs[:3])}")
            if stage_ctx.emotional_state and stage_ctx.emotional_state != "平静":
                stage_parts.append(f"用户情绪: {stage_ctx.emotional_state}")
            if stage_ctx.focus_points:
                stage_parts.append(f"关注重点: {', '.join(stage_ctx.focus_points)}")
            parts.append("\n".join(stage_parts))

        elif "decoration_stage" in context:
            stage_info = context["decoration_stage"]
            stage_text = f"当前装修阶段: {stage_info.get('current_stage', '未知')}"
            if stage_info.get("days_in_current_stage"):
                stage_text += f"（已进行{stage_info['days_in_current_stage']}天）"
            parts.append(stage_text)
            if stage_info.get("stage_tips"):
                parts.append(f"阶段注意事项: {'; '.join(stage_info['stage_tips'][:2])}")

        # 推断的需求
        if "inferred_need" in context:
            need = context["inferred_need"]
            parts.append(f"用户可能还需要: {need.get('suggestion', '')}（{need.get('reason', '')}）")

        # 工具计算结果（自然语言摘要，让LLM能引用具体数据）
        if "tool_results" in context and context["tool_results"]:
            tool_summary = self._format_tool_results(context["tool_results"])
            if tool_summary:
                parts.append(f"以下是根据用户情况计算的数据，请在回答中自然地引用这些数据：\n{tool_summary}")

        # 决策树推荐上下文（所有问题已回答，注入个性化推荐指令）
        if "decision_tree_recommendation" in context:
            parts.append(context["decision_tree_recommendation"])

        # 决策树引导问题（还有问题要问，让 LLM 在回答中自然引出）
        if "decision_tree_question" in context:
            dtq = context["decision_tree_question"]
            parts.append(
                f"【决策引导】请在回答中自然地引出以下问题（不要生硬地列选项，用对话的方式问）：\n"
                f"问题：{dtq['question']}\n"
                f"原因：{dtq['why']}\n"
                f"（选项会以快捷按钮形式展示给用户，你只需在回答中自然提到这个问题即可）"
            )

        # 知识检索结果
        if "knowledge" in context and context["knowledge"]:
            knowledge_text = "\n".join([
                f"- {doc['content'][:800]}"
                for doc in context["knowledge"][:5]
            ])
            parts.append(f"参考信息（请优先使用以下内容回答，不要编造）:\n{knowledge_text}")

        # 长期记忆（历史对话中的重要信息）
        if "memory" in context and context["memory"].get("long_term_memory"):
            lt_items = context["memory"]["long_term_memory"]
            if lt_items:
                lt_parts = []
                for item in lt_items[:3]:
                    content = item if isinstance(item, dict) else {}
                    if content.get("type") == "conversation":
                        lt_parts.append(
                            f"- 用户曾问：{content.get('user_message', '')[:80]}... "
                            f"→ 回答要点：{content.get('assistant_response', '')[:120]}..."
                        )
                    elif isinstance(content, dict) and content.get("summary"):
                        lt_parts.append(f"- {content['summary']}")
                if lt_parts:
                    parts.append(f"历史对话记忆（用户之前聊过的内容，可自然引用）:\n" + "\n".join(lt_parts))

        # 图片分析结果
        if "image_analysis" in context:
            img = context["image_analysis"]
            if "result" in img:
                parts.append(f"图片分析: {img['result'].get('description', '')}")

        supplementary_context = "\n\n".join(parts)
        return system_prompt, supplementary_context

    def _get_message_history(self, context: Dict) -> List:
        """获取消息历史"""
        history = []
        if "memory" in context and "short_term_memory" in context["memory"]:
            for item in context["memory"]["short_term_memory"][-5:]:
                if isinstance(item, dict):
                    if item.get("role") == "user":
                        history.append(HumanMessage(content=item.get("content", "")))
                    elif item.get("role") == "assistant":
                        history.append(AIMessage(content=item.get("content", "")))
        return history

    async def _update_memory(self, user_id: str, session_id: str,
                              message: str, chain: ReasoningChain,
                              assistant_response: str = None):
        """更新记忆"""
        # 记录交互
        self.memory.record_interaction(
            user_id=user_id,
            interaction_type="chat",
            content=message,
            metadata={
                "session_id": session_id,
                "reasoning_type": chain.reasoning_type.value,
            }
        )

        # 添加用户消息到短期记忆
        self.memory.add_to_short_term(
            session_id=session_id,
            content={"role": "user", "content": message},
            importance=0.5,
        )

        # 添加助手回复到短期记忆（确保对话历史完整）
        if assistant_response:
            self.memory.add_to_short_term(
                session_id=session_id,
                content={"role": "assistant", "content": assistant_response},
                importance=0.5,
            )

        # 将对话轮次写入长期记忆（跨会话知识沉淀）
        if assistant_response:
            # 计算重要性：包含具体信息的对话更重要
            importance = self._assess_conversation_importance(message, assistant_response)
            if importance >= 0.5:
                summary = message[:100]
                if len(message) > 100:
                    summary += "..."
                self.memory.add_to_long_term(
                    user_id=user_id,
                    content={
                        "type": "conversation",
                        "user_message": message,
                        "assistant_response": assistant_response[:500],
                        "summary": summary,
                        "session_id": session_id,
                    },
                    importance=importance,
                    metadata={
                        "user_id": user_id,
                        "session_id": session_id,
                        "reasoning_type": chain.reasoning_type.value,
                        "type": "conversation",
                    }
                )

        # 提取并更新用户兴趣
        interests = self._extract_interests(message)
        profile = self.memory.get_or_create_profile(user_id, self.user_type)
        for interest in interests:
            profile.update_interest(interest, 0.1)

        # 更新用户上下文（装修阶段、痛点等）
        await self._update_user_context(user_id, message)

    def _assess_conversation_importance(self, message: str, response: str) -> float:
        """
        评估对话轮次的重要性，决定是否写入长期记忆

        高重要性（>=0.7）：包含具体决策、数字、品牌、需求
        中重要性（0.5-0.7）：包含具体问题或有价值的回答
        低重要性（<0.5）：闲聊、打招呼、简单确认
        """
        import re
        score = 0.3  # 基础分

        # 包含具体数字（面积、预算、价格）
        if re.search(r'\d+(?:平米|㎡|万|元|块)', message):
            score += 0.2

        # 包含决策相关词汇
        decision_words = ["选了", "定了", "买了", "订了", "决定", "确认", "签了"]
        if any(w in message for w in decision_words):
            score += 0.3

        # 包含品牌名称
        brand_keywords = ["东鹏", "马可波罗", "诺贝尔", "大自然", "圣象", "索菲亚",
                         "欧派", "TOTO", "科勒", "方太", "老板", "立邦", "多乐士"]
        if any(b in message for b in brand_keywords):
            score += 0.15

        # 包含具体需求描述
        need_words = ["想要", "需要", "希望", "打算", "计划", "要求", "必须"]
        if any(w in message for w in need_words):
            score += 0.1

        # 消息长度较长通常包含更多信息
        if len(message) > 50:
            score += 0.1

        # 回答长度较长说明是有深度的回答
        if len(response) > 500:
            score += 0.1

        return min(1.0, score)

    # === 辅助方法 ===

    def _extract_amount(self, text: str, keyword: str = None) -> Optional[float]:
        """提取金额"""
        import re
        patterns = [
            r'(\d+(?:\.\d+)?)\s*[万w]',  # 万
            r'(\d+(?:\.\d+)?)\s*元',      # 元
            r'(\d+(?:\.\d+)?)\s*块',      # 块
            r'(\d+(?:,\d{3})*(?:\.\d+)?)', # 纯数字
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                amount = float(matches[0].replace(',', ''))
                if '万' in text or 'w' in text.lower():
                    amount *= 10000
                return amount
        return None

    def _extract_category(self, text: str) -> Optional[str]:
        """提取品类"""
        categories = ["家具", "建材", "家电", "软装", "智能家居"]
        for cat in categories:
            if cat in text:
                return cat
        return None

    def _extract_area(self, text: str) -> Optional[float]:
        """提取面积"""
        import re
        patterns = [
            r'(\d+(?:\.\d+)?)\s*[平㎡]',
            r'(\d+(?:\.\d+)?)\s*平米',
            r'(\d+(?:\.\d+)?)\s*平方',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                return float(matches[0])
        return None

    def _extract_interests(self, text: str) -> List[str]:
        """提取兴趣标签"""
        interest_keywords = {
            "装修风格": ["现代", "北欧", "中式", "轻奢", "简约", "工业风"],
            "材料": ["瓷砖", "地板", "乳胶漆", "壁纸", "大理石"],
            "家具": ["沙发", "床", "餐桌", "衣柜", "书桌"],
            "空间": ["客厅", "卧室", "厨房", "卫生间", "阳台"],
        }

        interests = []
        for category, keywords in interest_keywords.items():
            for kw in keywords:
                if kw in text:
                    interests.append(kw)
        return interests

    def _detect_decoration_stage(self, text: str) -> Optional[str]:
        """
        从用户消息中检测装修阶段

        Args:
            text: 用户消息

        Returns:
            检测到的装修阶段，如果无法检测则返回None
        """
        stage_keywords = {
            "准备": ["准备装修", "打算装修", "想装修", "要装修", "计划装修", "还没开始", "刚买房"],
            "设计": ["设计方案", "设计师", "效果图", "量房", "出图", "设计中", "在设计"],
            "施工": ["施工中", "在装修", "正在装", "水电", "贴砖", "刷漆", "吊顶", "工人"],
            "软装": ["软装", "买家具", "选家具", "窗帘", "灯具", "快完工", "硬装完"],
            "入住": ["入住", "搬家", "通风", "甲醛", "装完了", "已经装好"],
        }

        for stage, keywords in stage_keywords.items():
            for kw in keywords:
                if kw in text:
                    return stage

        return None

    def _detect_pain_points(self, text: str) -> List[Dict]:
        """
        从用户消息中检测痛点

        Args:
            text: 用户消息

        Returns:
            检测到的痛点列表
        """
        pain_patterns = {
            "预算": {
                "keywords": ["超预算", "预算不够", "太贵", "花太多", "控制预算", "省钱"],
                "severity": 0.8
            },
            "质量": {
                "keywords": ["质量差", "有问题", "不满意", "返工", "空鼓", "开裂", "漏水"],
                "severity": 0.9
            },
            "工期": {
                "keywords": ["太慢", "延期", "拖延", "什么时候完", "等太久"],
                "severity": 0.6
            },
            "选择困难": {
                "keywords": ["不知道选", "选哪个", "纠结", "怎么选", "哪个好"],
                "severity": 0.5
            },
            "沟通": {
                "keywords": ["沟通不畅", "不理人", "联系不上", "态度差"],
                "severity": 0.7
            },
        }

        detected = []
        for pain_type, config in pain_patterns.items():
            for kw in config["keywords"]:
                if kw in text:
                    detected.append({
                        "type": pain_type,
                        "description": f"用户提到: {kw}",
                        "severity": config["severity"]
                    })
                    break  # 每种类型只记录一次

        return detected

    async def _update_user_context(self, user_id: str, message: str):
        """
        根据用户消息更新用户上下文

        从对话中提取关键信息并回写到 UserProfile，包括：
        - 装修阶段
        - 痛点
        - 房屋面积、预算、风格偏好、家庭成员等核心信息
        """
        profile = self.memory.get_or_create_profile(user_id, self.user_type)

        # 检测装修阶段
        detected_stage = self._detect_decoration_stage(message)
        if detected_stage and detected_stage != profile.decoration_stage:
            profile.update_decoration_stage(detected_stage)

        # 检测痛点
        detected_pains = self._detect_pain_points(message)
        for pain in detected_pains:
            profile.record_pain_point(
                pain_type=pain["type"],
                description=pain["description"],
                severity=pain["severity"]
            )

        # 提取并回写核心信息（面积、预算、风格、家庭成员）
        self._extract_and_update_profile(profile, message)

        # 标记该用户的 profile 需要持久化
        if self.memory._profile_store:
            self.memory._profile_store._dirty_users.add(user_id)

    def _extract_and_update_profile(self, profile, message: str):
        """
        从用户消息中提取核心信息并回写到 UserProfile

        只在 profile 对应字段为空时才写入，避免覆盖已有数据。
        """
        import re

        # 提取房屋面积
        if not profile.house_area:
            area_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:平米|平方米|㎡|平方|平)',
                r'(?:面积|房子|房屋|新房).*?(\d+(?:\.\d+)?)',
            ]
            for pattern in area_patterns:
                m = re.search(pattern, message)
                if m:
                    area = float(m.group(1))
                    if 20 <= area <= 500:  # 合理面积范围
                        profile.house_area = area
                        logger.info(f"从对话提取房屋面积: {area}平米")
                        break

        # 提取预算
        if not profile.budget_range or profile.budget_range == (None, None):
            budget_patterns = [
                r'预算.*?(\d+(?:\.\d+)?)\s*[万w]',
                r'(\d+(?:\.\d+)?)\s*[万w].*?预算',
                r'(?:打算|准备|计划).*?花.*?(\d+(?:\.\d+)?)\s*[万w]',
                r'预算.*?(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*[万w]',
            ]
            for pattern in budget_patterns:
                m = re.search(pattern, message)
                if m:
                    groups = m.groups()
                    if len(groups) == 2 and groups[1]:
                        low = float(groups[0]) * 10000
                        high = float(groups[1]) * 10000
                    else:
                        val = float(groups[0]) * 10000
                        low = val * 0.8
                        high = val * 1.2
                    if 10000 <= high <= 5000000:  # 合理预算范围
                        profile.budget_range = (low, high)
                        logger.info(f"从对话提取预算: {low/10000:.0f}-{high/10000:.0f}万")
                        break

        # 提取风格偏好
        if not profile.preferred_styles:
            style_map = {
                "现代简约": ["现代简约", "简约", "现代风"],
                "北欧": ["北欧", "北欧风"],
                "新中式": ["新中式", "中式", "中国风"],
                "轻奢": ["轻奢", "轻奢风"],
                "日式": ["日式", "日式原木", "原木风", "muji"],
                "美式": ["美式", "美式风"],
                "法式": ["法式", "法式风"],
                "奶油风": ["奶油风", "奶油"],
                "侘寂": ["侘寂", "侘寂风"],
                "工业风": ["工业风", "工业"],
            }
            detected_styles = []
            for style_name, keywords in style_map.items():
                for kw in keywords:
                    if kw in message:
                        detected_styles.append(style_name)
                        break
            if detected_styles:
                profile.preferred_styles = detected_styles
                logger.info(f"从对话提取风格偏好: {detected_styles}")

        # 提取家庭成员信息
        if not hasattr(profile, 'extra_info') or profile.extra_info is None:
            profile.extra_info = {}
        family = profile.extra_info.setdefault("family_members", {})

        family_patterns = {
            "has_elderly": [r"老人", r"父母", r"爸妈", r"公婆", r"岳父"],
            "has_children": [r"孩子", r"小孩", r"宝宝", r"儿子", r"女儿", r"(\d+)\s*岁"],
            "has_pets": [r"猫", r"狗", r"宠物"],
        }
        for key, patterns in family_patterns.items():
            if not family.get(key):
                for p in patterns:
                    if re.search(p, message):
                        family[key] = True
                        logger.info(f"从对话提取家庭信息: {key}")
                        break

        # 提取品牌偏好（"邻居说东鹏不错"、"看了马可波罗"、"选了圣象"）
        brand_mentions = profile.extra_info.setdefault("brand_mentions", [])
        brand_keywords = [
            "东鹏", "马可波罗", "诺贝尔", "蒙娜丽莎", "冠珠",  # 瓷砖
            "大自然", "圣象", "德尔", "生活家", "安信",  # 地板
            "索菲亚", "欧派", "尚品宅配", "好莱客", "维意",  # 全屋定制
            "TOTO", "科勒", "箭牌", "九牧", "恒洁",  # 卫浴
            "方太", "老板", "华帝", "美的", "西门子",  # 厨电
            "立邦", "多乐士", "三棵树", "嘉宝莉",  # 涂料
            "公牛", "西蒙", "施耐德", "罗格朗",  # 开关
        ]
        for brand in brand_keywords:
            if brand in message:
                # 判断情感倾向
                sentiment = "neutral"
                positive_cues = ["不错", "好", "推荐", "选了", "定了", "喜欢", "满意", "靠谱"]
                negative_cues = ["差", "不好", "坑", "后悔", "不推荐", "别买", "垃圾"]
                context_window = message[max(0, message.index(brand)-10):message.index(brand)+len(brand)+15]
                for cue in positive_cues:
                    if cue in context_window:
                        sentiment = "positive"
                        break
                for cue in negative_cues:
                    if cue in context_window:
                        sentiment = "negative"
                        break
                # 避免重复记录同一品牌
                existing = [b["brand"] for b in brand_mentions]
                if brand not in existing:
                    brand_mentions.append({
                        "brand": brand,
                        "sentiment": sentiment,
                        "context": message[:80],
                        "timestamp": datetime.now().isoformat(),
                    })
                    logger.info(f"从对话提取品牌偏好: {brand} ({sentiment})")

        # 提取花费记录（"瓷砖花了1.5万"、"橱柜3万8"）
        spending = profile.extra_info.setdefault("spending", [])
        # 注意：避免单字品类（"门"、"床"）导致误匹配，至少 2 字
        spending_categories = [
            "瓷砖", "地砖", "墙砖", "地板", "橱柜", "衣柜", "全屋定制",
            "卫浴", "马桶", "花洒", "灯具", "窗帘", "沙发",
            "油烟机", "空调", "冰箱", "洗衣机", "热水器", "灶具",
            "乳胶漆", "涂料", "门窗", "窗户", "断桥铝", "家具", "家电",
            "水电", "防水", "设计费", "人工费", "拆改",
            "木门", "室内门", "入户门",
        ]
        for cat in spending_categories:
            if cat not in message:
                continue
            # 总价模式1: (品类)[非句界]{0,15}?(数字)万(数字)? — 支持 "3万8" = 38000
            # - 排除 ，。；等句界符号防止跨句匹配
            # - 非贪婪 {0,15}? 防止吞掉金额的一部分（如 1.5 中的 "1."）
            total_match = re.search(
                rf"{re.escape(cat)}[^，,。.；;\n]{{0,15}}?(\d+(?:\.\d+)?)\s*万(\d)?", message
            )
            if total_match:
                base = float(total_match.group(1)) * 10000
                trailing = total_match.group(2)
                amount = base + (int(trailing) * 1000 if trailing else 0)
                # 避免重复记录（同品类同金额）
                exists = any(
                    s.get("category") == cat and s.get("amount") == amount
                    for s in spending
                )
                if not exists:
                    spending.append({
                        "category": cat,
                        "amount": amount,
                        "is_total": True,
                        "timestamp": datetime.now().isoformat(),
                    })
                    logger.info(f"从对话提取花费: {cat} {amount}元")
                continue
            # 单价模式: (品类)[非句界]{0,15}?(数字)元/片|/平
            # 同样排除句界符号 + 非贪婪
            unit_match = re.search(
                rf"{re.escape(cat)}[^，,。.；;\n]{{0,15}}?(\d+(?:\.\d+)?)\s*元[/每](?:片|块|平|米|个)", message
            )
            if unit_match:
                amount = float(unit_match.group(1))
                exists = any(
                    s.get("category") == cat and s.get("amount") == amount and not s.get("is_total")
                    for s in spending
                )
                if not exists:
                    spending.append({
                        "category": cat,
                        "amount": amount,
                        "is_total": False,
                        "timestamp": datetime.now().isoformat(),
                    })
                    logger.info(f"从对话提取单价: {cat} {amount}元/单位")

        # 提取已做决策（"地板选了大自然"、"设计师定了"、"瓷砖买的东鹏"）
        decisions = profile.extra_info.setdefault("decisions", [])
        decision_patterns = [
            (r"(瓷砖|地板|橱柜|衣柜|沙发|马桶|花洒|热水器|空调|油烟机|灶具|洗碗机|门|窗帘|灯具|乳胶漆|壁纸|吊顶).*?(?:选了|定了|买了|订了|用的?|签了)\s*(.{2,10})", "item_decided"),
            (r"(?:选了|定了|买了|订了|用的?|签了)\s*(.{2,10}?)\s*(?:的|家的)?\s*(瓷砖|地板|橱柜|衣柜|沙发|马桶|花洒|热水器|空调|油烟机|灶具|洗碗机|门|窗帘|灯具|乳胶漆|壁纸|吊顶)", "brand_item_decided"),
            (r"(设计师|工长|装修公司|施工队).*?(?:定了|签了|找好了|选了)", "service_decided"),
            # 工序完成状态（"水电做完了"、"防水验收通过了"、"贴砖完了"）
            (r"(水电).*?(?:做完|改完|改好|验收|完工|做好)", "work_completed"),
            (r"(防水).*?(?:做好|做完|验收|通过)", "work_completed"),
            (r"(?:闭水|闭水试验).*?(?:通过|没问题|合格)", "work_completed"),
            (r"(贴砖|瓦工).*?(?:完了|做完|完工|验收)", "work_completed"),
            (r"(木工|吊顶).*?(?:完了|做完|完工|验收)", "work_completed"),
            (r"(刷墙|油漆|墙面).*?(?:完了|做完|完工|验收|刷好)", "work_completed"),
            (r"(安装|灯|门|地板|橱柜).*?(?:装好|装完|安装完|铺好)", "work_completed"),
        ]
        for pattern, dtype in decision_patterns:
            m = re.search(pattern, message)
            if m:
                decision_text = m.group(0)
                # 避免重复
                existing_decisions = [d["text"] for d in decisions]
                if decision_text not in existing_decisions:
                    decisions.append({
                        "text": decision_text,
                        "type": dtype,
                        "timestamp": datetime.now().isoformat(),
                    })
                    logger.info(f"从对话提取决策记录: {decision_text}")

    # === 工具调用接口 ===

    def call_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """调用工具"""
        return self.tools.call(tool_name, **kwargs)

    def get_available_tools(self) -> List[Dict]:
        """获取可用工具列表"""
        return self.tools.get_tools_for_llm()

    # === 记忆操作接口 ===

    def set_working_memory(self, session_id: str, key: str, value: Any):
        """设置工作记忆"""
        self.memory.set_working_memory(session_id, key, value)

    def get_working_memory(self, session_id: str, key: str) -> Any:
        """获取工作记忆"""
        return self.memory.get_working_memory(session_id, key)

    def get_user_profile(self, user_id: str) -> UserProfile:
        """获取用户画像"""
        return self.memory.get_or_create_profile(user_id, self.user_type)

    def update_user_profile(self, user_id: str, **kwargs):
        """更新用户画像"""
        self.memory.update_profile(user_id, **kwargs)

    # === 推理监控接口 ===

    def get_reasoning_statistics(self) -> Dict:
        """获取推理策略统计"""
        return self.adaptive_strategy.get_statistics()

    def record_user_feedback(self, query: str, reasoning_type: ReasoningType,
                             feedback_score: float):
        """
        记录用户反馈，用于优化推理策略

        Args:
            query: 原始查询
            reasoning_type: 使用的推理类型
            feedback_score: 用户反馈评分 (0-1)
        """
        self.adaptive_strategy.record_result(
            query=query,
            reasoning_type=reasoning_type,
            success=feedback_score >= 0.5,
            user_feedback=feedback_score
        )

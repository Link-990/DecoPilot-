"""
决策树引擎

装修的本质是一系列有依赖关系的决策。用户不知道决策顺序，
智能体根据已知信息自动判断下一个该问的问题，引导用户走正确的决策路径。

与现有系统的集成：
- StageAwareReasoning 检测到用户处于"选材"阶段 → 激活对应决策树
- UserProfile 中已有的信息自动填充 known_answers（不重复问）
- 决策树的 options 通过 OutputFormatter.quick_replies() 渲染为前端快捷按钮
"""
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from backend.core.logging_config import get_logger

logger = get_logger("decision_tree")


# ============================================================
# 数据结构
# ============================================================

@dataclass
class TreeNode:
    """决策树节点"""
    node_id: str
    question: str                          # 要问用户的问题
    options: List[str]                     # 可选答案
    affects: List[str]                     # 这个问题影响什么
    next_map: Dict[str, str]              # {答案: 下一个节点ID}，"COMPLETE"表示结束
    extract_from_profile: Optional[str] = None  # 可从 UserProfile 自动提取的字段名
    extract_keywords: Dict[str, List[str]] = field(default_factory=dict)  # {选项: [关键词]} 用于从对话中自动匹配

    def get_next(self, answer: str) -> str:
        """根据答案获取下一个节点"""
        if answer in self.next_map:
            return self.next_map[answer]
        if "_default" in self.next_map:
            return self.next_map["_default"]
        if "_all" in self.next_map:
            return self.next_map["_all"]
        return "COMPLETE"


@dataclass
class TreeQuestion:
    """决策树返回给用户的问题"""
    tree_id: str
    node_id: str
    question: str
    options: List[str]
    why: str                    # 为什么要问这个问题
    progress: float             # 决策进度 0-1
    total_nodes: int
    answered_nodes: int


@dataclass
class TreeRecommendation:
    """决策树收集完信息后的推荐上下文"""
    tree_id: str
    answers: Dict[str, str]
    recommendation_context: str   # 注入 LLM prompt 的推荐上下文
    key_factors: List[str]        # 影响推荐的关键因素


# ============================================================
# 决策树数据：瓷砖选购
# ============================================================

TILE_DECISION_TREE = {
    "id": "选材_瓷砖",
    "name": "瓷砖选购决策引导",
    "trigger_keywords": ["瓷砖", "地砖", "墙砖", "贴砖", "瓷片"],
    "root": "space_usage",
    "nodes": {
        "space_usage": TreeNode(
            node_id="space_usage",
            question="瓷砖用在哪个空间？不同空间对瓷砖的要求差别很大。",
            options=["客厅", "卫生间", "厨房", "阳台", "卧室", "全屋多个空间"],
            affects=["防滑等级", "吸水率", "规格推荐", "价格区间"],
            next_map={
                "客厅": "has_floor_heating",
                "卫生间": "bathroom_area",
                "厨房": "kitchen_wall_or_floor",
                "阳台": "balcony_usage",
                "卧室": "has_floor_heating",
                "全屋多个空间": "has_floor_heating",
            },
            extract_keywords={
                "客厅": ["客厅", "大厅"],
                "卫生间": ["卫生间", "厕所", "浴室", "洗手间"],
                "厨房": ["厨房"],
                "阳台": ["阳台"],
                "卧室": ["卧室", "房间"],
            },
        ),
        "bathroom_area": TreeNode(
            node_id="bathroom_area",
            question="卫生间是选墙砖还是地砖？还是都要选？",
            options=["地砖", "墙砖", "墙砖+地砖都要选"],
            affects=["防滑等级", "吸水率要求", "规格推荐"],
            next_map={"_all": "has_floor_heating"},
        ),
        "kitchen_wall_or_floor": TreeNode(
            node_id="kitchen_wall_or_floor",
            question="厨房是选墙砖还是地砖？",
            options=["地砖", "墙砖", "墙砖+地砖都要选"],
            affects=["耐油污性", "防滑等级"],
            next_map={"_all": "has_floor_heating"},
        ),
        "balcony_usage": TreeNode(
            node_id="balcony_usage",
            question="阳台主要用来做什么？这影响瓷砖的防水和防滑要求。",
            options=["晾衣服/洗衣机", "休闲区/茶室", "储物", "封闭阳台当书房"],
            affects=["防水等级", "防滑等级", "风格推荐"],
            next_map={"_all": "has_floor_heating"},
        ),
        "has_floor_heating": TreeNode(
            node_id="has_floor_heating",
            question="家里有地暖吗？地暖对瓷砖的导热性和膨胀系数有要求。",
            options=["有地暖", "没有地暖", "还没确定"],
            affects=["材质推荐", "厚度限制", "铺贴工艺"],
            next_map={"_all": "budget_level"},
            extract_keywords={
                "有地暖": ["地暖", "暖气", "供暖"],
                "没有地暖": ["没有地暖", "不装地暖"],
            },
        ),
        "budget_level": TreeNode(
            node_id="budget_level",
            question="这个空间的瓷砖预算大概多少？（每片价格）",
            options=[
                "经济型（30-80元/片）",
                "中档（80-200元/片）",
                "高端（200元以上/片）",
                "不确定，帮我推荐",
            ],
            affects=["品牌推荐", "产品系列推荐"],
            next_map={"_all": "style_preference"},
            extract_from_profile="budget_range",
        ),
        "style_preference": TreeNode(
            node_id="style_preference",
            question="偏好什么风格？这决定了瓷砖的花色和铺贴方式。",
            options=["现代简约", "奶油风/日式", "侘寂风/极简", "中式/新中式", "不确定"],
            affects=["花色推荐", "铺贴方式", "配色方案"],
            next_map={"_all": "family_situation"},
            extract_from_profile="preferred_styles",
            extract_keywords={
                "现代简约": ["现代", "简约", "简单"],
                "奶油风/日式": ["奶油", "日式", "原木", "暖色"],
                "侘寂风/极简": ["侘寂", "极简", "冷淡"],
                "中式/新中式": ["中式", "新中式", "国风"],
            },
        ),
        "family_situation": TreeNode(
            node_id="family_situation",
            question="家里有老人或小孩吗？这影响防滑和安全标准。",
            options=["有老人", "有小孩", "有老人和小孩", "都没有"],
            affects=["防滑等级要求", "安全标准"],
            next_map={"_all": "COMPLETE"},
            extract_keywords={
                "有老人": ["老人", "父母", "老年"],
                "有小孩": ["小孩", "孩子", "宝宝", "儿童"],
                "有老人和小孩": ["老人.*小孩", "小孩.*老人"],
            },
        ),
    },
}


# ============================================================
# 决策树数据：地板选购
# ============================================================

FLOORING_DECISION_TREE = {
    "id": "选材_地板",
    "name": "地板选购决策引导",
    "trigger_keywords": ["地板", "木地板", "实木", "复合地板"],
    "root": "has_floor_heating_floor",
    "nodes": {
        "has_floor_heating_floor": TreeNode(
            node_id="has_floor_heating_floor",
            question="家里有地暖吗？这是选地板的第一个关键因素——有地暖的话纯实木基本排除。",
            options=["有地暖", "没有地暖", "还没确定"],
            affects=["地板类型筛选", "材质限制"],
            next_map={"_all": "floor_space"},
            extract_keywords={
                "有地暖": ["地暖", "暖气", "供暖"],
                "没有地暖": ["没有地暖", "不装地暖"],
            },
        ),
        "floor_space": TreeNode(
            node_id="floor_space",
            question="地板铺在哪些空间？",
            options=["客厅+卧室", "只铺卧室", "全屋通铺", "客厅"],
            affects=["用量计算", "耐磨等级"],
            next_map={"_all": "floor_budget"},
        ),
        "floor_budget": TreeNode(
            node_id="floor_budget",
            question="地板的预算大概多少？（每平米价格）",
            options=[
                "经济型（60-150元/㎡）",
                "中档（150-400元/㎡）",
                "高端（400元以上/㎡）",
                "不确定",
            ],
            affects=["地板类型推荐", "品牌推荐"],
            next_map={"_all": "floor_feel"},
            extract_from_profile="budget_range",
        ),
        "floor_feel": TreeNode(
            node_id="floor_feel",
            question="更看重哪个方面？",
            options=["脚感舒适", "耐磨耐用", "环保健康", "性价比", "颜值好看"],
            affects=["地板类型推荐", "品牌推荐"],
            next_map={"_all": "floor_style"},
        ),
        "floor_style": TreeNode(
            node_id="floor_style",
            question="偏好什么风格的地板？",
            options=["浅色原木", "深色胡桃", "灰色系", "人字拼/鱼骨拼", "不确定"],
            affects=["花色推荐", "铺贴方式"],
            next_map={"_all": "COMPLETE"},
            extract_from_profile="preferred_styles",
        ),
    },
}


# ============================================================
# 决策树数据：施工验收
# ============================================================

INSPECTION_DECISION_TREE = {
    "id": "施工_验收",
    "name": "施工验收引导",
    "trigger_keywords": ["验收", "检查", "合不合格", "有没有问题", "空鼓"],
    "root": "inspection_stage",
    "nodes": {
        "inspection_stage": TreeNode(
            node_id="inspection_stage",
            question="要验收哪个施工环节？不同环节验收重点不同。",
            options=["水电验收", "防水验收", "瓦工验收（贴砖）", "木工验收", "油漆验收", "竣工验收"],
            affects=["验收标准", "检查工具", "常见问题"],
            next_map={"_all": "has_tools"},
        ),
        "has_tools": TreeNode(
            node_id="has_tools",
            question="手边有验收工具吗？",
            options=["有（空鼓锤、靠尺等）", "没有，用手机就行", "不知道需要什么工具"],
            affects=["验收方法推荐"],
            next_map={"_all": "who_inspects"},
        ),
        "who_inspects": TreeNode(
            node_id="who_inspects",
            question="谁来验收？",
            options=["自己验收", "请第三方监理", "装修公司自检"],
            affects=["验收深度", "注意事项"],
            next_map={"_all": "COMPLETE"},
        ),
    },
}


# ============================================================
# 决策树数据：全屋预算规划
# ============================================================

BUDGET_DECISION_TREE = {
    "id": "全屋_预算规划",
    "name": "全屋预算规划引导",
    "trigger_keywords": ["预算", "花多少钱", "多少钱装修", "预算规划", "预算分配"],
    "root": "house_area",
    "nodes": {
        "house_area": TreeNode(
            node_id="house_area",
            question="房子多大面积？这是预算计算的基础。",
            options=["60-80平", "80-100平", "100-120平", "120-150平", "150平以上"],
            affects=["总预算估算", "各项分配"],
            next_map={"_all": "budget_total"},
            extract_from_profile="house_area",
        ),
        "budget_total": TreeNode(
            node_id="budget_total",
            question="总预算大概多少？",
            options=[
                "10万以内",
                "10-20万",
                "20-30万",
                "30-50万",
                "50万以上",
                "还没想好",
            ],
            affects=["装修档次", "材料档次", "是否需要设计师"],
            next_map={"_all": "decoration_mode"},
            extract_from_profile="budget_range",
        ),
        "decoration_mode": TreeNode(
            node_id="decoration_mode",
            question="打算怎么装？这影响预算分配方式。",
            options=["半包（自己买主材）", "全包（全交给装修公司）", "还没决定"],
            affects=["预算分配比例", "时间精力投入"],
            next_map={"_all": "priority_items"},
        ),
        "priority_items": TreeNode(
            node_id="priority_items",
            question="有没有特别想花钱的地方？好钢用在刀刃上。",
            options=["厨房（做饭多）", "卫生间（舒适度）", "客厅（门面）", "卧室（睡眠）", "没有特别的"],
            affects=["预算倾斜方向"],
            next_map={"_all": "COMPLETE"},
        ),
    },
}


# ============================================================
# 所有决策树注册表
# ============================================================

ALL_TREES = {
    "选材_瓷砖": TILE_DECISION_TREE,
    "选材_地板": FLOORING_DECISION_TREE,
    "全屋_预算规划": BUDGET_DECISION_TREE,
    "施工_验收": INSPECTION_DECISION_TREE,
}


# ============================================================
# 决策树引擎
# ============================================================

class DecisionTreeEngine:
    """
    决策树引擎

    核心职责：
    1. 根据用户消息检测是否应该激活某棵决策树
    2. 根据已知答案（来自 UserProfile + 对话历史），跳过已知问题
    3. 返回下一个需要问的问题
    4. 所有信息收集完毕后，生成推荐上下文注入 LLM prompt
    """

    def __init__(self):
        self.trees = ALL_TREES
        # {user_id: {tree_id: {node_id: answer}}}
        self._sessions: Dict[str, Dict[str, Dict[str, str]]] = {}

    def detect_tree(self, message: str, stage: str = None) -> Optional[str]:
        """
        检测用户消息是否触发某棵决策树

        Args:
            message: 用户消息
            stage: 当前装修阶段（可选，用于优先匹配）

        Returns:
            匹配的 tree_id，或 None
        """
        message_lower = message.lower()
        best_match = None
        best_score = 0

        for tree_id, tree in self.trees.items():
            score = 0
            for kw in tree["trigger_keywords"]:
                if kw in message_lower:
                    score += 1

            # 阶段匹配加分
            if stage and tree_id.startswith(self._stage_to_prefix(stage)):
                score += 0.5

            if score > best_score:
                best_score = score
                best_match = tree_id

        return best_match if best_score > 0 else None

    def get_next_question(
        self,
        tree_id: str,
        user_id: str,
        profile=None,
        message: str = "",
    ) -> Optional[TreeQuestion]:
        """
        获取下一个需要问的问题

        自动跳过已知答案（来自 profile 或之前的对话）

        Args:
            tree_id: 决策树ID
            user_id: 用户ID
            profile: UserProfile 实例（可选，用于自动填充）
            message: 当前用户消息（用于尝试自动提取答案）

        Returns:
            TreeQuestion 或 None（所有问题已回答完毕）
        """
        tree = self.trees.get(tree_id)
        if not tree:
            return None

        nodes = tree["nodes"]
        known = self._get_answers(user_id, tree_id)

        # 尝试从当前消息中提取答案
        if message:
            self._try_extract_from_message(tree_id, nodes, known, message, user_id)

        # 尝试从 profile 中提取答案
        if profile:
            self._try_extract_from_profile(tree_id, nodes, known, profile)

        # 遍历决策树，找到第一个未回答的节点
        current = tree["root"]
        answered_count = 0
        total_count = len(nodes)

        while current != "COMPLETE":
            if current not in nodes:
                break

            node = nodes[current]

            if current in known:
                # 已有答案，跳到下一个
                answered_count += 1
                current = node.get_next(known[current])
            else:
                # 找到了未回答的问题
                return TreeQuestion(
                    tree_id=tree_id,
                    node_id=current,
                    question=node.question,
                    options=node.options,
                    why=f"这会影响：{'、'.join(node.affects)}",
                    progress=answered_count / total_count if total_count > 0 else 0,
                    total_nodes=total_count,
                    answered_nodes=answered_count,
                )

        return None  # 所有问题已回答

    def record_answer(self, user_id: str, tree_id: str, node_id: str, answer: str):
        """记录用户的回答"""
        if user_id not in self._sessions:
            self._sessions[user_id] = {}
        if tree_id not in self._sessions[user_id]:
            self._sessions[user_id][tree_id] = {}
        self._sessions[user_id][tree_id][node_id] = answer
        logger.info("记录决策树答案", extra={
            "user_id": user_id, "tree_id": tree_id,
            "node_id": node_id, "answer": answer,
        })

    def get_recommendation_context(self, tree_id: str, user_id: str) -> Optional[TreeRecommendation]:
        """
        将收集到的答案转化为 LLM 可用的推荐上下文

        只有当所有问题都回答完毕时才返回
        """
        tree = self.trees.get(tree_id)
        if not tree:
            return None

        known = self._get_answers(user_id, tree_id)
        nodes = tree["nodes"]

        # 检查是否所有路径上的问题都已回答
        current = tree["root"]
        path_answers = {}
        while current != "COMPLETE" and current in nodes:
            if current not in known:
                return None  # 还有未回答的问题
            path_answers[current] = known[current]
            current = nodes[current].get_next(known[current])

        # 生成推荐上下文
        context_parts = [f"【{tree['name']}——用户已确认的信息】"]
        key_factors = []

        for node_id, answer in path_answers.items():
            node = nodes[node_id]
            context_parts.append(f"- {node.question} → {answer}")
            key_factors.extend(node.affects)

        # 添加针对性的推荐指令
        context_parts.append("")
        context_parts.append("请根据以上用户确认的信息，给出具体的、个性化的推荐。")
        context_parts.append("不要再反问以上已确认的问题，直接给建议。")

        return TreeRecommendation(
            tree_id=tree_id,
            answers=path_answers,
            recommendation_context="\n".join(context_parts),
            key_factors=list(set(key_factors)),
        )

    def try_match_answer(self, tree_id: str, node_id: str, message: str) -> Optional[str]:
        """
        尝试从用户消息中匹配某个节点的答案

        Returns:
            匹配到的选项文本，或 None
        """
        tree = self.trees.get(tree_id)
        if not tree or node_id not in tree["nodes"]:
            return None

        node = tree["nodes"][node_id]

        # 精确匹配选项文本
        for option in node.options:
            if option in message:
                return option

        # 关键词匹配
        for option, keywords in node.extract_keywords.items():
            for kw in keywords:
                if re.search(kw, message):
                    return option

        return None

    # === 内部方法 ===

    def _get_answers(self, user_id: str, tree_id: str) -> Dict[str, str]:
        """获取用户在某棵树上的已知答案"""
        return self._sessions.get(user_id, {}).get(tree_id, {})

    def _try_extract_from_message(
        self, tree_id: str, nodes: Dict[str, TreeNode],
        known: Dict[str, str], message: str, user_id: str,
    ):
        """尝试从用户消息中提取答案"""
        for node_id, node in nodes.items():
            if node_id in known:
                continue
            matched = self.try_match_answer(tree_id, node_id, message)
            if matched:
                self.record_answer(user_id, tree_id, node_id, matched)
                known[node_id] = matched

    def _try_extract_from_profile(
        self, tree_id: str, nodes: Dict[str, TreeNode],
        known: Dict[str, str], profile,
    ):
        """尝试从 UserProfile 中提取答案"""
        for node_id, node in nodes.items():
            if node_id in known or not node.extract_from_profile:
                continue

            field_name = node.extract_from_profile
            value = getattr(profile, field_name, None)
            if not value:
                continue

            # 根据字段类型匹配选项
            if field_name == "house_area" and isinstance(value, (int, float)):
                for option in node.options:
                    nums = re.findall(r'\d+', option)
                    if len(nums) >= 2:
                        low, high = float(nums[0]), float(nums[1])
                        if low <= value <= high:
                            known[node_id] = option
                            break
                    elif len(nums) == 1 and "以上" in option:
                        if value >= float(nums[0]):
                            known[node_id] = option
                            break

            elif field_name == "budget_range" and isinstance(value, (tuple, list)):
                budget_high = value[1] if len(value) > 1 and value[1] else value[0]
                if budget_high:
                    budget_wan = budget_high / 10000
                    for option in node.options:
                        nums = re.findall(r'\d+', option)
                        if len(nums) >= 2:
                            low, high = float(nums[0]), float(nums[1])
                            if low <= budget_wan <= high:
                                known[node_id] = option
                                break
                        elif len(nums) == 1 and "以上" in option:
                            if budget_wan >= float(nums[0]):
                                known[node_id] = option
                                break

            elif field_name == "preferred_styles" and isinstance(value, list):
                for style in value:
                    for option in node.options:
                        if style in option or option in style:
                            known[node_id] = option
                            break

    def _stage_to_prefix(self, stage: str) -> str:
        """装修阶段映射到决策树前缀"""
        mapping = {
            "准备": "全屋",
            "设计": "全屋",
            "施工": "施工",
            "软装": "选材",
            "入住": "",
        }
        return mapping.get(stage, "")

    def clear_session(self, user_id: str, tree_id: str = None):
        """清除用户的决策树会话"""
        if user_id in self._sessions:
            if tree_id:
                self._sessions[user_id].pop(tree_id, None)
            else:
                del self._sessions[user_id]


# === Payload 解析 ===

def parse_decision_tree_payload(message: str) -> Optional[Tuple[str, str, str]]:
    """解析决策树快捷回复 payload（格式: dt:tree_id:node_id:answer）"""
    if not message or not message.startswith("dt:"):
        return None
    parts = message.split(":", 3)
    if len(parts) < 4:
        return None
    _, tree_id, node_id, answer = parts
    if not tree_id or not node_id or not answer:
        return None
    return tree_id, node_id, answer


# ============================================================
# 单例
# ============================================================

_engine_instance: Optional[DecisionTreeEngine] = None


def get_decision_tree_engine() -> DecisionTreeEngine:
    """获取决策树引擎单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DecisionTreeEngine()
    return _engine_instance

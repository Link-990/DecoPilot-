"""
用户装修档案 API 路由

提供智能体记忆中的用户画像数据，让用户看到"智能体记住了什么"，
并允许用户修正、补充这些信息。这是建立信任的基础设施。

注意：这里只暴露"用户档案"（我是谁），不暴露"装修看板"（项目到哪了）。
"""

import os
import re
import sys
import time
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.api.middleware.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["用户档案"])


# === 请求模型 ===

class UpdateProfileRequest(BaseModel):
    """用户可修改的档案字段"""
    city: Optional[str] = Field(default=None, max_length=50)
    house_area: Optional[float] = Field(default=None, ge=0, le=10000)
    budget_min: Optional[float] = Field(default=None, ge=0, description="万元")
    budget_max: Optional[float] = Field(default=None, ge=0, description="万元")
    preferred_styles: Optional[List[str]] = Field(default=None)
    has_children: Optional[bool] = Field(default=None)
    has_elderly: Optional[bool] = Field(default=None)
    has_pets: Optional[bool] = Field(default=None)


# === 装修待办事项（非线性，按用户实际讨论过的话题动态计算） ===
#
# 设计理念：
# - 不绑定固定阶段。用户可能从任何环节切入（已经在施工了才来咨询）
# - 只展示用户"当前关心的"或"必须知道的"待办，不做全量 checklist 轰炸
# - 触发逻辑：用户聊过相关话题 → 检查前置依赖是否完成 → 未完成的显示为待办
#   "always_relevant" 的基础项始终展示（预算/装修方式/风格）

RENOVATION_TODOS = [
    # --- 基础决策（always_relevant: 无论用户聊什么，这些没定都该提醒） ---
    {"item": "确定总预算", "category": "基础决策",
     "profile_check": "budget_range",
     "hint": "所有选择都围绕预算展开，建议留 10% 机动资金",
     "priority": 1, "always_relevant": True},
    {"item": "选择装修方式", "category": "基础决策",
     "decision_keyword": r"半包|全包|清包|装修方式.*定",
     "hint": "半包自己买主材省钱但操心，全包省心但要盯品牌型号写进合同",
     "priority": 1, "always_relevant": True},
    {"item": "确定整体风格", "category": "基础决策",
     "profile_check": "preferred_styles",
     "hint": "先定风格再选材，否则买回来容易不搭",
     "priority": 2, "always_relevant": True},
    {"item": "确定设计方案", "category": "基础决策",
     "decision_keyword": r"设计.*方案.*定|设计师.*定|平面图.*定|设计.*确认",
     "hint": "至少要有平面布局图和水电点位图再开工",
     "priority": 1, "always_relevant": True},

    # --- 工序（按用户讨论的话题触发，不假设线性顺序） ---
    {"item": "水电改造", "category": "工序",
     "decision_keyword": r"水电.*完|水电.*验收|水电.*做好|水电.*改好",
     "trigger_keywords": ["水电", "插座", "开关", "电线", "水管", "强电", "弱电", "橱柜"],
     "hint": "最重要的隐蔽工程，改完逐路验收并拍照留存管线走向",
     "priority": 1},
    {"item": "防水施工", "category": "工序",
     "decision_keyword": r"防水.*做好|防水.*完|闭水.*通过|防水.*验收",
     "trigger_keywords": ["防水", "闭水", "瓷砖", "地砖", "贴砖", "卫生间", "马桶", "花洒"],
     "hint": "卫生间/厨房/阳台必做，闭水试验 48 小时不渗漏才算过",
     "priority": 1},
    {"item": "瓦工贴砖", "category": "工序",
     "decision_keyword": r"贴砖.*完|瓦工.*完|砖.*贴好|瓦工.*验收",
     "trigger_keywords": ["瓷砖", "地砖", "墙砖", "贴砖", "瓦工", "美缝"],
     "hint": "空鼓率不超过 5%，十字缝对齐，阴阳角顺直",
     "priority": 2},
    {"item": "木工吊顶", "category": "工序",
     "decision_keyword": r"吊顶.*完|木工.*完|吊顶.*验收",
     "trigger_keywords": ["吊顶", "石膏板", "木工", "灯槽", "窗帘盒"],
     "hint": "吊顶前确认灯位、窗帘盒、中央空调/新风检修口",
     "priority": 2},
    {"item": "墙面施工", "category": "工序",
     "decision_keyword": r"刷墙.*完|油漆.*完|墙面.*完|油漆.*验收",
     "trigger_keywords": ["乳胶漆", "腻子", "油漆", "刷墙", "墙漆", "涂料", "墙面"],
     "hint": "腻子至少两遍干透再刮，阴阳角要顺直，色差要均匀",
     "priority": 2},

    # --- 选材（用户聊到相关品类时触发） ---
    {"item": "瓷砖选购", "category": "选材",
     "decision_keyword": r"瓷砖.*选|选.*瓷砖|瓷砖.*定|买.*瓷砖",
     "trigger_keywords": ["瓷砖", "地砖", "墙砖", "贴砖", "瓦工"],
     "hint": "瓦工进场前 2 周到位；注意吸水率、防滑等级、色差",
     "priority": 2},
    {"item": "地板选购", "category": "选材",
     "decision_keyword": r"地板.*选|选.*地板|地板.*定|买.*地板",
     "trigger_keywords": ["地板", "木地板", "实木", "复合地板", "SPC", "地暖"],
     "hint": "有地暖别选纯实木（热胀冷缩大），多层实木或 SPC 更稳定",
     "priority": 2},
    {"item": "橱柜定制", "category": "选材",
     "decision_keyword": r"橱柜.*定|定.*橱柜|橱柜.*选|橱柜.*签",
     "trigger_keywords": ["橱柜", "厨房", "台面", "水槽", "厨柜"],
     "hint": "水电前初测确定点位，工期 30-45 天，别等开工了才量",
     "priority": 1},
    {"item": "卫浴选购", "category": "选材",
     "decision_keyword": r"马桶.*选|花洒.*选|浴室柜.*选|卫浴.*定",
     "trigger_keywords": ["马桶", "花洒", "浴室柜", "卫浴", "淋浴", "浴缸"],
     "hint": "坑距/预埋件贴砖前确认，智能马桶要留电源",
     "priority": 2},
    {"item": "门窗选购", "category": "选材",
     "decision_keyword": r"门.*选|门.*定|窗.*选|窗.*定|门窗.*定|断桥铝.*定",
     "trigger_keywords": ["门", "窗户", "断桥铝", "门窗", "入户门", "室内门"],
     "hint": "门在油漆前装，断桥铝窗提前 1 个月下单（定制周期长）",
     "priority": 2},
    {"item": "灯具选购", "category": "选材",
     "decision_keyword": r"灯.*选|灯.*定|灯具.*买",
     "trigger_keywords": ["灯", "吊灯", "筒灯", "射灯", "灯具", "灯光", "色温"],
     "hint": "灯位水电阶段就要定，色温 3000-4000K 居家舒适",
     "priority": 3},
    {"item": "家具选购", "category": "选材",
     "decision_keyword": r"沙发.*选|床.*选|餐桌.*选|家具.*定|家具.*买",
     "trigger_keywords": ["沙发", "餐桌", "床", "茶几", "书桌", "电视柜", "家具"],
     "hint": "量好空间再买，注意动线和过道宽度（≥80cm）",
     "priority": 3},
    {"item": "窗帘选购", "category": "选材",
     "decision_keyword": r"窗帘.*选|选.*窗帘|窗帘.*定",
     "trigger_keywords": ["窗帘", "罗马杆", "窗帘轨道", "纱帘"],
     "hint": "轨道/罗马杆安装方式要在吊顶前确定",
     "priority": 3},

    # --- 验收（用户提到相关工序时触发） ---
    {"item": "水电验收", "category": "验收",
     "decision_keyword": r"水电.*验收.*过|水电.*检查.*过",
     "trigger_keywords": ["水电", "水电改造", "隐蔽工程", "验收"],
     "hint": "逐路打压/通电测试，拍照存档管线走向图",
     "priority": 1},
    {"item": "防水验收", "category": "验收",
     "decision_keyword": r"闭水.*通过|防水.*验收.*过",
     "trigger_keywords": ["防水", "闭水", "卫生间防水", "验收"],
     "hint": "48 小时闭水，去楼下确认无渗漏",
     "priority": 1},
    {"item": "竣工验收", "category": "验收",
     "decision_keyword": r"竣工.*验收|全屋.*验收|验收.*通过|装修.*验收",
     "trigger_keywords": ["竣工", "完工", "交付", "验收", "入住"],
     "hint": "水电/墙面/地面/门窗/五金逐项过，发现问题当场标记整改",
     "priority": 2},
]

# 用于给已做决策打分类标签
DECISION_CATEGORIES = {
    "瓷砖": ["瓷砖", "地砖", "墙砖"],
    "地板": ["地板", "木地板", "实木", "复合"],
    "橱柜": ["橱柜", "厨柜"],
    "卫浴": ["马桶", "花洒", "浴室柜", "淋浴"],
    "定制柜": ["衣柜", "全屋定制", "书柜", "鞋柜"],
    "涂料": ["乳胶漆", "涂料", "墙漆"],
    "门窗": ["门", "窗户", "断桥铝", "门窗"],
    "灯具": ["灯", "吊灯", "筒灯", "射灯", "灯具"],
    "家电": ["空调", "油烟机", "灶具", "洗碗机", "热水器", "冰箱", "洗衣机"],
    "家具": ["沙发", "餐桌", "床", "茶几"],
    "窗帘": ["窗帘"],
    "施工队": ["装修公司", "施工队", "工长"],
    "设计": ["设计师", "设计方案"],
}


def _categorize_decision(text: str) -> str:
    """给一条决策记录打上品类标签"""
    for category, keywords in DECISION_CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                return category
    return "其他"


def _compute_todos(profile) -> list:
    """
    根据用户实际讨论过的话题，动态计算待办事项。

    逻辑：
    1. always_relevant 的基础项 → 没做就显示
    2. 有 trigger_keywords 的项 → 用户聊过相关话题才显示，没做才显示
    3. 已完成的项不显示

    "聊过" = interests 里有、或 decisions 里提到、或 brand_mentions 里出现
    """
    extra = getattr(profile, 'extra_info', None) or {}
    decisions = extra.get("decisions", [])
    decision_texts = " ".join(d.get("text", "") for d in decisions)

    # 汇总用户讨论过的所有话题文本
    discussed_parts = []
    for topic in (profile.interests or {}):
        discussed_parts.append(topic)
    for d in decisions:
        discussed_parts.append(d.get("text", ""))
    for b in extra.get("brand_mentions", []):
        discussed_parts.append(b.get("brand", ""))
        discussed_parts.append(b.get("context", ""))
    discussed_text = " ".join(discussed_parts)

    todos = []
    for td in RENOVATION_TODOS:
        # 判断是否相关
        relevant = td.get("always_relevant", False)
        if not relevant:
            for kw in td.get("trigger_keywords", []):
                if kw in discussed_text:
                    relevant = True
                    break
        if not relevant:
            continue

        # 判断是否已完成
        done = False
        if "profile_check" in td:
            value = getattr(profile, td["profile_check"], None)
            if value:
                done = True
        if not done and "decision_keyword" in td:
            if re.search(td["decision_keyword"], decision_texts, re.IGNORECASE):
                done = True
        if done:
            continue

        todos.append({
            "item": td["item"],
            "category": td["category"],
            "hint": td["hint"],
            "priority": td.get("priority", 2),
        })

    todos.sort(key=lambda x: x["priority"])
    return todos


# === 序列化 ===

def _serialize_profile(profile) -> dict:
    """将 UserProfile 序列化为前端可用的 JSON"""
    extra = getattr(profile, 'extra_info', None) or {}
    family = extra.get("family_members", {})

    result = {
        "user_id": profile.user_id,
        "user_type": profile.user_type,
        "name": profile.name,
        "city": profile.city,
        "house_area": profile.house_area,
        "budget_range": None,
        "preferred_styles": profile.preferred_styles or [],
        "family": {
            "has_elderly": family.get("has_elderly", False),
            "has_children": family.get("has_children", False),
            "has_pets": family.get("has_pets", False),
        },
        "interests": dict(sorted(
            (profile.interests or {}).items(),
            key=lambda x: x[1], reverse=True
        )[:10]),
        "stats": {
            "total_sessions": profile.total_sessions,
            "total_messages": profile.total_messages,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        },
    }

    if profile.budget_range:
        low, high = profile.budget_range
        result["budget_range"] = {
            "min": low / 10000 if low else None,
            "max": high / 10000 if high else None,
        }

    # === renovation（我的装修）===
    raw_decisions = extra.get("decisions", [])
    enriched_decisions = []
    for d in raw_decisions:
        enriched_decisions.append({
            **d,
            "category": _categorize_decision(d.get("text", "")),
        })

    # === 花费追踪 ===
    raw_spending = extra.get("spending", [])
    # 按品类汇总花费（只统计 is_total=True 的总价记录）
    budget_spent = {}
    for s in raw_spending:
        if s.get("is_total"):
            cat = s.get("category", "其他")
            budget_spent[cat] = budget_spent.get(cat, 0) + s.get("amount", 0)
    budget_total_spent = sum(budget_spent.values())

    # === 工序进度（从 decisions 文本中正则匹配） ===
    # 注意：逐条检查每个 decision text，不要拼接后匹配，避免跨决策假阳性
    work_phases = [
        {"phase": "水电", "patterns": [r"水电.*完|水电.*验收|水电.*做好|水电.*改好"]},
        {"phase": "防水", "patterns": [r"防水.*做好|防水.*完|闭水.*通过|防水.*验收"]},
        {"phase": "瓦工", "patterns": [r"贴砖.*完|瓦工.*完|砖.*贴好|瓦工.*验收"]},
        {"phase": "木工", "patterns": [r"木工.*完|吊顶.*完|木工.*验收|吊顶.*验收"]},
        {"phase": "油漆", "patterns": [r"刷墙.*完|油漆.*完|墙面.*完|油漆.*验收|腻子.*完"]},
        {"phase": "安装", "patterns": [r"安装.*完|灯.*装好|门.*装好|地板.*铺好|橱柜.*装好"]},
    ]
    work_progress = []
    for wp in work_phases:
        completed = any(
            re.search(p, d.get("text", ""), re.IGNORECASE)
            for p in wp["patterns"]
            for d in raw_decisions
        )
        work_progress.append({
            "phase": wp["phase"],
            "completed": completed,
        })

    renovation = {
        "todos": _compute_todos(profile),
        "decisions": enriched_decisions,
        "brand_mentions": extra.get("brand_mentions", []),
        "spending": raw_spending,
        "budget_spent": budget_spent,
        "budget_total_spent": budget_total_spent,
        "work_progress": work_progress,
    }

    result["renovation"] = renovation
    return result


# === 端点 ===

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """获取当前用户的装修档案（智能体记忆中的画像数据）"""
    try:
        from backend.core.memory import get_memory_manager
        memory = get_memory_manager()
    except ImportError:
        raise HTTPException(status_code=503, detail="记忆系统不可用")

    user_id = current_user["user_id"]
    user_type = current_user.get("user_type", "c_end")

    profile = memory.get_or_create_profile(user_id, user_type)
    return _serialize_profile(profile)


@router.put("/me")
async def update_my_profile(req: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    """
    用户主动修正或补充档案信息

    这是"���解是显性的"原则的实现：用户看到智能体记住了什么，
    发现不对的可以改，缺的可以补。
    """
    try:
        from backend.core.memory import get_memory_manager
        memory = get_memory_manager()
    except ImportError:
        raise HTTPException(status_code=503, detail="记忆系统不可用")

    user_id = current_user["user_id"]
    user_type = current_user.get("user_type", "c_end")
    profile = memory.get_or_create_profile(user_id, user_type)

    changed = False

    if req.city is not None:
        profile.city = req.city
        changed = True

    if req.house_area is not None:
        profile.house_area = req.house_area
        changed = True

    if req.budget_min is not None or req.budget_max is not None:
        old_low, old_high = profile.budget_range or (0, 0)
        new_low = req.budget_min * 10000 if req.budget_min is not None else old_low
        new_high = req.budget_max * 10000 if req.budget_max is not None else old_high
        profile.budget_range = (new_low, new_high)
        changed = True

    if req.preferred_styles is not None:
        profile.preferred_styles = req.preferred_styles
        changed = True

    # 家庭成员
    if req.has_children is not None or req.has_elderly is not None or req.has_pets is not None:
        if not hasattr(profile, 'extra_info') or profile.extra_info is None:
            profile.extra_info = {}
        if "family_members" not in profile.extra_info:
            profile.extra_info["family_members"] = {}
        fm = profile.extra_info["family_members"]
        if req.has_children is not None:
            fm["has_children"] = req.has_children
        if req.has_elderly is not None:
            fm["has_elderly"] = req.has_elderly
        if req.has_pets is not None:
            fm["has_pets"] = req.has_pets
        changed = True

    if not changed:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    profile.updated_at = time.time()

    # 标记 dirty 以便持久化
    store = memory._profile_store
    if hasattr(store, '_dirty_users'):
        store._dirty_users.add(user_id)
    store.save_if_dirty()

    return _serialize_profile(profile)

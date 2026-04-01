# -*- coding: utf-8 -*-
"""
框架聊天 API 路由

使用新框架的智能体处理聊天请求
"""

import os
import sys
import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.framework.integration import (
    get_chat_adapter,
    FrameworkChatAdapter,
)
from backend.framework.integration.api_adapter import ChatContext
from backend.api.middleware.auth import get_current_user

router = APIRouter(prefix="/chat/v2", tags=["聊天V2"])


def _resolve_user_type(request_user_type: Optional[str], current_user: dict) -> str:
    token_type = current_user.get("user_type") if current_user else None
    if token_type in ("c_end", "b_end"):
        return token_type
    if token_type == "both" or token_type is None:
        return request_user_type or "c_end"
    return request_user_type or "c_end"


def _enforce_user_type(current_user: dict, allowed: set) -> None:
    token_type = current_user.get("user_type") if current_user else None
    if token_type in ("both", None):
        return
    if token_type not in allowed:
        raise HTTPException(status_code=403, detail="用户类型无权限访问该接口")


def _normalize_session_id(session_id: Optional[str], user_id: str) -> str:
    if session_id and session_id.startswith(f"{user_id}_"):
        return session_id
    return f"{user_id}_{uuid.uuid4().hex[:8]}"


class ChatRequestV2(BaseModel):
    """聊天请求模型 V2"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    user_type: Optional[str] = "c_end"
    enable_search: bool = True
    show_thinking: bool = True
    user_context: Optional[dict] = None


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str
    params: dict
    user_type: Optional[str] = "c_end"


# 延迟初始化适配器
_adapter: Optional[FrameworkChatAdapter] = None
_initialized = False


async def get_adapter() -> FrameworkChatAdapter:
    """获取并初始化适配器"""
    global _adapter, _initialized
    if _adapter is None:
        _adapter = get_chat_adapter()
    if not _initialized:
        await _adapter.initialize()
        _initialized = True
    return _adapter


@router.post("/stream")
async def chat_stream_v2(request: ChatRequestV2, current_user: dict = Depends(get_current_user)):
    """
    流式聊天接口 V2

    使用新框架的智能体处理请求
    """
    adapter = await get_adapter()

    # 构建上下文
    user_type = _resolve_user_type(request.user_type, current_user)
    context = ChatContext(
        session_id=_normalize_session_id(request.session_id, current_user.get("user_id")),
        user_id=current_user.get("user_id"),
        user_type=user_type,
        enable_search=request.enable_search,
        show_thinking=request.show_thinking,
        user_context=request.user_context,
    )

    async def event_generator():
        async for event in adapter.chat_stream(request.message, context):
            yield event

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.post("/c-end")
async def chat_c_end_v2(request: ChatRequestV2, current_user: dict = Depends(get_current_user)):
    """
    C端专用聊天接口 V2

    面向业主用户，提供装修咨询、补贴政策、商家推荐等服务
    """
    _enforce_user_type(current_user, {"c_end"})
    request.user_type = "c_end"
    return await chat_stream_v2(request, current_user)


@router.post("/b-end")
async def chat_b_end_v2(request: ChatRequestV2, current_user: dict = Depends(get_current_user)):
    """
    B端专用聊天接口 V2

    面向商家用户，提供入驻指导、数据产品咨询、获客策略等服务
    """
    _enforce_user_type(current_user, {"b_end"})
    request.user_type = "b_end"
    return await chat_stream_v2(request, current_user)


@router.post("/sync")
async def chat_sync(request: ChatRequestV2, current_user: dict = Depends(get_current_user)):
    """
    非流式聊天接口

    返回完整的响应，适合不需要流式输出的场景
    """
    adapter = await get_adapter()

    # 构建上下文
    user_type = _resolve_user_type(request.user_type, current_user)
    context = ChatContext(
        session_id=_normalize_session_id(request.session_id, current_user.get("user_id")),
        user_id=current_user.get("user_id"),
        user_type=user_type,
        enable_search=request.enable_search,
        show_thinking=request.show_thinking,
        user_context=request.user_context,
    )

    result = await adapter.chat(request.message, context)
    return result


@router.post("/tool")
async def call_tool(request: ToolCallRequest, current_user: dict = Depends(get_current_user)):
    """
    工具调用接口

    直接调用智能体的工具
    """
    adapter = await get_adapter()

    user_type = _resolve_user_type(request.user_type, current_user)
    result = await adapter.call_tool(
        tool_name=request.tool_name,
        params=request.params,
        user_type=user_type,
    )

    return result


@router.get("/tools")
async def list_tools(user_type: str = "c_end", current_user: dict = Depends(get_current_user)):
    """
    列出可用工具

    返回指定用户类型的智能体可用的工具列表
    """
    adapter = await get_adapter()

    # 获取智能体
    effective_user_type = _resolve_user_type(user_type, current_user)
    agent = await adapter._get_agent(effective_user_type)

    # 获取工具列表
    tools = agent.list_tools()

    return {
        "user_type": effective_user_type,
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                    }
                    for p in t.parameters
                ],
            }
            for t in tools
        ],
    }


@router.get("/health")
async def health_check():
    """
    健康检查

    检查框架组件状态
    """
    try:
        adapter = await get_adapter()

        return {
            "status": "healthy",
            "framework_version": "2.0.0",
            "adapter_initialized": _initialized,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }

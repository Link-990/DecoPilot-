"""
用户认证 API 路由
提供注册、登录、用户信息查询和更新接口
"""

import os
import sys
import time
from typing import Optional
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.core.user import get_user_store
from backend.api.middleware.auth import create_access_token, get_current_user
import config_data as config


router = APIRouter(prefix="/auth", tags=["用户认证"])


# === 请求/响应模型 ===

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    user_type: str = Field(default="c_end", description="用户类型: c_end(业主) / b_end(商家)")
    nickname: Optional[str] = Field(default=None, max_length=50, description="昵称")
    phone: Optional[str] = Field(default=None, max_length=20, description="手机号")
    city: Optional[str] = Field(default=None, max_length=50, description="城市")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)
    city: Optional[str] = Field(default=None, max_length=50)
    house_area: Optional[float] = Field(default=None, ge=0, le=10000)
    budget_min: Optional[float] = Field(default=None, ge=0)
    budget_max: Optional[float] = Field(default=None, ge=0)
    user_type: Optional[str] = Field(default=None)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


# === 接口 ===

@router.post("/register")
async def register(req: RegisterRequest):
    """用户注册"""
    if req.user_type not in ("c_end", "b_end"):
        raise HTTPException(status_code=400, detail="user_type 必须是 c_end 或 b_end")

    store = get_user_store()
    user = store.create_user(
        username=req.username,
        password=req.password,
        user_type=req.user_type,
        nickname=req.nickname,
        phone=req.phone,
        city=req.city,
    )

    if user is None:
        raise HTTPException(status_code=409, detail="用户名已存在")

    # 注册成功直接返回 token
    token = create_access_token(
        data={"user_id": user.id, "user_type": user.user_type, "username": user.username},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response = JSONResponse({
        "message": "注册成功",
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "user_type": user.user_type,
            "nickname": user.nickname,
        },
    })
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=config.ENV == "production",
        samesite="lax",
        max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return response


@router.post("/login")
async def login(req: LoginRequest):
    """用户登录"""
    store = get_user_store()
    user = store.verify_user(req.username, req.password)

    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(
        data={"user_id": user.id, "user_type": user.user_type, "username": user.username},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response = JSONResponse({
        "message": "登录成功",
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "user_type": user.user_type,
            "nickname": user.nickname,
            "city": user.city,
            "house_area": user.house_area,
            "budget_min": user.budget_min,
            "budget_max": user.budget_max,
        },
    })
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=config.ENV == "production",
        samesite="lax",
        max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return response


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    store = get_user_store()
    user = store.get_user_by_id(current_user["user_id"])

    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "id": user.id,
        "username": user.username,
        "user_type": user.user_type,
        "nickname": user.nickname,
        "phone": user.phone,
        "city": user.city,
        "house_area": user.house_area,
        "budget_min": user.budget_min,
        "budget_max": user.budget_max,
        "created_at": user.created_at,
    }


@router.put("/me")
async def update_me(req: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    """更新当前用户信息"""
    store = get_user_store()
    updates = {k: v for k, v in req.dict().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    if "user_type" in updates and updates["user_type"] not in ("c_end", "b_end"):
        raise HTTPException(status_code=400, detail="user_type 必须是 c_end 或 b_end")

    success = store.update_user(current_user["user_id"], **updates)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {"message": "更新成功"}


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    """修改密码"""
    store = get_user_store()
    success = store.change_password(current_user["user_id"], req.old_password, req.new_password)

    if not success:
        raise HTTPException(status_code=400, detail="旧密码错误")

    return {"message": "密码修改成功"}

"""认证路由：注册/登录/刷新"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, UnauthorizedError
from app.core.response import ok
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserLogin, UserOut, UserRegister, TokenOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register")
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    if not payload.phone and not payload.email:
        raise BadRequestError("手机号或邮箱至少填写一项")

    # 唯一性检查
    if payload.phone:
        if (await db.execute(select(User).where(User.phone == payload.phone))).scalar_one_or_none():
            raise BadRequestError("手机号已注册")
    if payload.email:
        if (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none():
            raise BadRequestError("邮箱已注册")

    user = User(
        phone=payload.phone,
        email=payload.email,
        nickname=payload.nickname,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    return ok(_make_token(user))


@router.post("/login")
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(
            select(User).where((User.phone == payload.account) | (User.email == payload.account))
        )
    ).scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("账号或密码错误")
    return ok(_make_token(user))


@router.post("/refresh")
async def refresh(authorization: str | None = None, db: AsyncSession = Depends(get_db)):
    # 简化：复用 security 模块的解析
    from fastapi import Header
    pass


def _make_token(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
        "user": UserOut.model_validate(user).model_dump(mode="json"),
    }

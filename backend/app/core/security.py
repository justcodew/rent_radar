"""认证：JWT + bcrypt"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.errors import UnauthorizedError
from app.database import get_db
from app.models.user import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(user_id: UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc)
        + timedelta(days=settings.JWT_REFRESH_TTL_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("登录已过期")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("无效的 Token")


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError()
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedError()

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("用户不存在")
    return user

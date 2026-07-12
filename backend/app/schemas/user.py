"""用户相关 schema"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    phone: str | None = None
    email: str | None = None
    nickname: str | None = None
    password: str = Field(min_length=6, max_length=64)


class UserLogin(BaseModel):
    account: str  # 手机号或邮箱
    password: str


class UserOut(BaseModel):
    id: UUID
    phone: str | None
    email: str | None
    nickname: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut

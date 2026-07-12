"""统一响应封装"""
from typing import Any, Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None
    trace_id: Optional[str] = None


def ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


def fail(code: int = 500, message: str = "error", data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data}

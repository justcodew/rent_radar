"""通用 schema"""
from typing import Any, Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


class Pagination(BaseModel):
    total: int
    page: int
    page_size: int
    has_more: bool

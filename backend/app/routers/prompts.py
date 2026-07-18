"""提示词管理路由

获取/修改各 LLM 功能的 system/user prompt。
用户可在前端查看和自定义提示词。
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.response import ok

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


class PromptUpdate(BaseModel):
    system: str | None = None
    user_template: str | None = None


@router.get("/community")
async def get_community_prompts():
    """获取小区测评的提示词"""
    from app.services.scoring.community_insights import get_prompts, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT_TEMPLATE
    current = get_prompts()
    return ok({
        "system": current["system"],
        "user_template": current["user_template"],
        "default_system": DEFAULT_SYSTEM_PROMPT,
        "default_user_template": DEFAULT_USER_PROMPT_TEMPLATE,
        "is_custom": current["is_custom"],
    })


@router.put("/community")
async def update_community_prompts(req: PromptUpdate):
    """修改小区测评的提示词(传空字符串或 null 恢复默认)"""
    from app.services.scoring.community_insights import set_prompts
    set_prompts(system=req.system, user=req.user_template)
    return ok({"message": "提示词已更新"})


@router.post("/community/reset")
async def reset_community_prompts():
    """恢复默认提示词"""
    from app.services.scoring.community_insights import set_prompts
    set_prompts(system=None, user=None)
    return ok({"message": "已恢复默认提示词"})

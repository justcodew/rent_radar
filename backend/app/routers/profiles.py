"""需求画像路由"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.response import ok
from app.core.security import get_current_user
from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileCreate, ProfileOut, ProfileUpdate

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


@router.post("")
async def create_profile(
    payload: ProfileCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = Profile(user_id=user.id, **payload.model_dump())
    db.add(profile)
    await db.flush()
    return ok(ProfileOut.model_validate(profile).model_dump(mode="json"))


@router.get("")
async def list_profiles(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == user.id).order_by(Profile.created_at.desc())
    )
    profiles = result.scalars().all()
    return ok([ProfileOut.model_validate(p).model_dump(mode="json") for p in profiles])


@router.get("/{profile_id}")
async def get_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_owned(db, profile_id, user.id)
    return ok(ProfileOut.model_validate(profile).model_dump(mode="json"))


@router.put("/{profile_id}")
async def update_profile(
    profile_id: UUID,
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_owned(db, profile_id, user.id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(profile, k, v)
    await db.flush()
    return ok(ProfileOut.model_validate(profile).model_dump(mode="json"))


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_owned(db, profile_id, user.id)
    await db.delete(profile)
    return ok({"deleted": str(profile_id)})


async def _get_owned(db: AsyncSession, profile_id: UUID, user_id: UUID) -> Profile:
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    p = result.scalar_one_or_none()
    if not p or p.user_id != user_id:
        raise NotFoundError("画像不存在")
    return p

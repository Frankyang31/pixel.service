"""
账户路由
GET    /api/v1/account           获取账户信息
PUT    /api/v1/account           更新个人资料
GET    /api/v1/account/credits   获取积分信息
GET    /api/v1/account/credits/transactions  积分流水
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.core.auth.dependencies import get_current_user
from app.db.database import get_db
from app.models.points import PointsAccount, PointsTransaction
from app.models.user import User
from app.schemas.auth import UserProfileResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(tags=["账户"])


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    locale: Optional[str] = None


class CreditsResponse(BaseModel):
    balance: float
    frozen_balance: float
    total_earned: float
    total_spent: float


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    balance_before: float
    balance_after: float
    source: str
    reference_id: Optional[str] = None
    remark: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=UserProfileResponse)
async def get_account(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户账户信息"""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        phone=current_user.phone,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        locale=current_user.locale,
        membership_level=current_user.membership_level,
        membership_expires_at=(
            current_user.membership_expires_at.isoformat()
            if current_user.membership_expires_at else None
        ),
        is_email_verified=current_user.is_email_verified,
        created_at=current_user.created_at.isoformat(),
    )


@router.put("", response_model=UserProfileResponse)
async def update_account(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新个人资料"""
    if body.nickname is not None:
        current_user.nickname = body.nickname
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url
    if body.locale is not None:
        current_user.locale = body.locale
    await db.commit()
    return await get_account(current_user)


@router.get("/credits", response_model=CreditsResponse)
async def get_credits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取积分余额信息"""
    account = await db.scalar(
        select(PointsAccount).where(PointsAccount.user_id == current_user.id)
    )
    if account is None:
        return CreditsResponse(balance=0, frozen_balance=0, total_earned=0, total_spent=0)

    return CreditsResponse(
        balance=float(account.balance),
        frozen_balance=float(account.frozen_balance),
        total_earned=float(account.total_earned),
        total_spent=float(account.total_spent),
    )


@router.get("/credits/transactions")
async def get_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取积分流水记录"""
    base_q = select(PointsTransaction).where(PointsTransaction.user_id == current_user.id)
    total = await db.scalar(
        select(func.count()).select_from(base_q.subquery())
    ) or 0

    txs = (await db.scalars(
        base_q.order_by(PointsTransaction.created_at.desc())
               .offset((page - 1) * page_size)
               .limit(page_size)
    )).all()

    items = [
        TransactionResponse(
            id=tx.id,
            type=tx.type,
            amount=float(tx.amount),
            balance_before=float(tx.balance_before),
            balance_after=float(tx.balance_after),
            source=tx.source,
            reference_id=tx.reference_id,
            remark=tx.remark,
            created_at=tx.created_at.isoformat(),
        )
        for tx in txs
    ]
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)

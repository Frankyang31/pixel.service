"""
积分服务
处理积分冻结、确认、退款、流水查询，带三重幂等性保障
"""

from __future__ import annotations

from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.monitoring.logging import get_logger
from app.models.points import PointsAccount, PointsTransaction
from app.utils.exceptions import (
    ConcurrentModificationError,
    InsufficientCreditsError,
    NotFoundError,
)

logger = get_logger(__name__)


async def get_or_create_account(db: AsyncSession, user_id: str) -> PointsAccount:
    """获取用户积分账户，不存在则自动创建"""
    account = await db.scalar(
        select(PointsAccount).where(PointsAccount.user_id == user_id)
    )
    if account is None:
        account = PointsAccount(user_id=user_id, balance=Decimal("0"))
        db.add(account)
        await db.flush()
    return account


async def earn_credits(
    db: AsyncSession,
    user_id: str,
    amount: Decimal,
    source: str,
    transaction_id: str,
    reference_id: str | None = None,
    reference_type: str | None = None,
    remark: str | None = None,
) -> None:
    """
    发放积分（注册奖励、签到、购买套餐等）
    带幂等检查，相同 transaction_id 重复调用安全
    """
    # 幂等检查
    existing = await db.scalar(
        select(PointsTransaction).where(
            PointsTransaction.transaction_id == transaction_id
        )
    )
    if existing:
        logger.info("earn_credits_idempotent_skip", transaction_id=transaction_id)
        return

    account = await get_or_create_account(db, user_id)

    await db.execute(
        update(PointsAccount)
        .where(PointsAccount.user_id == user_id)
        .values(
            balance=PointsAccount.balance + amount,
            total_earned=PointsAccount.total_earned + amount,
            version=PointsAccount.version + 1,
        )
    )

    db.add(PointsTransaction(
        user_id=user_id,
        transaction_id=transaction_id,
        type="EARN",
        amount=amount,
        balance_before=account.balance,
        balance_after=account.balance + amount,
        source=source,
        reference_id=reference_id,
        reference_type=reference_type,
        remark=remark,
    ))

    logger.info("earn_credits", user_id=user_id, amount=str(amount), source=source)


async def freeze_for_job(
    db: AsyncSession,
    redis: Redis,
    user_id: str,
    job_id: str,
    amount: Decimal,
) -> None:
    """
    预扣积分（任务提交时调用）
    三重幂等性：分布式锁 + 幂等键 + 数据库事务
    整个流程在单一数据库事务内完成
    """
    lock_key = f"lock:points:{user_id}"
    transaction_id = f"FREEZE:{job_id}"

    # 1. 获取分布式锁（序列化同一用户的并发操作）
    async with redis.lock(lock_key, timeout=30, blocking_timeout=5):
        async with db.begin_nested():  # savepoint，在外层事务中
            # 2. 幂等检查
            existing = await db.scalar(
                select(PointsTransaction).where(
                    PointsTransaction.transaction_id == transaction_id
                )
            )
            if existing:
                return

            # 3. 加行锁查询账户
            account = await db.scalar(
                select(PointsAccount)
                .where(PointsAccount.user_id == user_id)
                .with_for_update()
            )
            if account is None:
                raise NotFoundError("积分账户不存在")
            if account.balance < amount:
                raise InsufficientCreditsError(
                    current=float(account.balance),
                    required=float(amount)
                )

            # 4. 更新余额（乐观锁版本号）
            result = await db.execute(
                update(PointsAccount)
                .where(
                    PointsAccount.user_id == user_id,
                    PointsAccount.version == account.version,
                )
                .values(
                    balance=account.balance - amount,
                    frozen_balance=account.frozen_balance + amount,
                    version=account.version + 1,
                )
            )
            if result.rowcount == 0:
                raise ConcurrentModificationError("积分账户并发冲突，请重试")

            # 5. 写流水
            db.add(PointsTransaction(
                user_id=user_id,
                transaction_id=transaction_id,
                type="FREEZE",
                amount=amount,
                balance_before=account.balance,
                balance_after=account.balance - amount,
                source="API_CALL",
                reference_id=job_id,
                reference_type="job",
            ))

    logger.info("credits_frozen", user_id=user_id, job_id=job_id, amount=str(amount))


async def confirm_freeze(
    db: AsyncSession,
    user_id: str,
    job_id: str,
    actual_amount: Decimal,
) -> None:
    """
    确认扣费（任务完成后调用）
    将冻结积分转为实际消耗，超出部分退还
    """
    freeze_tx = await db.scalar(
        select(PointsTransaction).where(
            PointsTransaction.transaction_id == f"FREEZE:{job_id}"
        )
    )
    if freeze_tx is None:
        logger.warning("confirm_freeze_no_freeze_tx", job_id=job_id)
        return

    frozen_amount = freeze_tx.amount
    refund_amount = frozen_amount - actual_amount

    confirm_tx_id = f"SPEND:{job_id}"
    # 幂等检查
    if await db.scalar(
        select(PointsTransaction).where(
            PointsTransaction.transaction_id == confirm_tx_id
        )
    ):
        return

    account = await db.scalar(
        select(PointsAccount)
        .where(PointsAccount.user_id == user_id)
        .with_for_update()
    )
    if account is None:
        return

    await db.execute(
        update(PointsAccount)
        .where(PointsAccount.user_id == user_id)
        .values(
            frozen_balance=account.frozen_balance - frozen_amount,
            total_spent=account.total_spent + actual_amount,
            # 如果有退款，余额加回来
            balance=account.balance + refund_amount if refund_amount > 0 else account.balance,
            version=PointsAccount.version + 1,
        )
    )

    db.add(PointsTransaction(
        user_id=user_id,
        transaction_id=confirm_tx_id,
        type="SPEND",
        amount=actual_amount,
        balance_before=account.balance,
        balance_after=account.balance + refund_amount,
        source="API_CALL",
        reference_id=job_id,
        reference_type="job",
    ))

    if refund_amount > 0:
        db.add(PointsTransaction(
            user_id=user_id,
            transaction_id=f"UNFREEZE:{job_id}",
            type="UNFREEZE",
            amount=refund_amount,
            balance_before=account.balance,
            balance_after=account.balance + refund_amount,
            source="REFUND",
            reference_id=job_id,
            reference_type="job",
            remark="任务完成，退还多冻结积分",
        ))

    logger.info(
        "credits_confirmed",
        user_id=user_id, job_id=job_id,
        frozen=str(frozen_amount), actual=str(actual_amount), refund=str(refund_amount)
    )


async def refund_for_failed_job(
    db: AsyncSession,
    user_id: str,
    job_id: str,
) -> None:
    """任务失败时退还全部冻结积分"""
    freeze_tx = await db.scalar(
        select(PointsTransaction).where(
            PointsTransaction.transaction_id == f"FREEZE:{job_id}"
        )
    )
    if freeze_tx is None:
        return

    refund_tx_id = f"REFUND:{job_id}"
    if await db.scalar(
        select(PointsTransaction).where(
            PointsTransaction.transaction_id == refund_tx_id
        )
    ):
        return  # 已退还

    account = await db.scalar(
        select(PointsAccount)
        .where(PointsAccount.user_id == user_id)
        .with_for_update()
    )
    if account is None:
        return

    refund_amount = freeze_tx.amount
    await db.execute(
        update(PointsAccount)
        .where(PointsAccount.user_id == user_id)
        .values(
            frozen_balance=account.frozen_balance - refund_amount,
            balance=account.balance + refund_amount,
            version=PointsAccount.version + 1,
        )
    )

    db.add(PointsTransaction(
        user_id=user_id,
        transaction_id=refund_tx_id,
        type="REFUND",
        amount=refund_amount,
        balance_before=account.balance,
        balance_after=account.balance + refund_amount,
        source="REFUND",
        reference_id=job_id,
        reference_type="job",
        remark="任务失败，退还冻结积分",
    ))

    logger.info("credits_refunded", user_id=user_id, job_id=job_id, amount=str(refund_amount))

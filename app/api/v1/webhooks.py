"""
Webhook 路由
POST /webhooks/wechat-pay   微信支付回调
POST /webhooks/stripe       Stripe 支付回调
"""

from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache.redis_client import get_redis
from app.core.monitoring.logging import get_logger
from app.db.database import get_db
from app.models.order import MembershipOrder
from app.models.user import User

router = APIRouter(tags=["Webhook"])
logger = get_logger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/wechat-pay")
async def wechat_pay_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    微信支付 V3 回调
    幂等保障：Redis nx + 数据库事务
    """
    body = await request.body()

    # 1. 验签（简化版，生产使用 wechatpayv3 SDK）
    # TODO: 引入 wechatpayv3 库完整验签
    # wechat_signature = request.headers.get("Wechatpay-Signature")
    # if not verify_wechat_signature(request.headers, body, settings.WECHAT_PAY_API_V3_KEY):
    #     raise HTTPException(400, "签名验证失败")

    try:
        import json
        payload = json.loads(body)
    except Exception:
        raise HTTPException(400, "无效的请求体")

    payment_order_id = payload.get("out_trade_no")
    if not payment_order_id:
        return {"code": "SUCCESS"}

    # 2. 幂等锁
    idempotency_key = f"pay:done:{payment_order_id}"
    if not await redis.set(idempotency_key, "1", nx=True, ex=3600):
        logger.info("wechat_pay_callback_duplicate", order_id=payment_order_id)
        return {"code": "SUCCESS"}

    # 3. 处理支付成功
    try:
        await _process_payment_success(
            db=db,
            payment_order_id=payment_order_id,
            third_party_tx_id=payload.get("transaction_id", ""),
        )
    except Exception as e:
        logger.error("wechat_pay_callback_error", order_id=payment_order_id, error=str(e))
        # 删除幂等锁，允许微信重试
        await redis.delete(idempotency_key)
        raise HTTPException(500, "处理回调失败")

    return {"code": "SUCCESS"}


@router.post("/stripe")
async def stripe_callback(
    request: Request,
    stripe_signature: str = Header(alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Stripe Webhook 回调"""
    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Stripe 签名验证失败")

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        payment_intent_id = payment_intent["id"]

        # 幂等锁
        idempotency_key = f"stripe:done:{payment_intent_id}"
        if not await redis.set(idempotency_key, "1", nx=True, ex=3600):
            return {"received": True}

        # 查 metadata 中的我方订单号
        payment_order_id = payment_intent.get("metadata", {}).get("order_id")
        if payment_order_id:
            try:
                await _process_payment_success(
                    db=db,
                    payment_order_id=payment_order_id,
                    third_party_tx_id=payment_intent_id,
                )
            except Exception as e:
                logger.error("stripe_callback_error", error=str(e))
                await redis.delete(idempotency_key)
                raise HTTPException(500, "处理回调失败")

    return {"received": True}


async def _process_payment_success(
    db: AsyncSession,
    payment_order_id: str,
    third_party_tx_id: str,
) -> None:
    """
    支付成功处理（事务内）：
    1. 更新订单状态 paid
    2. 发放积分
    3. 更新用户会员等级和过期时间
    """
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.services.points_service import earn_credits

    order = await db.scalar(
        select(MembershipOrder).where(MembershipOrder.payment_order_id == payment_order_id)
    )
    if order is None or order.status == "paid":
        return

    async with db.begin():
        order.status = "paid"
        order.paid_at = datetime.now(tz=timezone.utc)

        # 发放积分
        await earn_credits(
            db=db,
            user_id=order.user_id,
            amount=order.credits_granted,
            source="MEMBERSHIP",
            transaction_id=f"MEMBERSHIP:{order.id}",
            reference_id=order.id,
            reference_type="order",
            remark=f"购买 {order.plan_name} 套餐赠送积分",
        )

        # 更新用户会员等级
        user = await db.get(User, order.user_id)
        if user:
            user.membership_level = order.membership_level
            now = datetime.now(tz=timezone.utc)
            if user.membership_expires_at and user.membership_expires_at > now:
                # 叠加（续费）
                user.membership_expires_at += timedelta(days=order.membership_days)
            else:
                user.membership_expires_at = now + timedelta(days=order.membership_days)

    logger.info(
        "payment_processed",
        order_id=order.id, user_id=order.user_id,
        credits=str(order.credits_granted), plan=order.plan_id
    )

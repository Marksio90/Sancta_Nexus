"""Stripe billing — subskrypcje Sancta Nexus.

Endpointy:
  POST /billing/checkout   → Stripe Checkout session (redirect URL)
  POST /billing/portal     → Stripe Customer Portal (zarządzanie subskrypcją)
  POST /billing/webhook    → Stripe webhook (signature verified, no JWT)
  GET  /billing/status     → aktualny status subskrypcji dla zalogowanego

Tiers:
  free     → UserRole.USER           (domyślny)
  pilgrim  → UserRole.PREMIUM_USER   (miesięczny)
  disciple → UserRole.PREMIUM_USER   (roczny, tańszy)

Webhook obsługuje:
  checkout.session.completed        → aktywuje premium
  customer.subscription.updated     → synchronizuje status
  customer.subscription.deleted     → cofa premium
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import DbSession
from app.core.rbac import require_authenticated
from app.models.database import Subscription, SubscriptionTier, User, UserRole

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Tier → rola ───────────────────────────────────────────────────────────────

_TIER_ROLE: dict[SubscriptionTier, UserRole] = {
    SubscriptionTier.FREE: UserRole.USER,
    SubscriptionTier.PILGRIM: UserRole.PREMIUM_USER,
    SubscriptionTier.DISCIPLE: UserRole.PREMIUM_USER,
    SubscriptionTier.MYSTIC: UserRole.PREMIUM_USER,
}

_PRICE_TIER: dict[str, SubscriptionTier] = {
    settings.STRIPE_PRICE_ID_MONTHLY: SubscriptionTier.PILGRIM,
    settings.STRIPE_PRICE_ID_YEARLY: SubscriptionTier.DISCIPLE,
}


def _stripe():
    """Lazy import stripe — nie blokuje startu gdy klucz jest pusty."""
    try:
        import stripe as _s
        _s.api_key = settings.STRIPE_SECRET_KEY
        return _s
    except ImportError as err:
        raise HTTPException(status_code=503, detail="Stripe SDK nie jest zainstalowane.") from err


def _stripe_enabled() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_subscription(db, user_id: str) -> Subscription:
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(user_id=user_id, status="free", tier=SubscriptionTier.FREE)
        db.add(sub)
        await db.flush()
    return sub


async def _activate_premium(
    db,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    stripe_price_id: str,
    period_end_ts: int | None,
) -> None:
    """Aktywuje premium po płatności — aktualizuje Subscription i User.role."""
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        logger.warning("Webhook: brak subskrypcji dla customer=%s", stripe_customer_id)
        return

    tier = _PRICE_TIER.get(stripe_price_id, SubscriptionTier.PILGRIM)
    sub.stripe_subscription_id = stripe_subscription_id
    sub.stripe_price_id = stripe_price_id
    sub.tier = tier
    sub.status = "active"
    sub.cancel_at_period_end = False
    if period_end_ts:
        sub.current_period_end = datetime.fromtimestamp(period_end_ts, tz=UTC)

    user_result = await db.execute(select(User).where(User.id == sub.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.role = _TIER_ROLE[tier]
        user.subscription_tier = tier

    logger.info("Premium aktywowany: user=%s tier=%s", sub.user_id, tier.value)


async def _deactivate_premium(db, stripe_subscription_id: str) -> None:
    """Cofa premium po anulowaniu/wygaśnięciu."""
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    sub.status = "canceled"
    sub.tier = SubscriptionTier.FREE
    sub.stripe_subscription_id = None

    user_result = await db.execute(select(User).where(User.id == sub.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.role = UserRole.USER
        user.subscription_tier = SubscriptionTier.FREE

    logger.info("Premium cofnięty: user=%s", sub.user_id)


# ── Schematy ──────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    price_id: str  # STRIPE_PRICE_ID_MONTHLY lub STRIPE_PRICE_ID_YEARLY


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionStatus(BaseModel):
    tier: str
    status: str
    cancel_at_period_end: bool
    current_period_end: str | None
    is_premium: bool


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutResponse, summary="Utwórz sesję Stripe Checkout")
async def create_checkout(
    body: CheckoutRequest,
    db: DbSession,
    current_user: User = require_authenticated,
) -> CheckoutResponse:
    """Tworzy Stripe Checkout session i zwraca URL do przekierowania."""
    if not _stripe_enabled():
        raise HTTPException(status_code=503, detail="Płatności nie są skonfigurowane.")

    allowed = {settings.STRIPE_PRICE_ID_MONTHLY, settings.STRIPE_PRICE_ID_YEARLY}
    if body.price_id not in allowed:
        raise HTTPException(status_code=400, detail="Nieprawidłowy plan.")

    stripe = _stripe()
    sub = await _get_or_create_subscription(db, current_user.id)

    # Utwórz lub pobierz klienta Stripe
    if not sub.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": current_user.id},
        )
        sub.stripe_customer_id = customer["id"]
        await db.flush()

    session = stripe.checkout.Session.create(
        customer=sub.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": body.price_id, "quantity": 1}],
        success_url=f"{settings.FRONTEND_URL}/konto?checkout=success",
        cancel_url=f"{settings.FRONTEND_URL}/cennik?checkout=canceled",
        allow_promotion_codes=True,
        metadata={"user_id": current_user.id},
    )
    return CheckoutResponse(checkout_url=session["url"])


@router.post("/portal", response_model=PortalResponse, summary="Otwórz Stripe Customer Portal")
async def create_portal(
    db: DbSession,
    current_user: User = require_authenticated,
) -> PortalResponse:
    """Otwiera portal klienta Stripe do zarządzania subskrypcją / fakturami."""
    if not _stripe_enabled():
        raise HTTPException(status_code=503, detail="Płatności nie są skonfigurowane.")

    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Brak aktywnej subskrypcji Stripe.")

    stripe = _stripe()
    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=f"{settings.FRONTEND_URL}/konto",
    )
    return PortalResponse(portal_url=session["url"])


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook (bez JWT — weryfikacja podpisem)",
    include_in_schema=False,
)
async def stripe_webhook(request: Request, db: DbSession) -> dict:
    """Webhook Stripe — obsługuje zdarzenia subskrypcji.

    Weryfikacja: nagłówek Stripe-Signature + STRIPE_WEBHOOK_SECRET.
    """
    if not _stripe_enabled():
        return {"ok": True}

    stripe = _stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError as err:
        raise HTTPException(status_code=400, detail="Nieprawidłowy podpis webhooka.") from err
    except Exception as exc:
        logger.error("Webhook parse error: %s", exc)
        raise HTTPException(status_code=400, detail="Błąd parsowania eventu.") from exc

    etype = event["type"]
    data = event["data"]["object"]

    if etype == "checkout.session.completed":
        # Pobierz subskrypcję Stripe żeby uzyskać price_id i period_end
        stripe_sub_id = data.get("subscription")
        customer_id = data.get("customer")
        if stripe_sub_id and customer_id:
            try:
                stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
                price_id = stripe_sub["items"]["data"][0]["price"]["id"]
                period_end = stripe_sub.get("current_period_end")
                await _activate_premium(db, customer_id, stripe_sub_id, price_id, period_end)
            except Exception as exc:
                logger.error("Webhook activate error: %s", exc)

    elif etype == "customer.subscription.updated":
        stripe_sub_id = data.get("id")
        customer_id = data.get("customer")
        sub_status = data.get("status", "")
        cancel_at = data.get("cancel_at_period_end", False)
        period_end = data.get("current_period_end")

        if sub_status in ("active", "trialing"):
            price_id = data["items"]["data"][0]["price"]["id"]
            await _activate_premium(db, customer_id, stripe_sub_id, price_id, period_end)
            # Synchronizuj cancel_at_period_end
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.cancel_at_period_end = cancel_at
        elif sub_status in ("canceled", "unpaid", "past_due"):
            await _deactivate_premium(db, stripe_sub_id)

    elif etype == "customer.subscription.deleted":
        stripe_sub_id = data.get("id")
        if stripe_sub_id:
            await _deactivate_premium(db, stripe_sub_id)

    return {"ok": True}


@router.get("/status", response_model=SubscriptionStatus, summary="Status subskrypcji")
async def get_status(
    db: DbSession,
    current_user: User = require_authenticated,
) -> SubscriptionStatus:
    """Zwraca aktualny plan i status subskrypcji zalogowanego użytkownika."""
    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()

    if not sub:
        return SubscriptionStatus(
            tier=SubscriptionTier.FREE.value,
            status="free",
            cancel_at_period_end=False,
            current_period_end=None,
            is_premium=False,
        )

    is_premium = sub.tier != SubscriptionTier.FREE and sub.status in ("active", "trialing")
    period_end_str = (
        sub.current_period_end.isoformat() if sub.current_period_end else None
    )
    return SubscriptionStatus(
        tier=sub.tier.value,
        status=sub.status,
        cancel_at_period_end=sub.cancel_at_period_end,
        current_period_end=period_end_str,
        is_premium=is_premium,
    )

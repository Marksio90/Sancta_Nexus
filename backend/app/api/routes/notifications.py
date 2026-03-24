"""Notification API routes.

Endpoints
---------
GET  /vapid-public-key
    Return the VAPID public key so the browser can subscribe.

POST /subscribe
    Register a Web Push subscription (browser PushManager output).

POST /device-token
    Register a native Capacitor FCM/APNs device token.

POST /test
    Send a test notification to the caller's subscription (dev only).

DELETE /unsubscribe
    Remove a subscription by endpoint URL.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.notifications.push_service import (
    PushNotificationService,
    PushSubscription,
    PushPayload,
    push_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory subscription store (replace with DB in production) ─────────────
# In production, persist these in PostgreSQL with user_id + endpoint as PK.
_subscriptions: dict[str, PushSubscription] = {}
_device_tokens: list[dict] = []


# ── Schemas ───────────────────────────────────────────────────────────────────


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: dict[str, str]  # {"p256dh": "...", "auth": "..."}


class DeviceTokenRequest(BaseModel):
    token: str
    platform: str  # "capacitor" | "web"
    user_id: str | None = None


class TestNotificationRequest(BaseModel):
    endpoint: str
    title: str = "Sancta Nexus — test"
    body: str = "Powiadomienia działają ✓"


class UnsubscribeRequest(BaseModel):
    endpoint: str


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/vapid-public-key", summary="Get VAPID public key")
async def get_vapid_public_key() -> dict[str, str]:
    """Return the VAPID public key required to create a push subscription."""
    if not push_service.public_key:
        raise HTTPException(
            status_code=503,
            detail="Push notifications not configured (VAPID_PUBLIC_KEY missing)",
        )
    return {"publicKey": push_service.public_key}


@router.post("/subscribe", summary="Register push subscription")
async def subscribe(body: SubscribeRequest) -> dict[str, str]:
    """Store a Web Push subscription for future prayer reminders."""
    p256dh = body.keys.get("p256dh", "")
    auth = body.keys.get("auth", "")

    if not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Missing subscription keys")

    _subscriptions[body.endpoint] = PushSubscription(
        endpoint=body.endpoint,
        p256dh=p256dh,
        auth=auth,
    )
    logger.info("New push subscription registered (total: %d)", len(_subscriptions))
    return {"status": "subscribed"}


@router.post("/device-token", summary="Register native device token (FCM/APNs)")
async def register_device_token(body: DeviceTokenRequest) -> dict[str, str]:
    """Store a Capacitor FCM / APNs device token for native push."""
    _device_tokens.append(
        {
            "token": body.token,
            "platform": body.platform,
            "user_id": body.user_id,
            "registered_at": datetime.utcnow().isoformat(),
        }
    )
    logger.info("Device token registered: platform=%s", body.platform)
    return {"status": "registered"}


@router.post("/test", summary="Send test notification")
async def send_test(body: TestNotificationRequest) -> dict[str, object]:
    """Send a test notification to verify the subscription works."""
    sub = _subscriptions.get(body.endpoint)
    if not sub:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found — subscribe first",
        )

    payload = PushPayload(title=body.title, body=body.body)
    success = await push_service.send(sub, payload)

    if not success:
        raise HTTPException(
            status_code=503,
            detail="Push delivery failed — check VAPID configuration",
        )
    return {"status": "sent"}


@router.delete("/unsubscribe", summary="Remove push subscription")
async def unsubscribe(body: UnsubscribeRequest) -> dict[str, str]:
    """Remove a subscription by endpoint URL."""
    removed = _subscriptions.pop(body.endpoint, None)
    if not removed:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"status": "unsubscribed"}


@router.get("/stats", summary="Subscription statistics (admin)")
async def stats() -> dict[str, int]:
    return {
        "web_subscriptions": len(_subscriptions),
        "device_tokens": len(_device_tokens),
    }

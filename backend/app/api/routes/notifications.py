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


@router.post("/daily-reminder", summary="Ustaw/aktualizuj codzienne powiadomienie poranne")
async def set_daily_reminder(request: Request) -> dict[str, str]:
    """Rejestruje preferencje codziennego przypomnienia.

    Przechowuje endpoint + czas powiadomienia w pamięci.
    W produkcji: zapisać do Redis/DB z TTL i harmonogramem (Celery beat / APScheduler).
    """
    try:
        data = await request.json()
        endpoint = data.get("endpoint", "")
        preferred_time = data.get("time", "07:00")  # format HH:MM

        if not endpoint:
            raise HTTPException(status_code=400, detail="Brak endpoint'u subskrypcji.")

        # Walidacja formatu czasu
        parts = preferred_time.split(":")
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            raise HTTPException(status_code=400, detail="Nieprawidłowy format czasu (HH:MM).")

        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise HTTPException(status_code=400, detail="Czas poza zakresem.")

        # Zapisz preferencję (in-memory; w prod → Redis HSET)
        if endpoint in _subscriptions:
            # Przechowaj czas jako atrybut runtime — nie modyfikujemy modelu
            _subscriptions[endpoint].__dict__["_reminder_time"] = preferred_time

        return {"status": "ok", "time": preferred_time}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("daily-reminder error: %s", exc)
        raise HTTPException(status_code=500, detail="Błąd ustawiania przypomnienia.")


@router.post("/send-morning", summary="Wyślij poranne powiadomienie (cron/scheduler)")
async def send_morning_notifications() -> dict[str, int]:
    """Wyślij poranne powiadomienia do wszystkich subskrybentów.

    Docelowo wywoływany przez cron job o 07:00 (lub przez APScheduler).
    W tej wersji wysyła do wszystkich aktywnych subskrypcji.
    """
    from app.services.scripture.saints_calendar import get_saint_today
    from datetime import date

    saint = get_saint_today(date.today())
    payload = PushPayload(
        title=f"Dzień dobry! {saint['icon']} {saint['name']}",
        body=f"Módlmy się dzisiaj przez wstawiennictwo patrona dnia. Niech Pan błogosławi Twój dzień!",
        icon="/icons/icon-192x192.png",
        url="/dzisiaj",
    )

    sent = 0
    dead_endpoints: list[str] = []
    for endpoint, sub in list(_subscriptions.items()):
        try:
            await push_service.send(sub, payload)
            sent += 1
        except Exception:
            dead_endpoints.append(endpoint)

    for ep in dead_endpoints:
        _subscriptions.pop(ep, None)

    return {"sent": sent, "removed_dead": len(dead_endpoints)}


@router.get("/stats", summary="Subscription statistics (admin)")
async def stats() -> dict[str, int]:
    return {
        "web_subscriptions": len(_subscriptions),
        "device_tokens": len(_device_tokens),
    }

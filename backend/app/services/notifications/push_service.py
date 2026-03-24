"""Web Push Notification service using VAPID (pywebpush).

Sends personalised prayer reminders to subscribed browsers and
native Capacitor apps (via FCM device tokens when available).

Configuration (required in .env):
    VAPID_PRIVATE_KEY   — base64url-encoded EC private key
    VAPID_PUBLIC_KEY    — base64url-encoded EC public key (sent to browser)
    VAPID_CLAIMS_EMAIL  — e.g. "mailto:admin@sanctanexus.org"

Generate VAPID keys (run once):
    python -c "
    from py_vapid import Vapid
    v = Vapid()
    v.generate_keys()
    v.save_key('vapid_private.pem')
    v.save_public_key('vapid_public.pem')
    print('private:', v.private_key_b64url)
    print('public: ', v.public_key_b64url)
    "
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PushSubscription:
    """JSON push subscription from the browser's PushManager."""
    endpoint: str
    p256dh: str   # client public key
    auth: str     # client auth secret


@dataclass
class PushPayload:
    title: str
    body: str
    url: str = "/lectio-divina"
    icon: str = "/icons/icon-192.svg"
    badge: str = "/icons/icon-192.svg"
    tag: str = "sancta-prayer"
    data: dict = field(default_factory=dict)


class PushNotificationService:
    """Send VAPID web push notifications to subscribed users."""

    def __init__(self) -> None:
        self._enabled = bool(
            settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY
        )
        if not self._enabled:
            logger.info("VAPID keys not configured — push notifications disabled")

    @property
    def public_key(self) -> str:
        return settings.VAPID_PUBLIC_KEY

    async def send(
        self,
        subscription: PushSubscription,
        payload: PushPayload,
    ) -> bool:
        """Send a single push notification.  Returns True on success."""
        if not self._enabled:
            return False

        try:
            from pywebpush import webpush, WebPushException  # type: ignore[import]

            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=json.dumps(
                    {
                        "title": payload.title,
                        "body": payload.body,
                        "url": payload.url,
                        "icon": payload.icon,
                        "badge": payload.badge,
                        "tag": payload.tag,
                        **payload.data,
                    }
                ),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}",
                },
                content_encoding="aes128gcm",
                ttl=86400,  # 24 hours TTL
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Push send failed for %s: %s", subscription.endpoint[:40], exc)
            return False

    async def broadcast(
        self,
        subscriptions: list[PushSubscription],
        payload: PushPayload,
    ) -> dict[str, int]:
        """Broadcast to many subscriptions.  Returns {sent, failed} counts."""
        sent, failed = 0, 0
        for sub in subscriptions:
            if await self.send(sub, payload):
                sent += 1
            else:
                failed += 1
        return {"sent": sent, "failed": failed}

    # ── Canned prayer reminder payloads ──────────────────────────────────

    @staticmethod
    def morning_prayer_payload(feast: str | None = None) -> PushPayload:
        body = f"Dziś: {feast}. " if feast else ""
        body += "Lectio Divina czeka — zacznij dzień ze Słowem."
        return PushPayload(
            title="🌅 Jutrznia — Sancta Nexus",
            body=body,
            url="/lectio-divina",
            tag="morning-prayer",
        )

    @staticmethod
    def vespers_payload() -> PushPayload:
        return PushPayload(
            title="🌇 Nieszpory",
            body="Zakończ dzień Liturgią Godzin.",
            url="/breviary",
            tag="vespers",
        )

    @staticmethod
    def compline_payload() -> PushPayload:
        return PushPayload(
            title="🌙 Kompleta",
            body="Rachunek sumienia i modlitwa przed snem.",
            url="/breviary",
            tag="compline",
        )


# Module-level singleton
push_service = PushNotificationService()

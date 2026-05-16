"""Guest mode — one free Lectio Divina session without registration.

Design constraints:
  - No JWT required for POST /guest/lectio or GET /guest/session/{id}.
  - POST /guest/capture-email is also unauthenticated — email is saved in
    Redis alongside the session; a welcome email is sent separately.
  - Rate limit: 1 guest session per IP per 24 h (Redis key per hashed IP).
  - Session data lives in Redis with a 24 h TTL — nothing persisted to Postgres.
  - After the session, clients show a CTA: save the session by creating an
    account. ``POST /guest/capture-email`` records interest; it does NOT
    auto-create a full account (avoids password-less shadow accounts).
  - AI safety layer is enforced exactly as for authenticated users.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field

from app.core.dependencies import RedisDep

logger = logging.getLogger(__name__)

router = APIRouter()

# Redis key namespaces
_GUEST_RATE_KEY = "guest_rate:{ip_hash}"
_GUEST_SESSION_KEY = "guest_session:{session_id}"
_GUEST_EMAIL_KEY = "guest_email:{session_id}"

_GUEST_TTL = 86_400  # 24 h


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GuestRunRequest(BaseModel):
    emotion_text: str = Field(..., min_length=1, max_length=2000)
    tradition: str = Field(default="")


class GuestSessionResponse(BaseModel):
    guest_session_id: str
    scripture: dict[str, Any] | None = None
    meditation: dict[str, Any] | None = None
    prayer: dict[str, Any] | None = None
    contemplation: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    tradition: str = ""
    kerygmatic_theme: str = ""
    error: str | None = None
    cta: str = (
        "Chcesz zapisać tę sesję i śledzić swój postęp duchowy? "
        "Utwórz bezpłatne konto — zajmuje to 30 sekund."
    )


class GuestEmailCaptureRequest(BaseModel):
    guest_session_id: str
    email: EmailStr


class GuestEmailCaptureResponse(BaseModel):
    message: str
    registered: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ip_hash(request: Request) -> str:
    """Return a stable 16-char hex hash of the client IP for rate-limiting."""
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


async def _check_guest_rate_limit(redis, ip_hash: str) -> None:
    """Raise 429 if this IP already started a guest session today."""
    key = _GUEST_RATE_KEY.format(ip_hash=ip_hash)
    existing = await redis.get(key)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Możesz skorzystać z jednej bezpłatnej sesji na 24 godziny. "
                "Zaloguj się, aby kontynuować bez ograniczeń."
            ),
            headers={"Retry-After": "86400"},
        )


async def _mark_guest_rate_limit(redis, ip_hash: str) -> None:
    key = _GUEST_RATE_KEY.format(ip_hash=ip_hash)
    await redis.setex(key, _GUEST_TTL, "1")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/lectio",
    response_model=GuestSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run one free Lectio Divina session without registration",
)
async def guest_run_lectio(
    request: Request,
    body: GuestRunRequest,
    redis: RedisDep,
) -> GuestSessionResponse:
    """Execute the Lectio Divina pipeline for a guest (unauthenticated) user.

    One session per IP per 24 hours.  The result is stored temporarily in
    Redis (24 h TTL) so the client can retrieve it later.  A CTA message is
    included to encourage account creation.
    """
    ip_hash = _ip_hash(request)
    await _check_guest_rate_limit(redis, ip_hash)

    guest_session_id = str(uuid.uuid4())

    # Run the pipeline — same agent as authenticated users.
    result: dict[str, Any] = {}
    try:
        from app.agents.lectio_divina.lectio_divina_graph import run_session

        result = await run_session(
            user_id=f"guest:{guest_session_id}",
            raw_input=body.emotion_text,
            tradition=body.tradition,
        )
    except Exception as exc:
        logger.error("Guest Lectio pipeline failed: %s", exc, exc_info=True)
        result = {"error": "Błąd przetwarzania. Spróbuj ponownie."}

    # Persist session data in Redis (no Postgres writes for guests).
    session_payload = {
        "guest_session_id": guest_session_id,
        "created_at": datetime.now(UTC).isoformat(),
        "emotion_text": body.emotion_text,
        "tradition": body.tradition,
        "result": result,
    }
    await redis.setex(
        _GUEST_SESSION_KEY.format(session_id=guest_session_id),
        _GUEST_TTL,
        json.dumps(session_payload),
    )

    # Mark IP as having used today's free session.
    await _mark_guest_rate_limit(redis, ip_hash)

    return GuestSessionResponse(
        guest_session_id=guest_session_id,
        scripture=result.get("scripture"),
        meditation=result.get("meditation"),
        prayer=result.get("prayer"),
        contemplation=result.get("contemplation"),
        action=result.get("action"),
        tradition=result.get("tradition", ""),
        kerygmatic_theme=result.get("kerygmatic_theme", ""),
        error=result.get("error"),
    )


@router.get(
    "/session/{guest_session_id}",
    response_model=GuestSessionResponse,
    summary="Retrieve a previously completed guest session",
)
async def get_guest_session(
    guest_session_id: str,
    redis: RedisDep,
) -> GuestSessionResponse:
    """Return a cached guest session by ID (valid for 24 h)."""
    raw = await redis.get(_GUEST_SESSION_KEY.format(session_id=guest_session_id))
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesja gościa wygasła lub nie istnieje. Spróbuj ponownie.",
        )
    data = json.loads(raw)
    result = data.get("result", {})
    return GuestSessionResponse(
        guest_session_id=guest_session_id,
        scripture=result.get("scripture"),
        meditation=result.get("meditation"),
        prayer=result.get("prayer"),
        contemplation=result.get("contemplation"),
        action=result.get("action"),
        tradition=result.get("tradition", ""),
        kerygmatic_theme=result.get("kerygmatic_theme", ""),
        error=result.get("error"),
    )


@router.post(
    "/capture-email",
    response_model=GuestEmailCaptureResponse,
    summary="Record email interest after a guest session (CTA)",
)
async def guest_capture_email(
    body: GuestEmailCaptureRequest,
    redis: RedisDep,
) -> GuestEmailCaptureResponse:
    """Record the guest's email alongside their session for follow-up.

    This does NOT create a full account — it stores the email in Redis so
    the registration flow can pre-fill it.  The frontend should redirect to
    /register?email=... to complete sign-up with a password.
    """
    # Verify session exists (proves user actually completed a session).
    session_raw = await redis.get(_GUEST_SESSION_KEY.format(session_id=body.guest_session_id))
    if not session_raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesja gościa wygasła — nie można zapisać adresu e-mail.",
        )

    await redis.setex(
        _GUEST_EMAIL_KEY.format(session_id=body.guest_session_id),
        _GUEST_TTL,
        body.email,
    )
    logger.info(
        "Guest email captured for session=%s (email=***%s)",
        body.guest_session_id,
        body.email[-10:],
    )

    return GuestEmailCaptureResponse(
        message=(
            "Świetnie! Przejdź do rejestracji, by zapisać swoją sesję i "
            "śledzić postęp duchowy. Twój adres e-mail został zapamiętany."
        ),
        registered=False,
    )

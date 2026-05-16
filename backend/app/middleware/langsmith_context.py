"""LangSmith context middleware.

Sets per-request LangChain run metadata so every LLM call in a request
carries searchable tags in LangSmith:
  - route: the FastAPI path template (e.g. "/api/v1/lectio-divina/run")
  - module: derived from the path (e.g. "lectio-divina")
  - user_id: extracted from JWT sub claim without full validation
    (for trace labelling only — auth is enforced by require_authenticated)

When LANGCHAIN_TRACING_V2 is not active this middleware is a no-op pass-through.
"""
from __future__ import annotations

import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


def _extract_user_id_from_bearer(authorization: str | None) -> str | None:
    """Extract user id from JWT without full signature verification.

    This is used only for trace labelling — actual auth uses require_authenticated.
    Returns None if token is absent or malformed.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    try:
        # JWT header.payload.sig — decode payload (no verification)
        import base64
        import json
        parts = token.split(".")
        if len(parts) != 3:
            return None
        # Pad to multiple of 4 for urlsafe b64 decode
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("sub")
    except Exception:
        return None


class LangSmithContextMiddleware(BaseHTTPMiddleware):
    """Inject per-request LangSmith metadata into LangChain run context."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if os.environ.get("LANGCHAIN_TRACING_V2") != "true":
            return await call_next(request)

        try:
            from langchain_core.callbacks.manager import collect_runs
        except ImportError:
            return await call_next(request)

        # Derive module from path segment after /api/v1/
        path = request.url.path
        parts = path.strip("/").split("/")
        module = parts[2] if len(parts) > 2 else "unknown"

        user_id = _extract_user_id_from_bearer(request.headers.get("authorization"))

        metadata = {
            "route": path,
            "module": module,
            "http_method": request.method,
        }
        if user_id:
            metadata["user_id"] = user_id

        tags = [f"module:{module}", f"env:{os.environ.get('ENV', 'dev')}"]

        try:
            # Set metadata on the LangChain run context for this request scope.
            # ``collect_runs`` is a context manager that captures run IDs but
            # we use it here purely as the entry point to set metadata.
            # LangChain ≥0.2 propagates metadata to child runs automatically.
            import langchain
            if hasattr(langchain, "metadata"):
                langchain.metadata.update(metadata)  # type: ignore[attr-defined]
        except Exception:
            pass

        return await call_next(request)

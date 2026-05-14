"""Audit log service for Sancta Nexus.

Every important platform operation should be recorded here.
Rules:
- Log the WHAT and WHO, not the sensitive content.
- payload_json must never contain: passwords, raw journal text,
  AI response text, confessional content, or PII beyond user IDs.
- Audit rows are never deleted — only archived by admin.

Usage::

    from app.services.audit.audit_service import audit

    await audit.log(
        db=db,
        event_type=AuditEventType.USER_ROLE_CHANGED,
        user_id=target_user.id,
        actor_id=admin_user.id,
        description=f"Role changed from {old_role} to {new_role}",
        payload={"old_role": old_role, "new_role": new_role},
    )
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditEventType, AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Writes structured audit events to the ``audit_logs`` table."""

    async def log(
        self,
        db: AsyncSession,
        event_type: AuditEventType,
        description: str,
        *,
        user_id: str | None = None,
        actor_id: str | None = None,
        payload: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Persist an audit event.

        Parameters
        ----------
        db:           Active async SQLAlchemy session.
        event_type:   Enum value describing the operation.
        description:  Human-readable summary (no PII, no sensitive content).
        user_id:      Subject of the action (may be None for system ops).
        actor_id:     Who performed the action (admin, system, etc.).
        payload:      Non-sensitive context dict (serialised to JSON).
        ip_address:   Request IP for traceability (IPv4 or IPv6).
        """
        payload_json: str | None = None
        if payload:
            try:
                payload_json = json.dumps(payload, default=str, ensure_ascii=False)
            except (TypeError, ValueError):
                payload_json = "{}"

        entry = AuditLog(
            event_type=event_type,
            user_id=user_id,
            actor_id=actor_id,
            description=description[:512],
            payload_json=payload_json,
            ip_address=ip_address,
        )
        db.add(entry)
        # Don't commit here — let the calling route's session handle the transaction.
        logger.info("AUDIT %s | user=%s actor=%s | %s", event_type.value, user_id, actor_id, description)
        return entry

    async def log_ai_interaction(
        self,
        db: AsyncSession,
        *,
        user_id: str | None,
        module: str,
        risk_category: str,
        was_modified: bool,
        violations: list[str] | None = None,
        session_id: str | None = None,
    ) -> None:
        """Record AI interaction metadata (no message text stored)."""
        from app.models.database import AiInteraction

        interaction = AiInteraction(
            user_id=user_id,
            session_id=session_id,
            module=module,
            risk_category=risk_category,
            was_modified=was_modified,
            violations=",".join(violations) if violations else None,
        )
        db.add(interaction)

        if was_modified:
            await self.log(
                db,
                event_type=AuditEventType.AI_RESPONSE_REWRITTEN,
                description=f"AI response rewritten in module '{module}'. "
                            f"category={risk_category} violations={violations}",
                user_id=user_id,
                payload={"module": module, "risk_category": risk_category, "violations": violations},
            )

        if risk_category in ("crisis", "self_harm_risk", "abuse_risk"):
            await self.log(
                db,
                event_type=AuditEventType.AI_CRISIS_DETECTED,
                description=f"Crisis category detected in module '{module}': {risk_category}",
                user_id=user_id,
                payload={"module": module, "risk_category": risk_category},
            )


audit = AuditService()

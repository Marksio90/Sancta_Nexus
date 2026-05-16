"""Feature flag system for Sancta Nexus.

Each platform module has a flag that controls its visibility:
- true  → available to users (or admins, depending on module status)
- false → module disabled; routes return 503, UI hides entry points

Module lifecycle: planned → experimental → beta → stable → disabled

Usage:
    from app.core.feature_flags import require_feature, FeatureFlags

    # In a FastAPI route (raises HTTP 503 when flag is off):
    @router.get("/something")
    async def endpoint(_: None = Depends(require_feature(FeatureFlags.REFLECTION_ASSISTANT))):
        ...

    # Programmatic check:
    if feature_flags.is_enabled(FeatureFlags.COMMUNITIES):
        ...
"""

from __future__ import annotations

from enum import StrEnum

from fastapi import Depends, HTTPException, status

from app.core.config import settings


class FeatureFlags(StrEnum):
    """Canonical names for every platform module flag."""

    LECTIO_DIVINA = "FEATURE_LECTIO_DIVINA"
    BIBLE = "FEATURE_BIBLE"
    PRAYER_JOURNAL = "FEATURE_PRAYER_JOURNAL"
    REFLECTION_ASSISTANT = "FEATURE_REFLECTION_ASSISTANT"
    BREVIARY = "FEATURE_BREVIARY"
    PRAYER_INTENTIONS = "FEATURE_PRAYER_INTENTIONS"
    COMMUNITIES = "FEATURE_COMMUNITIES"
    RETREAT_PROGRAMS = "FEATURE_RETREAT_PROGRAMS"
    SACRAMENTAL_PREP = "FEATURE_SACRAMENTAL_PREP"
    SPIRITUAL_DASHBOARD = "FEATURE_SPIRITUAL_DASHBOARD"
    CONTENT_LIBRARY = "FEATURE_CONTENT_LIBRARY"
    EXAMINATION_OF_CONSCIENCE = "FEATURE_EXAMINATION_OF_CONSCIENCE"
    DISCERNMENT_NOTEBOOK = "FEATURE_DISCERNMENT_NOTEBOOK"
    VOICE = "FEATURE_VOICE"
    NOTIFICATIONS = "FEATURE_NOTIFICATIONS"


_FLAG_TO_SETTING: dict[FeatureFlags, str] = {
    FeatureFlags.LECTIO_DIVINA: "FEATURE_LECTIO_DIVINA",
    FeatureFlags.BIBLE: "FEATURE_BIBLE",
    FeatureFlags.PRAYER_JOURNAL: "FEATURE_PRAYER_JOURNAL",
    FeatureFlags.REFLECTION_ASSISTANT: "FEATURE_REFLECTION_ASSISTANT",
    FeatureFlags.BREVIARY: "FEATURE_BREVIARY",
    FeatureFlags.PRAYER_INTENTIONS: "FEATURE_PRAYER_INTENTIONS",
    FeatureFlags.COMMUNITIES: "FEATURE_COMMUNITIES",
    FeatureFlags.RETREAT_PROGRAMS: "FEATURE_RETREAT_PROGRAMS",
    FeatureFlags.SACRAMENTAL_PREP: "FEATURE_SACRAMENTAL_PREP",
    FeatureFlags.SPIRITUAL_DASHBOARD: "FEATURE_SPIRITUAL_DASHBOARD",
    FeatureFlags.CONTENT_LIBRARY: "FEATURE_CONTENT_LIBRARY",
    FeatureFlags.EXAMINATION_OF_CONSCIENCE: "FEATURE_EXAMINATION_OF_CONSCIENCE",
    FeatureFlags.DISCERNMENT_NOTEBOOK: "FEATURE_DISCERNMENT_NOTEBOOK",
    FeatureFlags.VOICE: "FEATURE_VOICE",
    FeatureFlags.NOTIFICATIONS: "FEATURE_NOTIFICATIONS",
}


class FeatureFlagRegistry:
    """Reads feature flag values from the application settings object."""

    def is_enabled(self, flag: FeatureFlags) -> bool:
        attr = _FLAG_TO_SETTING[flag]
        return bool(getattr(settings, attr, False))

    def all_flags(self) -> dict[str, bool]:
        return {flag.value: self.is_enabled(flag) for flag in FeatureFlags}


feature_flags = FeatureFlagRegistry()


def require_feature(flag: FeatureFlags):
    """FastAPI dependency that raises HTTP 503 when a module is disabled.

    Example::

        @router.get("/path")
        async def my_endpoint(_: None = Depends(require_feature(FeatureFlags.BREVIARY))):
            ...
    """

    def _check() -> None:
        if not feature_flags.is_enabled(flag):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Module '{flag.name.lower()}' is currently disabled.",
            )

    return Depends(_check)

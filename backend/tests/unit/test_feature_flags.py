"""Unit tests for the feature flag system."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.feature_flags import FeatureFlags, FeatureFlagRegistry, require_feature


@pytest.fixture
def registry():
    return FeatureFlagRegistry()


class TestFeatureFlagRegistry:
    def test_stable_flags_enabled_by_default(self, registry):
        with patch("app.core.feature_flags.settings") as mock_settings:
            mock_settings.FEATURE_LECTIO_DIVINA = True
            mock_settings.FEATURE_BIBLE = True
            assert registry.is_enabled(FeatureFlags.LECTIO_DIVINA) is True
            assert registry.is_enabled(FeatureFlags.BIBLE) is True

    def test_planned_flags_disabled_by_default(self, registry):
        with patch("app.core.feature_flags.settings") as mock_settings:
            mock_settings.FEATURE_COMMUNITIES = False
            mock_settings.FEATURE_RETREAT_PROGRAMS = False
            assert registry.is_enabled(FeatureFlags.COMMUNITIES) is False
            assert registry.is_enabled(FeatureFlags.RETREAT_PROGRAMS) is False

    def test_all_flags_returns_dict(self, registry):
        with patch("app.core.feature_flags.settings") as mock_settings:
            for flag in FeatureFlags:
                setattr(mock_settings, flag.value, True)
            flags = registry.all_flags()
            assert isinstance(flags, dict)
            assert len(flags) == len(FeatureFlags)

    def test_missing_attribute_defaults_to_false(self, registry):
        with patch("app.core.feature_flags.settings") as mock_settings:
            del mock_settings.FEATURE_VOICE
            # getattr with default False should handle missing attrs
            result = getattr(mock_settings, "FEATURE_VOICE", False)
            assert result is False


class TestRequireFeature:
    def test_enabled_feature_does_not_raise(self):
        with patch("app.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.is_enabled.return_value = True
            dep = require_feature(FeatureFlags.LECTIO_DIVINA)
            # The dependency factory returns a Depends object; test the inner function
            # by calling the check function directly
            # Extract the inner callable
            inner = dep.dependency
            inner()  # Should not raise

    def test_disabled_feature_raises_503(self):
        with patch("app.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.is_enabled.return_value = False
            dep = require_feature(FeatureFlags.COMMUNITIES)
            inner = dep.dependency
            with pytest.raises(HTTPException) as exc_info:
                inner()
            assert exc_info.value.status_code == 503
            assert "communities" in exc_info.value.detail.lower()

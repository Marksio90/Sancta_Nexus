"""Unit tests for FeatureFlags enum catalog and _FLAG_TO_SETTING mapping.

No mocking needed — pure enum and dict inspection.

Contracts verified:
FeatureFlags enum:
- Exactly 15 flags
- All values start with "FEATURE_"
- Is str subclass, all unique values
- Core spiritual features present: LECTIO_DIVINA, BIBLE, PRAYER_JOURNAL,
  REFLECTION_ASSISTANT, BREVIARY, PRAYER_INTENTIONS, EXAMINATION_OF_CONSCIENCE
- Community features present: COMMUNITIES, PRAYER_INTENTIONS
- Advanced features present: DISCERNMENT_NOTEBOOK, RETREAT_PROGRAMS,
  SPIRITUAL_DASHBOARD, CONTENT_LIBRARY
- Service features present: VOICE, NOTIFICATIONS

_FLAG_TO_SETTING mapping:
- Exactly 15 entries (one per flag)
- All FeatureFlags are covered
- Each flag maps to its own setting name (FEATURE_FLAG → "FEATURE_FLAG")
- All mapped values start with "FEATURE_"
- Values match FeatureFlags enum values exactly (self-referential)
"""

from __future__ import annotations

from app.core.feature_flags import FeatureFlags, _FLAG_TO_SETTING

_EXPECTED_FLAGS = {
    "FEATURE_LECTIO_DIVINA",
    "FEATURE_BIBLE",
    "FEATURE_PRAYER_JOURNAL",
    "FEATURE_REFLECTION_ASSISTANT",
    "FEATURE_BREVIARY",
    "FEATURE_PRAYER_INTENTIONS",
    "FEATURE_COMMUNITIES",
    "FEATURE_RETREAT_PROGRAMS",
    "FEATURE_SACRAMENTAL_PREP",
    "FEATURE_SPIRITUAL_DASHBOARD",
    "FEATURE_CONTENT_LIBRARY",
    "FEATURE_EXAMINATION_OF_CONSCIENCE",
    "FEATURE_DISCERNMENT_NOTEBOOK",
    "FEATURE_VOICE",
    "FEATURE_NOTIFICATIONS",
}


# ===========================================================================
# FeatureFlags enum
# ===========================================================================


class TestFeatureFlagsCatalog:
    def test_exactly_15_flags(self):
        assert len(FeatureFlags) == 15

    def test_all_expected_flags_present(self):
        assert _EXPECTED_FLAGS == {f.value for f in FeatureFlags}

    def test_is_str_subclass(self):
        assert isinstance(FeatureFlags.LECTIO_DIVINA, str)

    def test_all_values_unique(self):
        vals = [f.value for f in FeatureFlags]
        assert len(vals) == len(set(vals))

    def test_all_values_start_with_feature(self):
        for flag in FeatureFlags:
            assert flag.value.startswith("FEATURE_"), (
                f"{flag.name} value {flag.value!r} doesn't start with FEATURE_"
            )

    # Core spiritual features
    def test_lectio_divina(self):
        assert FeatureFlags.LECTIO_DIVINA == "FEATURE_LECTIO_DIVINA"

    def test_bible(self):
        assert FeatureFlags.BIBLE == "FEATURE_BIBLE"

    def test_prayer_journal(self):
        assert FeatureFlags.PRAYER_JOURNAL == "FEATURE_PRAYER_JOURNAL"

    def test_reflection_assistant(self):
        assert FeatureFlags.REFLECTION_ASSISTANT == "FEATURE_REFLECTION_ASSISTANT"

    def test_breviary(self):
        assert FeatureFlags.BREVIARY == "FEATURE_BREVIARY"

    def test_prayer_intentions(self):
        assert FeatureFlags.PRAYER_INTENTIONS == "FEATURE_PRAYER_INTENTIONS"

    def test_examination_of_conscience(self):
        assert FeatureFlags.EXAMINATION_OF_CONSCIENCE == "FEATURE_EXAMINATION_OF_CONSCIENCE"

    # Community features
    def test_communities(self):
        assert FeatureFlags.COMMUNITIES == "FEATURE_COMMUNITIES"

    # Advanced features
    def test_discernment_notebook(self):
        assert FeatureFlags.DISCERNMENT_NOTEBOOK == "FEATURE_DISCERNMENT_NOTEBOOK"

    def test_retreat_programs(self):
        assert FeatureFlags.RETREAT_PROGRAMS == "FEATURE_RETREAT_PROGRAMS"

    def test_spiritual_dashboard(self):
        assert FeatureFlags.SPIRITUAL_DASHBOARD == "FEATURE_SPIRITUAL_DASHBOARD"

    def test_sacramental_prep(self):
        assert FeatureFlags.SACRAMENTAL_PREP == "FEATURE_SACRAMENTAL_PREP"

    def test_content_library(self):
        assert FeatureFlags.CONTENT_LIBRARY == "FEATURE_CONTENT_LIBRARY"

    # Service features
    def test_voice(self):
        assert FeatureFlags.VOICE == "FEATURE_VOICE"

    def test_notifications(self):
        assert FeatureFlags.NOTIFICATIONS == "FEATURE_NOTIFICATIONS"


# ===========================================================================
# _FLAG_TO_SETTING mapping
# ===========================================================================


class TestFlagToSettingMapping:
    def test_exactly_15_entries(self):
        assert len(_FLAG_TO_SETTING) == 15

    def test_all_flags_covered(self):
        for flag in FeatureFlags:
            assert flag in _FLAG_TO_SETTING, f"{flag.name} missing from _FLAG_TO_SETTING"

    def test_each_flag_maps_to_its_own_setting(self):
        for flag, setting in _FLAG_TO_SETTING.items():
            assert setting == flag.value, (
                f"{flag.name} maps to {setting!r}, expected {flag.value!r}"
            )

    def test_all_setting_values_start_with_feature(self):
        for flag, setting in _FLAG_TO_SETTING.items():
            assert setting.startswith("FEATURE_"), (
                f"{flag.name} setting {setting!r} doesn't start with FEATURE_"
            )

    def test_no_extra_entries(self):
        # No settings for unknown/removed flags
        flag_set = set(FeatureFlags)
        for key in _FLAG_TO_SETTING:
            assert key in flag_set, f"Unknown flag {key!r} in _FLAG_TO_SETTING"

    def test_all_settings_unique(self):
        settings = list(_FLAG_TO_SETTING.values())
        assert len(settings) == len(set(settings)), "Duplicate settings in _FLAG_TO_SETTING"

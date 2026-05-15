"""Extended unit tests for app/services/emotion/emotion_service.py.

Complements the basic test_emotion_service.py with focused coverage of:
- EMOTION_LABELS: count, content, assertion guard
- SpiritualStateType enum: 7 values, all expected states
- EmotionAnalysis / SpiritualState dataclasses
- _classify_spiritual_state: dark_night, desolation, consolation, gratitude,
  peace, seeking, neutral
- _detect_movement: towards_consolation, towards_desolation, stable, empty history
- _suggest_prayer: one suggestion per spiritual state
- _describe_state: non-empty description per state
- _compute_vector: keyword presence increases vector, peace floor, all 36 dimensions

No LLM calls — EmotionService is instantiated directly (keyword-based fallback path).
"""

from __future__ import annotations

from app.services.emotion.emotion_service import (
    EMOTION_LABELS,
    EmotionAnalysis,
    EmotionService,
    SpiritualState,
    SpiritualStateType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _svc() -> EmotionService:
    return EmotionService()


def _vector(**kwargs) -> dict[str, float]:
    base = {label: 0.0 for label in EMOTION_LABELS}
    base.update(kwargs)
    return base


def _analysis(primary: str = "peace", vector: dict | None = None) -> EmotionAnalysis:
    v = vector or _vector(peace=0.5)
    return EmotionAnalysis(
        vector=v,
        primary_emotion=primary,
        secondary_emotions=[],
        confidence=0.8,
        spiritual_state=SpiritualStateType.PEACE,
    )


# ===========================================================================
# EMOTION_LABELS
# ===========================================================================


class TestEmotionLabels:
    def test_exactly_36_labels(self):
        assert len(EMOTION_LABELS) == 36

    def test_no_duplicates(self):
        assert len(EMOTION_LABELS) == len(set(EMOTION_LABELS))

    def test_ignatian_markers_present(self):
        for label in ("consolation", "desolation", "indifference"):
            assert label in EMOTION_LABELS

    def test_core_affects_present(self):
        for label in ("joy", "sadness", "anger", "fear"):
            assert label in EMOTION_LABELS

    def test_spiritual_emotions_present(self):
        for label in ("awe", "reverence", "hope", "peace", "dark_night"):
            assert label in EMOTION_LABELS


# ===========================================================================
# SpiritualStateType enum
# ===========================================================================


class TestSpiritualStateType:
    def test_has_7_values(self):
        assert len(SpiritualStateType) == 7

    def test_consolation(self):
        assert SpiritualStateType.CONSOLATION == "consolation"

    def test_desolation(self):
        assert SpiritualStateType.DESOLATION == "desolation"

    def test_dark_night(self):
        assert SpiritualStateType.DARK_NIGHT == "dark_night"

    def test_peace(self):
        assert SpiritualStateType.PEACE == "peace"

    def test_seeking(self):
        assert SpiritualStateType.SEEKING == "seeking"

    def test_gratitude(self):
        assert SpiritualStateType.GRATITUDE == "gratitude"

    def test_neutral(self):
        assert SpiritualStateType.NEUTRAL == "neutral"


# ===========================================================================
# EmotionAnalysis dataclass
# ===========================================================================


class TestEmotionAnalysis:
    def test_fields_set(self):
        ea = EmotionAnalysis(
            vector={"joy": 0.8},
            primary_emotion="joy",
            secondary_emotions=["hope"],
            confidence=0.9,
            spiritual_state=SpiritualStateType.CONSOLATION,
        )
        assert ea.primary_emotion == "joy"
        assert ea.confidence == 0.9
        assert ea.spiritual_state == SpiritualStateType.CONSOLATION

    def test_raw_scores_defaults_empty(self):
        ea = EmotionAnalysis(
            vector={},
            primary_emotion="peace",
            secondary_emotions=[],
            confidence=0.5,
            spiritual_state=SpiritualStateType.PEACE,
        )
        assert ea.raw_scores == {}


# ===========================================================================
# SpiritualState dataclass
# ===========================================================================


class TestSpiritualStateDataclass:
    def test_fields_set(self):
        ss = SpiritualState(
            state=SpiritualStateType.CONSOLATION,
            description="Consolation",
            ignatian_movement="towards_consolation",
            suggested_prayer_form="lectio_divina",
            confidence=0.85,
        )
        assert ss.state == SpiritualStateType.CONSOLATION
        assert ss.ignatian_movement == "towards_consolation"

    def test_confidence_default_zero(self):
        ss = SpiritualState(
            state=SpiritualStateType.NEUTRAL,
            description="",
            ignatian_movement="stable",
            suggested_prayer_form="lectio_divina",
        )
        assert ss.confidence == 0.0


# ===========================================================================
# _classify_spiritual_state
# ===========================================================================


class TestClassifySpiritualState:
    def test_dark_night_threshold(self):
        svc = _svc()
        vector = _vector(dark_night=0.6)
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.DARK_NIGHT

    def test_desolation_threshold(self):
        svc = _svc()
        vector = _vector(desolation=0.6)
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.DESOLATION

    def test_consolation_threshold(self):
        svc = _svc()
        vector = _vector(consolation=0.6)
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.CONSOLATION

    def test_gratitude_threshold(self):
        svc = _svc()
        vector = _vector(gratitude=0.5)
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.GRATITUDE

    def test_peace_threshold(self):
        svc = _svc()
        vector = _vector(peace=0.5)
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.PEACE

    def test_serenity_maps_to_peace(self):
        svc = _svc()
        vector = _vector(serenity=0.5)
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.PEACE

    def test_longing_maps_to_seeking(self):
        svc = _svc()
        vector = _vector(longing=0.5)
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.SEEKING

    def test_doubt_maps_to_seeking(self):
        svc = _svc()
        vector = _vector(doubt=0.4)
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.SEEKING

    def test_all_zeros_returns_neutral(self):
        svc = _svc()
        vector = _vector()
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.NEUTRAL

    def test_dark_night_takes_priority_over_desolation(self):
        svc = _svc()
        vector = _vector(dark_night=0.6, desolation=0.6)
        assert svc._classify_spiritual_state(vector) == SpiritualStateType.DARK_NIGHT


# ===========================================================================
# _detect_movement
# ===========================================================================


class TestDetectMovement:
    def test_empty_history_is_stable(self):
        svc = _svc()
        current = _analysis(vector=_vector(consolation=0.5))
        assert svc._detect_movement(current, []) == "stable"

    def test_rising_consolation_towards_consolation(self):
        svc = _svc()
        history = [
            _analysis(vector=_vector(consolation=0.2, desolation=0.3)),
            _analysis(vector=_vector(consolation=0.2, desolation=0.3)),
        ]
        current = _analysis(vector=_vector(consolation=0.8, desolation=0.0))
        result = svc._detect_movement(current, history)
        assert result == "towards_consolation"

    def test_rising_desolation_towards_desolation(self):
        svc = _svc()
        history = [
            _analysis(vector=_vector(consolation=0.5, desolation=0.1)),
            _analysis(vector=_vector(consolation=0.5, desolation=0.1)),
        ]
        current = _analysis(vector=_vector(consolation=0.0, desolation=0.8))
        result = svc._detect_movement(current, history)
        assert result == "towards_desolation"

    def test_similar_pattern_is_stable(self):
        svc = _svc()
        history = [
            _analysis(vector=_vector(consolation=0.5, desolation=0.1)),
            _analysis(vector=_vector(consolation=0.5, desolation=0.1)),
        ]
        current = _analysis(vector=_vector(consolation=0.5, desolation=0.1))
        result = svc._detect_movement(current, history)
        assert result == "stable"


# ===========================================================================
# _suggest_prayer
# ===========================================================================


class TestSuggestPrayer:
    def test_consolation_gets_lectio(self):
        svc = _svc()
        result = svc._suggest_prayer(SpiritualStateType.CONSOLATION, _vector())
        assert result == "lectio_divina"

    def test_desolation_gets_examen(self):
        svc = _svc()
        result = svc._suggest_prayer(SpiritualStateType.DESOLATION, _vector())
        assert result == "examen"

    def test_dark_night_gets_centering(self):
        svc = _svc()
        result = svc._suggest_prayer(SpiritualStateType.DARK_NIGHT, _vector())
        assert result == "centering_prayer"

    def test_peace_gets_contemplation(self):
        svc = _svc()
        result = svc._suggest_prayer(SpiritualStateType.PEACE, _vector())
        assert result == "contemplation"

    def test_seeking_gets_ignatian(self):
        svc = _svc()
        result = svc._suggest_prayer(SpiritualStateType.SEEKING, _vector())
        assert result == "ignatian_meditation"

    def test_gratitude_gets_psalms(self):
        svc = _svc()
        result = svc._suggest_prayer(SpiritualStateType.GRATITUDE, _vector())
        assert result == "psalms_of_praise"

    def test_neutral_gets_lectio(self):
        svc = _svc()
        result = svc._suggest_prayer(SpiritualStateType.NEUTRAL, _vector())
        assert result == "lectio_divina"


# ===========================================================================
# _describe_state
# ===========================================================================


class TestDescribeState:
    def test_all_states_return_non_empty_description(self):
        svc = _svc()
        ea = _analysis()
        for state in SpiritualStateType:
            desc = svc._describe_state(state, ea)
            assert desc.strip(), f"{state} has empty description"

    def test_consolation_description(self):
        svc = _svc()
        desc = svc._describe_state(SpiritualStateType.CONSOLATION, _analysis())
        assert "pocieszeni" in desc.lower() or "pokój" in desc.lower() or "radosci" in desc.lower()

    def test_dark_night_description(self):
        svc = _svc()
        desc = svc._describe_state(SpiritualStateType.DARK_NIGHT, _analysis())
        assert "ciemn" in desc.lower()


# ===========================================================================
# _compute_vector
# ===========================================================================


class TestComputeVector:
    def test_returns_36_dimensions(self):
        svc = _svc()
        v = svc._compute_vector("some text")
        assert len(v) == 36

    def test_all_keys_are_valid_labels(self):
        svc = _svc()
        v = svc._compute_vector("text")
        assert set(v.keys()) == set(EMOTION_LABELS)

    def test_empty_text_has_peace_floor(self):
        svc = _svc()
        v = svc._compute_vector("")
        assert v["peace"] > 0

    def test_joy_keywords_raise_joy(self):
        svc = _svc()
        # Use exact keyword forms from _KEYWORD_MAP (no diacritics)
        v = svc._compute_vector("radosc szczescie joy happy")
        # At least one joy-related emotion should be non-zero
        joy_related = v.get("joy", 0) + v.get("gratitude", 0) + v.get("consolation", 0)
        assert joy_related > 0

    def test_all_values_in_range(self):
        svc = _svc()
        for text in ("peace", "fear anxiety dread", "", "dziękuję Bogu"):
            v = svc._compute_vector(text)
            for val in v.values():
                assert 0.0 <= val <= 1.0, f"Value {val} out of range"

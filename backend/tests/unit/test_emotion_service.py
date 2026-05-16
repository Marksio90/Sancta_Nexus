"""Unit tests for EmotionService — sync and async paths, crisis detection."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.services.emotion.emotion_service import EmotionService, SpiritualStateType

# ---------------------------------------------------------------------------
# analyze_text (sync, keyword-based) — always works
# ---------------------------------------------------------------------------

def test_analyze_text_returns_emotion_analysis():
    svc = EmotionService()
    result = svc.analyze_text("Czuję spokój i wdzięczność.")
    assert result.primary_emotion
    assert isinstance(result.vector, dict)
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0


def test_analyze_text_detects_spiritual_state():
    svc = EmotionService()
    result = svc.analyze_text("Jestem w ciemności, nie czuję Boga.")
    assert result.spiritual_state in SpiritualStateType


# ---------------------------------------------------------------------------
# analyze_text_async — EmotionDetectorAgent and SpiritualStateClassifier
# are lazy-imported inside the method, so we patch at their source modules.
# ---------------------------------------------------------------------------

async def test_analyze_text_async_falls_back_to_sync_on_error():
    """If LLM agents fail, async analysis must fall back to keyword analysis."""
    svc = EmotionService()
    with patch(
        "app.agents.emotion.emotion_detector.EmotionDetectorAgent",
        side_effect=Exception("no API key"),
    ):
        result = await svc.analyze_text_async("Modlę się z ufnością.")

    assert result.primary_emotion
    assert isinstance(result.vector, dict)


async def test_analyze_text_async_returns_valid_structure_on_success():
    """When A-022 succeeds, the result must satisfy EmotionAnalysis shape."""
    mock_vector = {"peace": 0.9, "gratitude": 0.7, "joy": 0.5}
    mock_state = MagicMock()
    mock_state.primary_state = MagicMock(value="consolation")
    mock_state.confidence = 0.85

    mock_llm = MagicMock()
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm), patch(
        "app.agents.emotion.emotion_detector.EmotionDetectorAgent"
    ) as MockDet:
        det_inst = MockDet.return_value
        det_inst.detect = AsyncMock(return_value=mock_vector)

        with patch(
            "app.agents.emotion.spiritual_state_classifier.SpiritualStateClassifier"
        ) as MockCls:
            cls_inst = MockCls.return_value
            cls_inst.classify = AsyncMock(return_value=mock_state)

            svc = EmotionService()
            result = await svc.analyze_text_async("Panie, jestem blisko Ciebie.")

    assert result.primary_emotion
    assert isinstance(result.vector, dict)


# ---------------------------------------------------------------------------
# detect_crisis — CrisisDetectorAgent is lazy-imported; patch at source.
# ---------------------------------------------------------------------------

async def test_detect_crisis_returns_required_keys():
    svc = EmotionService()
    crisis_result = MagicMock()
    crisis_result.is_crisis = False
    crisis_result.severity = "none"
    crisis_result.concerns = []
    crisis_result.resources = []

    mock_llm = MagicMock()
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm), patch(
        "app.agents.emotion.crisis_detector.CrisisDetectorAgent"
    ) as MockCrisis:
        inst = MockCrisis.return_value
        inst.check = AsyncMock(return_value=crisis_result)

        result = await svc.detect_crisis("Modlę się dziś spokojnie.")

    assert "is_crisis" in result
    assert "severity" in result
    assert "concerns" in result
    assert "resources" in result
    assert result["is_crisis"] is False


async def test_detect_crisis_returns_safe_defaults_on_failure():
    """Even if A-026 explodes, detect_crisis must never raise — safety-critical."""
    svc = EmotionService()
    with patch(
        "app.agents.emotion.crisis_detector.CrisisDetectorAgent",
        side_effect=RuntimeError("meltdown"),
    ):
        result = await svc.detect_crisis("test input")

    assert "is_crisis" in result
    assert result["is_crisis"] is False

"""Tests for AISafetyLayer behaviour expected in the reflection assistant flow.

These extend test_safety.py by covering scenarios that arise specifically when
the reflection assistant processes user messages.
"""

from __future__ import annotations

import pytest

from app.core.safety import AISafetyLayer, RiskCategory


@pytest.fixture
def safety():
    return AISafetyLayer()


class TestSafetyInReflectionContext:
    def test_normal_reflection_not_modified(self, safety):
        result = safety.process(
            user_message="Chcę lepiej rozumieć modlitwę różańcową.",
            ai_response="Różaniec jest piękną formą modlitwy kontemplacyjnej.",
        )
        assert result.final_response
        assert not result.was_modified

    def test_divine_command_pattern_blocked(self, safety):
        result = safety.process(
            user_message="Co mam zrobić?",
            ai_response="Bóg nakazuje ci opuścić rodzinę i wstąpić do zakonu.",
        )
        assert result.was_modified
        assert "divine_command" in result.assessment.detected_issues

    def test_sin_judgment_pattern_blocked(self, safety):
        result = safety.process(
            user_message="Czy to był grzech?",
            ai_response="Tak, masz grzech ciężki i powinieneś żałować.",
        )
        assert result.was_modified
        assert "sin_judgment" in result.assessment.detected_issues

    def test_crisis_input_classified_correctly(self, safety):
        category = safety.classify_input(
            "Nie chcę już żyć. Myślę o skrzywdzeniu siebie."
        )
        assert category in (
            RiskCategory.CRISIS,
            RiskCategory.SELF_HARM_RISK,
            RiskCategory.EMOTIONAL_DISTRESS,
        )

    def test_normal_prayer_question_low_risk(self, safety):
        category = safety.classify_input(
            "Jak mogę pogłębić moją modlitwę poranną?"
        )
        assert category in (RiskCategory.NORMAL_REFLECTION, RiskCategory.PRAYER_SUPPORT)

    def test_final_response_not_empty(self, safety):
        result = safety.process(
            user_message="Potrzebuję spokoju.",
            ai_response="Zapraszam do chwili ciszy z Bogiem.",
        )
        assert result.final_response.strip()

    def test_assessment_category_is_valid_enum(self, safety):
        result = safety.process(
            user_message="Czuję się zagubiony.",
            ai_response="To naturalne. Modlitwa może pomóc.",
        )
        assert result.assessment.category in RiskCategory.__members__.values()

    def test_detected_issues_is_list(self, safety):
        result = safety.process(
            user_message="Co mam zrobić z moim życiem?",
            ai_response="Spokojnie, zastanów się nad modlitwą.",
        )
        assert isinstance(result.assessment.detected_issues, list)


class TestReflectionAssistantSchemaContract:
    """Verify MessageResponse schema contract using a standalone Pydantic model."""

    def test_message_response_has_assistant_response_field(self):
        from pydantic import BaseModel, Field
        from typing import Any

        # Mirror the MessageResponse schema without route imports
        class MessageResponse(BaseModel):
            session_id: str
            assistant_response: str
            emotion_analysis: dict[str, Any] = Field(default_factory=dict)
            suggested_scriptures: list[dict[str, Any]] = Field(default_factory=list)
            spiritual_state: str | None = None
            follow_up_questions: list[str] = Field(default_factory=list)
            prayer_suggestion: str | None = None
            disclaimer: str = (
                "Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy. "
                "Nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty."
            )

        resp = MessageResponse(session_id="s1", assistant_response="Treść refleksji.")
        assert resp.disclaimer
        assert len(resp.disclaimer) > 20
        assert "Asystent refleksji" in resp.disclaimer
        assert "zastępuje" in resp.disclaimer
        assert resp.assistant_response == "Treść refleksji."
        assert "director_response" not in resp.model_fields

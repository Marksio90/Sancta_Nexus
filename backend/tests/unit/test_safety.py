"""Unit tests for the AI safety layer."""

import pytest

from app.core.safety import (
    AISafetyLayer,
    HIGH_RISK_CATEGORIES,
    RiskCategory,
    ai_safety,
)


@pytest.fixture
def safety():
    return AISafetyLayer()


class TestClassifyInput:
    def test_normal_reflection_returns_default(self, safety):
        category = safety.classify_input("Dziś rozważałem Ewangelię Łukasza.")
        assert category == RiskCategory.NORMAL_REFLECTION

    def test_detects_crisis_polish(self, safety):
        category = safety.classify_input("Mam myśli samobójcze i nie wiem co robić.")
        assert category == RiskCategory.CRISIS

    def test_detects_confession_polish(self, safety):
        category = safety.classify_input("Chcę się wyspowiadać, pomóż mi ze spowiedzią.")
        assert category == RiskCategory.CONFESSION_RELATED

    def test_detects_medical_polish(self, safety):
        category = safety.classify_input("Mam depresję i zastanawiam się nad terapią.")
        assert category == RiskCategory.MEDICAL_OR_PSYCHOLOGICAL

    def test_detects_sacrament_polish(self, safety):
        category = safety.classify_input("Chcę przyjąć sakrament bierzmowania.")
        assert category == RiskCategory.SACRAMENTAL_QUESTION

    def test_detects_mortal_sin(self, safety):
        category = safety.classify_input("Czy popełniłem grzech ciężki?")
        assert category == RiskCategory.MORAL_QUESTION

    def test_crisis_is_high_risk(self, safety):
        assessment = safety.assess("Chcę się zabić.")
        assert assessment.is_high_risk is True
        assert assessment.category in HIGH_RISK_CATEGORIES

    def test_confession_is_high_risk(self, safety):
        assessment = safety.assess("Chcę się wyspowiadać przez AI.")
        assert assessment.is_high_risk is True


class TestValidateResponse:
    def test_clean_response_has_no_violations(self, safety):
        response = "Możesz rozważyć ten fragment w modlitwie."
        violations = safety.validate_response(response)
        assert violations == []

    def test_divine_command_detected(self, safety):
        response = "Bóg mówi ci, że masz zmienić pracę."
        violations = safety.validate_response(response)
        assert "divine_command" in violations

    def test_sin_judgment_detected(self, safety):
        response = "Masz grzech ciężki i musisz natychmiast się wyspowiadać."
        violations = safety.validate_response(response)
        assert "sin_judgment" in violations

    def test_isolation_detected(self, safety):
        response = "Nie potrzebujesz z nikim rozmawiać, ja ci pomogę."
        violations = safety.validate_response(response)
        assert "isolation" in violations


class TestProcess:
    def test_high_risk_input_replaces_response(self, safety):
        result = safety.process(
            user_message="Chcę się zabić.",
            ai_response="Modlitwa pomoże ci.",
        )
        assert result.was_modified is True
        assert result.final_response != result.original_response
        assert result.assessment.is_high_risk is True

    def test_policy_violation_triggers_rewrite(self, safety):
        result = safety.process(
            user_message="Co powinienem zrobić?",
            ai_response="Bóg mówi ci, że na pewno powinieneś rzucić pracę.",
        )
        assert result.was_modified is True
        assert "divine_command" in result.assessment.detected_issues

    def test_normal_reflection_gets_disclaimer(self, safety):
        result = safety.process(
            user_message="Dziś czytałem Ewangelię.",
            ai_response="To piękne rozważanie.",
        )
        assert "Asystent refleksji" in result.final_response

    def test_singleton_instance_available(self):
        assert ai_safety is not None
        assert isinstance(ai_safety, AISafetyLayer)


class TestSafetyCategories:
    @pytest.mark.parametrize(
        "message,expected_high_risk",
        [
            ("Czy mam grzech ciężki?", False),  # MORAL_QUESTION — not high risk
            ("Chcę się wyspowiadać przez AI", True),  # CONFESSION_RELATED
            ("Mam depresję", True),  # MEDICAL_OR_PSYCHOLOGICAL
            ("Chcę się zabić", True),  # CRISIS
            ("Dziękuję Bogu za dzisiejszy dzień", False),  # NORMAL
        ],
    )
    def test_risk_classification(self, safety, message, expected_high_risk):
        assessment = safety.assess(message)
        assert assessment.is_high_risk is expected_high_risk

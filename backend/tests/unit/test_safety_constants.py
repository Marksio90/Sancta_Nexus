"""Unit tests for AISafetyLayer constants and data classes.

No LLM, no network — pure catalog and data-layer testing.

Contracts verified:
RiskCategory enum:
- Exactly 14 categories
- Specific values present
- Is a str+Enum

HIGH_RISK_CATEGORIES:
- Is a frozenset
- Exactly 5 categories
- Specific high-risk categories present (crisis, self_harm_risk, abuse_risk,
  medical_or_psychological, confession_related)
- Does not include normal_reflection or prayer_support

ADVISORY_CATEGORIES:
- Is a frozenset
- Exactly 6 categories
- Specific advisory categories present
- HIGH_RISK_CATEGORIES and ADVISORY_CATEGORIES are disjoint

SafetyAssessment dataclass:
- Has all required fields: category, is_high_risk, requires_disclaimer,
  detected_issues, referral_message
- referral_message defaults to None

SafetyResult dataclass:
- Has fields: original_response, final_response, assessment, was_modified

_STANDARD_DISCLAIMER:
- Non-empty string
- Mentions kapłan, spowiednika, kierownika duchowego, terapeuty
- Contains the canonical mission disclaimer phrase

_CRISIS_REFERRAL:
- Mentions telefon zaufania
- Mentions niejesteś sam

_CONFESSION_BOUNDARY:
- Mentions spowiednikiem
- Mentions sakrament

_MORAL_DISCLAIMER:
- Mentions kapłanem or kierownikiem duchowym
"""

from __future__ import annotations

from app.core.safety import (
    _CONFESSION_BOUNDARY,
    _CRISIS_REFERRAL,
    _MORAL_DISCLAIMER,
    _STANDARD_DISCLAIMER,
    ADVISORY_CATEGORIES,
    HIGH_RISK_CATEGORIES,
    RiskCategory,
    SafetyAssessment,
    SafetyResult,
)

# ===========================================================================
# RiskCategory enum
# ===========================================================================


class TestRiskCategoryEnum:
    def test_exactly_14_categories(self):
        assert len(RiskCategory) == 14

    def test_normal_reflection(self):
        assert RiskCategory.NORMAL_REFLECTION.value == "normal_reflection"

    def test_prayer_support(self):
        assert RiskCategory.PRAYER_SUPPORT.value == "prayer_support"

    def test_crisis(self):
        assert RiskCategory.CRISIS.value == "crisis"

    def test_self_harm_risk(self):
        assert RiskCategory.SELF_HARM_RISK.value == "self_harm_risk"

    def test_abuse_risk(self):
        assert RiskCategory.ABUSE_RISK.value == "abuse_risk"

    def test_medical_or_psychological(self):
        assert RiskCategory.MEDICAL_OR_PSYCHOLOGICAL.value == "medical_or_psychological"

    def test_confession_related(self):
        assert RiskCategory.CONFESSION_RELATED.value == "confession_related"

    def test_moral_question(self):
        assert RiskCategory.MORAL_QUESTION.value == "moral_question"

    def test_emotional_distress(self):
        assert RiskCategory.EMOTIONAL_DISTRESS.value == "emotional_distress"

    def test_theological_dispute(self):
        assert RiskCategory.THEOLOGICAL_DISPUTE.value == "theological_dispute"

    def test_is_str_subclass(self):
        assert isinstance(RiskCategory.CRISIS, str)

    def test_all_values_unique(self):
        vals = [c.value for c in RiskCategory]
        assert len(vals) == len(set(vals))


# ===========================================================================
# HIGH_RISK_CATEGORIES
# ===========================================================================


class TestHighRiskCategories:
    def test_is_frozenset(self):
        assert isinstance(HIGH_RISK_CATEGORIES, frozenset)

    def test_exactly_5_categories(self):
        assert len(HIGH_RISK_CATEGORIES) == 5

    def test_crisis_is_high_risk(self):
        assert RiskCategory.CRISIS in HIGH_RISK_CATEGORIES

    def test_self_harm_risk_is_high_risk(self):
        assert RiskCategory.SELF_HARM_RISK in HIGH_RISK_CATEGORIES

    def test_abuse_risk_is_high_risk(self):
        assert RiskCategory.ABUSE_RISK in HIGH_RISK_CATEGORIES

    def test_medical_is_high_risk(self):
        assert RiskCategory.MEDICAL_OR_PSYCHOLOGICAL in HIGH_RISK_CATEGORIES

    def test_confession_is_high_risk(self):
        assert RiskCategory.CONFESSION_RELATED in HIGH_RISK_CATEGORIES

    def test_normal_reflection_not_high_risk(self):
        assert RiskCategory.NORMAL_REFLECTION not in HIGH_RISK_CATEGORIES

    def test_prayer_support_not_high_risk(self):
        assert RiskCategory.PRAYER_SUPPORT not in HIGH_RISK_CATEGORIES

    def test_moral_question_not_high_risk(self):
        assert RiskCategory.MORAL_QUESTION not in HIGH_RISK_CATEGORIES


# ===========================================================================
# ADVISORY_CATEGORIES
# ===========================================================================


class TestAdvisoryCategories:
    def test_is_frozenset(self):
        assert isinstance(ADVISORY_CATEGORIES, frozenset)

    def test_exactly_6_categories(self):
        assert len(ADVISORY_CATEGORIES) == 6

    def test_moral_question_is_advisory(self):
        assert RiskCategory.MORAL_QUESTION in ADVISORY_CATEGORIES

    def test_sacramental_question_is_advisory(self):
        assert RiskCategory.SACRAMENTAL_QUESTION in ADVISORY_CATEGORIES

    def test_vocation_discernment_is_advisory(self):
        assert RiskCategory.VOCATION_DISCERNMENT in ADVISORY_CATEGORIES

    def test_emotional_distress_is_advisory(self):
        assert RiskCategory.EMOTIONAL_DISTRESS in ADVISORY_CATEGORIES

    def test_relationship_or_marriage_is_advisory(self):
        assert RiskCategory.RELATIONSHIP_OR_MARRIAGE in ADVISORY_CATEGORIES

    def test_theological_dispute_is_advisory(self):
        assert RiskCategory.THEOLOGICAL_DISPUTE in ADVISORY_CATEGORIES

    def test_crisis_not_advisory(self):
        assert RiskCategory.CRISIS not in ADVISORY_CATEGORIES

    def test_disjoint_with_high_risk(self):
        overlap = HIGH_RISK_CATEGORIES & ADVISORY_CATEGORIES
        assert not overlap, f"Overlapping categories: {overlap}"


# ===========================================================================
# SafetyAssessment dataclass
# ===========================================================================


class TestSafetyAssessment:
    def test_has_category_field(self):
        sa = SafetyAssessment(
            category=RiskCategory.NORMAL_REFLECTION,
            is_high_risk=False,
            requires_disclaimer=False,
            detected_issues=[],
        )
        assert sa.category == RiskCategory.NORMAL_REFLECTION

    def test_referral_message_defaults_none(self):
        sa = SafetyAssessment(
            category=RiskCategory.NORMAL_REFLECTION,
            is_high_risk=False,
            requires_disclaimer=False,
            detected_issues=[],
        )
        assert sa.referral_message is None

    def test_detected_issues_list(self):
        sa = SafetyAssessment(
            category=RiskCategory.CRISIS,
            is_high_risk=True,
            requires_disclaimer=True,
            detected_issues=["crisis_keyword"],
        )
        assert "crisis_keyword" in sa.detected_issues

    def test_is_high_risk_field(self):
        sa = SafetyAssessment(
            category=RiskCategory.CRISIS,
            is_high_risk=True,
            requires_disclaimer=True,
            detected_issues=[],
        )
        assert sa.is_high_risk is True

    def test_referral_message_can_be_set(self):
        sa = SafetyAssessment(
            category=RiskCategory.CRISIS,
            is_high_risk=True,
            requires_disclaimer=True,
            detected_issues=[],
            referral_message="Nie jesteś sam/sama.",
        )
        assert sa.referral_message is not None


# ===========================================================================
# SafetyResult dataclass
# ===========================================================================


class TestSafetyResult:
    def test_fields(self):
        assessment = SafetyAssessment(
            category=RiskCategory.NORMAL_REFLECTION,
            is_high_risk=False,
            requires_disclaimer=False,
            detected_issues=[],
        )
        sr = SafetyResult(
            original_response="Original",
            final_response="Final",
            assessment=assessment,
            was_modified=False,
        )
        assert sr.original_response == "Original"
        assert sr.final_response == "Final"
        assert sr.was_modified is False

    def test_was_modified_true(self):
        assessment = SafetyAssessment(
            category=RiskCategory.CRISIS,
            is_high_risk=True,
            requires_disclaimer=True,
            detected_issues=[],
        )
        sr = SafetyResult(
            original_response="Old",
            final_response="Crisis response",
            assessment=assessment,
            was_modified=True,
        )
        assert sr.was_modified is True


# ===========================================================================
# _STANDARD_DISCLAIMER
# ===========================================================================


class TestStandardDisclaimer:
    def test_non_empty(self):
        assert len(_STANDARD_DISCLAIMER.strip()) > 50

    def test_mentions_kapłan(self):
        assert "kapłana" in _STANDARD_DISCLAIMER or "kapłan" in _STANDARD_DISCLAIMER

    def test_mentions_spowiednika(self):
        assert "spowiednika" in _STANDARD_DISCLAIMER

    def test_mentions_kierownika_duchowego(self):
        assert "kierownika duchowego" in _STANDARD_DISCLAIMER

    def test_mentions_terapeuty(self):
        assert "terapeuty" in _STANDARD_DISCLAIMER

    def test_mentions_modlitwy(self):
        assert "modlitwy" in _STANDARD_DISCLAIMER or "modlitw" in _STANDARD_DISCLAIMER


# ===========================================================================
# _CRISIS_REFERRAL
# ===========================================================================


class TestCrisisReferral:
    def test_non_empty(self):
        assert len(_CRISIS_REFERRAL.strip()) > 50

    def test_mentions_telefon_zaufania(self):
        assert "telefon zaufania" in _CRISIS_REFERRAL.lower()

    def test_mentions_nie_jestes_sam(self):
        combined = _CRISIS_REFERRAL.lower()
        assert "sam" in combined

    def test_mentions_terapeutą(self):
        assert "terapeutą" in _CRISIS_REFERRAL or "terapeut" in _CRISIS_REFERRAL.lower()


# ===========================================================================
# _CONFESSION_BOUNDARY
# ===========================================================================


class TestConfessionBoundary:
    def test_non_empty(self):
        assert len(_CONFESSION_BOUNDARY.strip()) > 50

    def test_mentions_spowiednikiem(self):
        assert "spowiednikiem" in _CONFESSION_BOUNDARY

    def test_mentions_sakrament(self):
        assert "sakrament" in _CONFESSION_BOUNDARY.lower()

    def test_mentions_kapłana(self):
        assert "kapłana" in _CONFESSION_BOUNDARY


# ===========================================================================
# _MORAL_DISCLAIMER
# ===========================================================================


class TestMoralDisclaimer:
    def test_non_empty(self):
        assert len(_MORAL_DISCLAIMER.strip()) > 30

    def test_mentions_kapłanem_or_kierownikiem(self):
        combined = _MORAL_DISCLAIMER.lower()
        assert "kapłan" in combined or "kierownik" in combined

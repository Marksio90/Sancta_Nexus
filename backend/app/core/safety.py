"""AI Safety Layer for Sancta Nexus.

Every AI interaction must pass through this module before a response is
returned to the user.  The pipeline has five stages:

    1. classify_input   — determine risk category
    2. detect_crisis    — flag high-risk situations immediately
    3. validate_response — check the generated response against policy
    4. apply_disclaimer — append mandatory disclaimer when required
    5. rewrite_if_needed — replace responses that cross theological boundaries

Key principle: the AI is a *reflection assistant*, not a spiritual authority.
It never replaces a priest, confessor, spiritual director, therapist, or
crisis service.

Policy document: docs/safety/ai-safety-policy.md
Theological boundaries: docs/safety/theological-boundaries.md
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ── Risk categories ──────────────────────────────────────────────────────────


class RiskCategory(str, Enum):
    """Classification of user input by theological and safety risk level."""

    NORMAL_REFLECTION = "normal_reflection"
    PRAYER_SUPPORT = "prayer_support"
    SCRIPTURE_QUESTION = "scripture_question"
    MORAL_QUESTION = "moral_question"
    SACRAMENTAL_QUESTION = "sacramental_question"
    EMOTIONAL_DISTRESS = "emotional_distress"
    CRISIS = "crisis"
    SELF_HARM_RISK = "self_harm_risk"
    ABUSE_RISK = "abuse_risk"
    MEDICAL_OR_PSYCHOLOGICAL = "medical_or_psychological"
    CONFESSION_RELATED = "confession_related"
    VOCATION_DISCERNMENT = "vocation_discernment"
    RELATIONSHIP_OR_MARRIAGE = "relationship_or_marriage"
    THEOLOGICAL_DISPUTE = "theological_dispute"


# Categories that require cautious handling and referral to a real person.
HIGH_RISK_CATEGORIES: frozenset[RiskCategory] = frozenset(
    {
        RiskCategory.CRISIS,
        RiskCategory.SELF_HARM_RISK,
        RiskCategory.ABUSE_RISK,
        RiskCategory.MEDICAL_OR_PSYCHOLOGICAL,
        RiskCategory.CONFESSION_RELATED,
    }
)

# Categories where AI may respond but must add an advisory disclaimer.
ADVISORY_CATEGORIES: frozenset[RiskCategory] = frozenset(
    {
        RiskCategory.MORAL_QUESTION,
        RiskCategory.SACRAMENTAL_QUESTION,
        RiskCategory.VOCATION_DISCERNMENT,
        RiskCategory.EMOTIONAL_DISTRESS,
        RiskCategory.RELATIONSHIP_OR_MARRIAGE,
        RiskCategory.THEOLOGICAL_DISPUTE,
    }
)


# ── Keyword patterns (heuristic, supplemented by LLM classification) ─────────

_CRISIS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(samobójstwo|suicide|zabić się|kill myself|nie chcę żyć|end my life)\b", re.I),
    re.compile(r"\b(skrzywdz\w+|przemoc|abuse|hurt myself|self.harm)\b", re.I),
]

_CONFESSION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(spowied\w+|rozgrzeszenie|absolucja|confession|absolution)\b", re.I),
]

_MORTAL_SIN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(grzech ciężki|mortal sin|stan łaski|state of grace)\b", re.I),
]

_SACRAMENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(sakrament\w*|sacrament\w*|eucharystia|communion|bierzmowanie|confirmation)\b", re.I),
]

_MEDICAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(depresja|depression|lęk|anxiety|terapia|therapy|psychiatr\w+|medication)\b", re.I),
]


# ── Forbidden AI response patterns ───────────────────────────────────────────

_FORBIDDEN_RESPONSE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bBóg (mówi ci|nakazuje ci|chce żebyś)\b", re.I), "divine_command"),
    (re.compile(r"\bna pewno powinieneś\b", re.I), "certainty_command"),
    (re.compile(r"\b(masz grzech ciężki|jesteś w grzechu)\b", re.I), "sin_judgment"),
    (re.compile(r"\bnie (potrzebujesz|musisz) (z nikim|do nikogo) (rozmawiać|iść)\b", re.I), "isolation"),
    (re.compile(r"\bGod (tells you|commands you|wants you to)\b", re.I), "divine_command_en"),
    (re.compile(r"\byou (definitely|certainly) (should|must)\b", re.I), "certainty_en"),
    (re.compile(r"\byou (have|committed) (a )?(mortal|grave) sin\b", re.I), "sin_judgment_en"),
]


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class SafetyAssessment:
    category: RiskCategory
    is_high_risk: bool
    requires_disclaimer: bool
    detected_issues: list[str]
    referral_message: str | None = None


@dataclass
class SafetyResult:
    original_response: str
    final_response: str
    assessment: SafetyAssessment
    was_modified: bool


# ── Disclaimers ───────────────────────────────────────────────────────────────

_STANDARD_DISCLAIMER = (
    "\n\n---\n"
    "Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy oraz Słowa Bożego. "
    "Nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty."
)

_CRISIS_REFERRAL = (
    "Widzę, że to, o czym piszesz, jest bardzo trudne. "
    "Zachęcam Cię, żebyś porozmawiał z zaufaną osobą — kapłanem, "
    "terapeutą lub bliskim. W nagłej potrzebie zadzwoń na telefon zaufania.\n\n"
    "Nie jesteś sam/sama."
)

_CONFESSION_BOUNDARY = (
    "W kwestiach spowiedzi i rachunku sumienia najlepiej porozmawiać "
    "bezpośrednio ze spowiednikiem. Mogę pomóc Ci przygotować się do modlitwy "
    "lub rozmyślania, ale nie zastępuję sakramentu ani kapłana."
)

_MORAL_DISCLAIMER = (
    "\n\n---\n"
    "W trudnych kwestiach moralnych warto porozmawiać z zaufanym kapłanem "
    "lub kierownikiem duchowym. Asystent refleksji nie jest autorytetem moralnym."
)


# ── Safety pipeline ───────────────────────────────────────────────────────────


class AISafetyLayer:
    """Stateless safety pipeline applied to every AI interaction."""

    def classify_input(self, user_message: str) -> RiskCategory:
        """Heuristic classification — complement with LLM classification in production."""
        text = user_message.lower()

        for pattern in _CRISIS_PATTERNS:
            if pattern.search(text):
                return RiskCategory.CRISIS

        for pattern in _CONFESSION_PATTERNS:
            if pattern.search(text):
                return RiskCategory.CONFESSION_RELATED

        for pattern in _MORTAL_SIN_PATTERNS:
            if pattern.search(text):
                return RiskCategory.MORAL_QUESTION

        for pattern in _MEDICAL_PATTERNS:
            if pattern.search(text):
                return RiskCategory.MEDICAL_OR_PSYCHOLOGICAL

        for pattern in _SACRAMENT_PATTERNS:
            if pattern.search(text):
                return RiskCategory.SACRAMENTAL_QUESTION

        return RiskCategory.NORMAL_REFLECTION

    def assess(self, user_message: str) -> SafetyAssessment:
        category = self.classify_input(user_message)
        is_high_risk = category in HIGH_RISK_CATEGORIES
        requires_disclaimer = category in ADVISORY_CATEGORIES or is_high_risk

        referral: str | None = None
        if category == RiskCategory.CRISIS or category == RiskCategory.SELF_HARM_RISK:
            referral = _CRISIS_REFERRAL
        elif category == RiskCategory.CONFESSION_RELATED:
            referral = _CONFESSION_BOUNDARY

        return SafetyAssessment(
            category=category,
            is_high_risk=is_high_risk,
            requires_disclaimer=requires_disclaimer,
            detected_issues=[],
            referral_message=referral,
        )

    def validate_response(self, response: str) -> list[str]:
        """Return list of policy violation names found in the response."""
        violations: list[str] = []
        for pattern, name in _FORBIDDEN_RESPONSE_PATTERNS:
            if pattern.search(response):
                violations.append(name)
        return violations

    def process(self, user_message: str, ai_response: str) -> SafetyResult:
        """Full pipeline: assess → validate → modify if needed."""
        assessment = self.assess(user_message)
        violations = self.validate_response(ai_response)
        assessment.detected_issues = violations
        was_modified = False
        final = ai_response

        if assessment.is_high_risk and assessment.referral_message:
            # For high-risk: prepend referral, skip the AI response
            final = assessment.referral_message
            was_modified = True
            logger.warning(
                "AI response replaced by safety referral. category=%s",
                assessment.category,
            )
        elif violations:
            # Response contains forbidden patterns; strip and add boundary message
            final = (
                "Mogę pomóc Ci wrócić do modlitwy i refleksji. "
                "W tej kwestii zachęcam do rozmowy z zaufanym kapłanem lub kierownikiem duchowym."
            )
            was_modified = True
            logger.warning(
                "AI response rewritten due to policy violations: %s",
                violations,
            )
        elif assessment.requires_disclaimer:
            final = final + _MORAL_DISCLAIMER
            was_modified = True
        else:
            final = final + _STANDARD_DISCLAIMER

        return SafetyResult(
            original_response=ai_response,
            final_response=final,
            assessment=assessment,
            was_modified=was_modified,
        )


# Module-level singleton
ai_safety = AISafetyLayer()

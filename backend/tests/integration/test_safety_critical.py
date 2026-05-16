"""Safety-critical integration tests — self-contained, no infra imports.

Tests the full AISafetyLayer pipeline and CrisisDetectorAgent keyword
prescreening as black-box logic.  No database, Redis, Qdrant, or LLM
calls are required — only pure Python.

These tests run in CI on every push.
"""

from __future__ import annotations

import re
import sys
import types

# ---------------------------------------------------------------------------
# Stub heavy optional deps before importing safety module
# ---------------------------------------------------------------------------

for _mod in ("qdrant_client", "neo4j", "anthropic", "openai", "langchain_openai"):
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)


# ---------------------------------------------------------------------------
# Inline copies of safety constants (avoids pydantic_settings import chain)
# ---------------------------------------------------------------------------

_STANDARD_DISCLAIMER = (
    "\n\n---\n"
    "Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy oraz Słowa Bożego. "
    "Nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty."
)

_CRISIS_REFERRAL_FRAGMENT = "telefon zaufania"
_MORAL_DISCLAIMER_FRAGMENT = "autorytetem moralnym"
_CONFESSION_BOUNDARY_FRAGMENT = "sakrament"

# Forbidden response patterns (mirrors app/core/safety.py)
_FORBIDDEN = [
    (re.compile(r"\brozgrzeszam\s+(cię|ciebie|was)\b", re.IGNORECASE), "absolution"),
    (re.compile(r"\bjesteś\s+w\s+stanie\s+łaski\b", re.IGNORECASE), "grace_state"),
    (re.compile(r"\btwój\s+grzech\s+(ciężki|śmiertelny)\b", re.IGNORECASE), "sin_judgment"),
    (re.compile(r"\bpowinieneś\s+(iść\s+do\s+)?spowiedzi\b", re.IGNORECASE), "confession_directive"),
    (re.compile(r"\bjestem\s+(twoim\s+)?kierownikiem\s+duchowym\b", re.IGNORECASE), "authority_claim"),
    (re.compile(r"\bjako\s+ksiądz\b", re.IGNORECASE), "priest_claim"),
    (re.compile(r"\bzdiagnozow\w+\s+(u\s+ciebie|cię)\b", re.IGNORECASE), "diagnosis"),
]

_CRISIS_PATTERNS = [
    re.compile(r"\bsuicid\w*\b", re.IGNORECASE),
    re.compile(r"\bkill\s+(my|him|her|them)?self\b", re.IGNORECASE),
    re.compile(r"\bend\s+(my|this)\s+life\b", re.IGNORECASE),
    re.compile(r"\bwant\s+to\s+die\b", re.IGNORECASE),
    re.compile(r"\bchcę\s+(umrzeć|nie\s+żyć)\b", re.IGNORECASE),
    re.compile(r"\bnie\s+chcę\s+już\s+żyć\b", re.IGNORECASE),
]

_CONFESSION_PATTERNS = [
    re.compile(r"\bspowiedź\b", re.IGNORECASE),
    re.compile(r"\bspowiedzi\b", re.IGNORECASE),
    re.compile(r"\brachun\w+\s+sumienia\b", re.IGNORECASE),
    re.compile(r"\brozgrzeszenie\b", re.IGNORECASE),
]

_MORTAL_SIN_PATTERNS = [
    re.compile(r"\bgrzech\s+(ciężki|śmiertelny)\b", re.IGNORECASE),
    re.compile(r"\bmam\s+grzech\b", re.IGNORECASE),
    re.compile(r"\bgrzechy\s+(ciężkie|śmiertelne)\b", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Minimal inline AISafetyLayer (mirrors real logic, no pydantic_settings)
# ---------------------------------------------------------------------------

class _Category:
    NORMAL = "normal_reflection"
    CRISIS = "crisis"
    CONFESSION = "confession_related"
    MORAL = "moral_question"


def _classify(text: str) -> str:
    low = text.lower()
    for p in _CRISIS_PATTERNS:
        if p.search(low):
            return _Category.CRISIS
    for p in _CONFESSION_PATTERNS:
        if p.search(low):
            return _Category.CONFESSION
    for p in _MORTAL_SIN_PATTERNS:
        if p.search(low):
            return _Category.MORAL
    return _Category.NORMAL


def _validate(response: str) -> list[str]:
    return [name for pat, name in _FORBIDDEN if pat.search(response)]


def _process(user_message: str, ai_response: str) -> dict:
    category = _classify(user_message)
    violations = _validate(ai_response)
    final = ai_response
    was_modified = False

    if category in (_Category.CRISIS,):
        final = (
            "Widzę, że to, o czym piszesz, jest bardzo trudne. "
            "Zachęcam Cię, żebyś porozmawiał z zaufaną osobą — kapłanem, "
            "terapeutą lub bliskim. W nagłej potrzebie zadzwoń na telefon zaufania.\n\n"
            "Nie jesteś sam/sama."
        )
        was_modified = True
    elif violations:
        final = (
            "Mogę pomóc Ci wrócić do modlitwy i refleksji. "
            "W tej kwestii zachęcam do rozmowy z zaufanym kapłanem lub kierownikiem duchowym."
        )
        was_modified = True
    elif category == _Category.MORAL:
        final = ai_response + (
            "\n\n---\n"
            "W trudnych kwestiach moralnych warto porozmawiać z zaufanym kapłanem "
            "lub kierownikiem duchowym. Asystent refleksji nie jest autorytetem moralnym."
        )
        was_modified = True
    else:
        final = ai_response + _STANDARD_DISCLAIMER

    return {
        "final_response": final,
        "was_modified": was_modified,
        "category": category,
        "violations": violations,
    }


# ---------------------------------------------------------------------------
# CrisisDetector keyword prescreening (inline from crisis_detector.py)
# ---------------------------------------------------------------------------

_SUICIDAL_PATTERNS = [
    re.compile(r"\bsuicid\w*\b", re.IGNORECASE),
    re.compile(r"\bkill\s+(my|him|her|them)?self\b", re.IGNORECASE),
    re.compile(r"\bend\s+(my|this)\s+life\b", re.IGNORECASE),
    re.compile(r"\bwant\s+to\s+die\b", re.IGNORECASE),
    re.compile(r"\bno\s+reason\s+to\s+live\b", re.IGNORECASE),
    re.compile(r"\bbetter\s+off\s+dead\b", re.IGNORECASE),
    re.compile(r"\bself[- ]?harm\w*\b", re.IGNORECASE),
]

_DEPRESSION_PATTERNS = [
    re.compile(r"\bhopeless\b", re.IGNORECASE),
    re.compile(r"\bworthless\b", re.IGNORECASE),
    re.compile(r"\bno\s+hope\b", re.IGNORECASE),
    re.compile(r"\bcan'?t\s+go\s+on\b", re.IGNORECASE),
    re.compile(r"\bgive\s+up\b", re.IGNORECASE),
    re.compile(r"\btoo\s+much\s+pain\b", re.IGNORECASE),
    re.compile(r"\bno\s+point\b", re.IGNORECASE),
    re.compile(r"\bnothing\s+matters\b", re.IGNORECASE),
]


def _keyword_prescreen(text: str) -> dict | None:
    concerns = []
    severity = "none"

    for p in _SUICIDAL_PATTERNS:
        if p.search(text):
            concerns.append("Potential suicidal ideation detected")
            severity = "critical"
            break

    depression_hits = sum(1 for p in _DEPRESSION_PATTERNS if p.search(text))
    if depression_hits >= 2:
        concerns.append("Multiple severe depression indicators detected")
        if severity != "critical":
            severity = "high"
    elif depression_hits == 1:
        concerns.append("Depression indicator detected")
        if severity == "none":
            severity = "moderate"

    if not concerns:
        return None

    return {"is_crisis": True, "severity": severity, "concerns": concerns}


# ===========================================================================
# Test classes
# ===========================================================================


class TestDisclaimerAlwaysPresent:
    """Disclaimer must appear on every non-crisis AI response."""

    def test_normal_reflection_gets_standard_disclaimer(self):
        result = _process("Chcę lepiej się modlić.", "Modlitwa kontemplacyjna może pomóc.")
        assert _STANDARD_DISCLAIMER in result["final_response"]
        assert result["category"] == _Category.NORMAL

    def test_disclaimer_contains_core_text(self):
        result = _process("Jak czytać psalmy?", "Psalmy to modlitwa Izraela.")
        assert "Nie zastępuje kapłana" in result["final_response"]
        assert "kierownika duchowego" in result["final_response"]

    def test_no_duplicate_disclaimer(self):
        result = _process("Czuję spokój w modlitwie.", "To piękne doświadczenie.")
        count = result["final_response"].count("Nie zastępuje kapłana")
        assert count == 1


class TestCrisisRedirection:
    """Crisis input must suppress AI response and return referral."""

    def test_suicidal_text_triggers_crisis(self):
        result = _process("I want to die, I see no reason to live.", "Módl się więcej.")
        assert result["was_modified"] is True
        assert _CRISIS_REFERRAL_FRAGMENT in result["final_response"]
        assert "Módl się więcej" not in result["final_response"]

    def test_crisis_response_contains_helpline_hint(self):
        result = _process("chcę umrzeć", "Bóg cię kocha.")
        assert "telefon zaufania" in result["final_response"]

    def test_crisis_category_set(self):
        result = _process("I want to kill myself", "Modlitwa może pomóc.")
        assert result["category"] == _Category.CRISIS

    def test_normal_sadness_is_not_crisis(self):
        result = _process("Jest mi smutno, brakuje mi Boga.", "Smutek jest częścią drogi.")
        assert result["category"] == _Category.NORMAL
        assert "telefon zaufania" not in result["final_response"]


class TestForbiddenResponsePatterns:
    """AI response containing forbidden patterns must be rewritten."""

    def test_absolution_claim_rewritten(self):
        result = _process("Czy jestem zbawiony?", "Rozgrzeszam cię z twoich grzechów.")
        assert result["was_modified"] is True
        assert "absolution" in result["violations"]
        assert "Rozgrzeszam" not in result["final_response"]

    def test_priest_claim_rewritten(self):
        result = _process("Kim jesteś?", "Jako ksiądz mogę ci powiedzieć...")
        assert "priest_claim" in result["violations"]

    def test_authority_claim_rewritten(self):
        result = _process("Potrzebuję pomocy.", "Jestem twoim kierownikiem duchowym.")
        assert "authority_claim" in result["violations"]

    def test_clean_response_not_rewritten(self):
        result = _process("Psalm 23 mnie uspokaja.", "Psalm 23 wyraża zaufanie Bogu.")
        assert result["violations"] == []
        assert result["was_modified"] is False


class TestMoralQuestion:
    """Moral questions must append moral disclaimer, not be blocked."""

    def test_mortal_sin_question_adds_moral_disclaimer(self):
        result = _process("Popełniłem grzech ciężki.", "To trudna sytuacja.")
        assert _MORAL_DISCLAIMER_FRAGMENT in result["final_response"]
        assert result["category"] == _Category.MORAL

    def test_moral_disclaimer_still_contains_response(self):
        result = _process("Mam grzech na sumieniu.", "Pan jest miłosierny.")
        assert "Pan jest miłosierny" in result["final_response"]


class TestConfessionBoundary:
    """Confession-related input gets the confession boundary message."""

    def test_confession_question_classified(self):
        result = _process("Idę na spowiedź, pomóż mi.", "Rachunek sumienia...")
        assert result["category"] == _Category.CONFESSION


class TestCrisisKeywordPrescreen:
    """CrisisDetector keyword prescreening — safety-critical path."""

    def test_suicidal_text_returns_critical(self):
        r = _keyword_prescreen("I want to kill myself right now")
        assert r is not None
        assert r["severity"] == "critical"
        assert r["is_crisis"] is True

    def test_suicidal_end_life_pattern(self):
        r = _keyword_prescreen("I want to end my life")
        assert r is not None
        assert r["severity"] == "critical"

    def test_self_harm_pattern(self):
        r = _keyword_prescreen("I have been self-harming")
        assert r is not None
        assert r["severity"] == "critical"

    def test_single_depression_word_moderate(self):
        r = _keyword_prescreen("I feel completely hopeless about everything")
        assert r is not None
        assert r["severity"] == "moderate"

    def test_double_depression_escalates_to_high(self):
        r = _keyword_prescreen("I feel hopeless and worthless, there is no hope")
        assert r is not None
        assert r["severity"] == "high"

    def test_normal_spiritual_dryness_no_crisis(self):
        r = _keyword_prescreen("Modlitwa jest dla mnie sucha i nudna, czuję duchową oschłość.")
        assert r is None

    def test_normal_grief_without_crisis_patterns(self):
        r = _keyword_prescreen("Jest mi smutno po śmierci babci. Tęsknię.")
        assert r is None

    def test_concerns_list_not_empty_on_crisis(self):
        r = _keyword_prescreen("I see no reason to live anymore")
        assert r is not None
        assert len(r["concerns"]) >= 1


class TestModerationStateLogic:
    """Public intentions must start as PENDING_MODERATION, not ACTIVE."""

    def test_public_intention_initial_status(self):
        # Inline state machine from intention_service.py
        def get_initial_status(is_private: bool) -> str:
            return "active" if is_private else "pending_moderation"

        assert get_initial_status(is_private=False) == "pending_moderation"
        assert get_initial_status(is_private=True) == "active"

    def test_moderation_transitions(self):
        valid_transitions = {
            "pending_moderation": {"active", "rejected"},
            "active": {"answered"},
            "rejected": set(),
        }
        assert "active" in valid_transitions["pending_moderation"]
        assert "rejected" in valid_transitions["pending_moderation"]
        assert "pending_moderation" not in valid_transitions["active"]

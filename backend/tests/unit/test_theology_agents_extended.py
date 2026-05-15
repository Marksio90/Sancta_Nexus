"""Unit tests for theology agents and marriage-prep service.

Stubs qdrant_client (not installed).

Contracts verified:
ExegesisAgent (A-018):
- _DIMENSION_PROMPTS: 4 keys, all non-empty strings
- AGENT_ID / AGENT_NAME constants
- _format_reference: single verse and verse range

MagisteriumValidator (A-016):
- ALIGNMENT_THRESHOLD / COLLECTION_NAME constants
- SOURCE_CATEGORIES: 5 values, all expected
- ValidationResult: frozen dataclass, fields, defaults
- validate: embedding failure → invalid, search failure → invalid,
  no results → invalid, above threshold → valid with references,
  below threshold → invalid with issue text

PatristicAgent (A-017):
- COLLECTION_NAME / DEFAULT_MIN_RELEVANCE constants
- SUPPORTED_FATHERS: 18 fathers, key figures present
- PatristicReference: frozen, all fields
- find_patristic_references: embedding failure → [], search failure → [],
  success → list of PatristicReference

MarriagePrepService:
- MarriagePrepSession enum: 8 values, all expected
- SESSIONS: 8 items, unique session_ids, scripture, CCC refs, questions,
  exercises, prayers; each contains Humanae Vitae / Familiaris Consortio refs
- get_program: 8 dicts with all required keys
- get_session: found/not found
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

# Stub unavailable packages before import
if "qdrant_client" not in sys.modules:
    sys.modules["qdrant_client"] = MagicMock()
    sys.modules["qdrant_client.models"] = MagicMock()
if "openai" not in sys.modules:
    sys.modules["openai"] = MagicMock()

import pytest

from app.agents.theology.exegesis_agent import (
    ExegesisAgent,
    _DIMENSION_PROMPTS,
)
from app.agents.theology.magisterium_validator import (
    ALIGNMENT_THRESHOLD,
    COLLECTION_NAME as MAGISTERIUM_COLLECTION,
    MagisteriumValidator,
    ValidationResult,
)
from app.agents.theology.patristic_agent import (
    COLLECTION_NAME as PATRISTIC_COLLECTION,
    DEFAULT_MIN_RELEVANCE,
    PatristicAgent,
    PatristicReference,
)
from app.services.sacraments.marriage_prep_service import (
    SESSIONS,
    MarriagePrepService,
    MarriagePrepSession,
    SessionContent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mag_validator(
    *,
    embed_fn=None,
    threshold: float = ALIGNMENT_THRESHOLD,
) -> MagisteriumValidator:
    client = AsyncMock()
    embed = embed_fn or AsyncMock(return_value=[0.1] * 1536)
    v = MagisteriumValidator.__new__(MagisteriumValidator)
    v._client = client
    v._embed = embed
    v._collection = MAGISTERIUM_COLLECTION
    v._threshold = threshold
    v._top_k = 10
    return v


def _patristic_agent(*, embed_fn=None) -> PatristicAgent:
    client = AsyncMock()
    embed = embed_fn or AsyncMock(return_value=[0.1] * 1536)
    a = PatristicAgent.__new__(PatristicAgent)
    a._client = client
    a._embed = embed
    a._collection = PATRISTIC_COLLECTION
    a._min_relevance = DEFAULT_MIN_RELEVANCE
    a._top_k = 10
    return a


def _make_hit(score: float, payload: dict | None = None):
    hit = MagicMock()
    hit.score = score
    hit.payload = payload or {}
    return hit


def _marriage_svc() -> MarriagePrepService:
    svc = MarriagePrepService.__new__(MarriagePrepService)
    svc._client = AsyncMock()
    svc._model = "gpt-4o-mini"
    return svc


# ===========================================================================
# ExegesisAgent (A-018)
# ===========================================================================


class TestExegesisConstants:
    def test_agent_id(self):
        assert ExegesisAgent.AGENT_ID == "A-018"

    def test_agent_name(self):
        assert ExegesisAgent.AGENT_NAME == "ExegesisAgent"

    def test_agent_id_class_level(self):
        assert hasattr(ExegesisAgent, "AGENT_ID")

    def test_exactly_4_dimensions(self):
        assert len(_DIMENSION_PROMPTS) == 4

    def test_all_four_dimensions_present(self):
        expected = {"historical_critical", "literary", "theological", "canonical"}
        assert set(_DIMENSION_PROMPTS.keys()) == expected

    def test_all_prompts_non_empty(self):
        for key, prompt in _DIMENSION_PROMPTS.items():
            assert isinstance(prompt, str) and len(prompt) > 20, f"{key} prompt too short"

    def test_historical_critical_mentions_sitz_im_leben(self):
        assert "Sitz im Leben" in _DIMENSION_PROMPTS["historical_critical"]

    def test_literary_mentions_genre_or_structure(self):
        p = _DIMENSION_PROMPTS["literary"].lower()
        assert "genre" in p or "structure" in p

    def test_theological_mentions_catholic(self):
        assert "Catholic" in _DIMENSION_PROMPTS["theological"]

    def test_canonical_mentions_typological(self):
        p = _DIMENSION_PROMPTS["canonical"].lower()
        assert "typolog" in p or "canonical" in p


class TestFormatReference:
    def test_single_verse(self):
        result = ExegesisAgent._format_reference("John", 3, 16, 16)
        assert result == "John 3:16"

    def test_verse_range(self):
        result = ExegesisAgent._format_reference("Genesis", 1, 1, 5)
        assert result == "Genesis 1:1-5"

    def test_start_equals_end_no_dash(self):
        result = ExegesisAgent._format_reference("Psalm", 23, 1, 1)
        assert "-" not in result

    def test_range_includes_both_verse_numbers(self):
        result = ExegesisAgent._format_reference("Romans", 8, 28, 39)
        assert "28" in result
        assert "39" in result

    def test_book_and_chapter_included(self):
        result = ExegesisAgent._format_reference("Matthew", 5, 3, 12)
        assert "Matthew" in result
        assert "5" in result


# ===========================================================================
# MagisteriumValidator (A-016)
# ===========================================================================


class TestMagisteriumConstants:
    def test_alignment_threshold(self):
        assert 0 < ALIGNMENT_THRESHOLD < 1

    def test_collection_name(self):
        assert MAGISTERIUM_COLLECTION == "magisterium"

    def test_source_categories_count(self):
        assert len(MagisteriumValidator.SOURCE_CATEGORIES) == 5

    def test_catechism_present(self):
        assert "catechism" in MagisteriumValidator.SOURCE_CATEGORIES

    def test_vatican_ii_present(self):
        assert "vatican_ii" in MagisteriumValidator.SOURCE_CATEGORIES

    def test_papal_encyclical_present(self):
        assert "papal_encyclical" in MagisteriumValidator.SOURCE_CATEGORIES

    def test_apostolic_constitution_present(self):
        assert "apostolic_constitution" in MagisteriumValidator.SOURCE_CATEGORIES

    def test_apostolic_exhortation_present(self):
        assert "apostolic_exhortation" in MagisteriumValidator.SOURCE_CATEGORIES


class TestValidationResultDataclass:
    def test_is_frozen(self):
        r = ValidationResult(is_valid=True, confidence=0.9)
        with pytest.raises((AttributeError, TypeError)):
            r.confidence = 0.1  # type: ignore[misc]

    def test_required_fields(self):
        r = ValidationResult(is_valid=True, confidence=0.85)
        assert r.is_valid is True
        assert r.confidence == 0.85

    def test_issues_default_empty(self):
        r = ValidationResult(is_valid=True, confidence=0.9)
        assert r.issues == []

    def test_references_default_empty(self):
        r = ValidationResult(is_valid=True, confidence=0.9)
        assert r.references == []

    def test_custom_fields(self):
        r = ValidationResult(
            is_valid=False,
            confidence=0.4,
            issues=["Score too low"],
            references=["CCC §100"],
        )
        assert r.issues == ["Score too low"]
        assert r.references == ["CCC §100"]


class TestMagisteriumValidate:
    @pytest.mark.asyncio
    async def test_embedding_failure_returns_invalid(self):
        embed = AsyncMock(side_effect=RuntimeError("embedding failed"))
        v = _mag_validator(embed_fn=embed)
        result = await v.validate("some theological content")
        assert result.is_valid is False
        assert result.confidence == 0.0
        assert any("mbedding" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_search_failure_returns_invalid(self):
        v = _mag_validator()
        v._client.search = AsyncMock(side_effect=RuntimeError("qdrant down"))
        result = await v.validate("some content")
        assert result.is_valid is False
        assert result.confidence == 0.0
        assert any("search" in i.lower() or "qdrant" in i.lower() or "vector" in i.lower() for i in result.issues)

    @pytest.mark.asyncio
    async def test_no_results_returns_invalid(self):
        v = _mag_validator()
        v._client.search = AsyncMock(return_value=[])
        result = await v.validate("some content")
        assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_above_threshold_is_valid(self):
        v = _mag_validator(threshold=0.80)
        hit = _make_hit(0.92, {"source": "CCC", "paragraph": "§100"})
        v._client.search = AsyncMock(return_value=[hit])
        result = await v.validate("Eucharist is the source and summit")
        assert result.is_valid is True
        assert result.confidence >= 0.80

    @pytest.mark.asyncio
    async def test_below_threshold_is_invalid(self):
        v = _mag_validator(threshold=0.82)
        hit = _make_hit(0.60, {"source": "CCC"})
        v._client.search = AsyncMock(return_value=[hit])
        result = await v.validate("something vague")
        assert result.is_valid is False
        assert len(result.issues) >= 1

    @pytest.mark.asyncio
    async def test_references_collected_above_threshold(self):
        v = _mag_validator(threshold=0.80)
        hits = [
            _make_hit(0.91, {"source": "Lumen Gentium", "paragraph": "§8"}),
            _make_hit(0.85, {"source": "CCC", "paragraph": "§100"}),
            _make_hit(0.65, {"source": "other"}),  # below threshold, not in refs
        ]
        v._client.search = AsyncMock(return_value=hits)
        result = await v.validate("ecclesiology content")
        assert any("Lumen Gentium" in r for r in result.references)
        assert any("CCC" in r for r in result.references)
        # below-threshold source should not appear
        assert not any("other" in r for r in result.references)

    @pytest.mark.asyncio
    async def test_confidence_is_top_score(self):
        v = _mag_validator(threshold=0.80)
        hits = [_make_hit(0.88), _make_hit(0.75)]
        v._client.search = AsyncMock(return_value=hits)
        result = await v.validate("content")
        assert result.confidence == pytest.approx(0.88, abs=0.001)

    @pytest.mark.asyncio
    async def test_invalid_category_returns_invalid(self):
        v = _mag_validator()
        result = await v.validate_with_category("content", "unknown_category")
        assert result.is_valid is False
        assert any("Unknown category" in i or "nknown" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_valid_category_accepted(self):
        v = _mag_validator(threshold=0.80)
        hit = _make_hit(0.91, {"source": "Catechism"})
        v._client.search = AsyncMock(return_value=[hit])
        result = await v.validate_with_category("content", "catechism")
        assert result.is_valid is True


# ===========================================================================
# PatristicAgent (A-017)
# ===========================================================================


class TestPatristicConstants:
    def test_collection_name(self):
        assert PATRISTIC_COLLECTION == "patrystyka"

    def test_default_min_relevance(self):
        assert 0 < DEFAULT_MIN_RELEVANCE < 1

    def test_supported_fathers_count(self):
        assert len(PatristicAgent.SUPPORTED_FATHERS) == 18

    def test_augustine_present(self):
        assert any("Augustine" in f for f in PatristicAgent.SUPPORTED_FATHERS)

    def test_aquinas_present(self):
        assert any("Aquinas" in f for f in PatristicAgent.SUPPORTED_FATHERS)

    def test_john_of_the_cross_present(self):
        assert any("John of the Cross" in f for f in PatristicAgent.SUPPORTED_FATHERS)

    def test_teresa_of_avila_present(self):
        assert any("Teresa" in f for f in PatristicAgent.SUPPORTED_FATHERS)

    def test_all_fathers_non_empty(self):
        for name in PatristicAgent.SUPPORTED_FATHERS:
            assert name.strip()


class TestPatristicReferenceDataclass:
    def test_is_frozen(self):
        ref = PatristicReference(
            father_name="Augustine",
            work="Confessions",
            quote="Our heart is restless",
            relevance_score=0.9,
        )
        with pytest.raises((AttributeError, TypeError)):
            ref.relevance_score = 0.5  # type: ignore[misc]

    def test_all_fields(self):
        ref = PatristicReference(
            father_name="Thomas Aquinas",
            work="Summa Theologica",
            quote="Faith is a habit of mind",
            relevance_score=0.88,
        )
        assert ref.father_name == "Thomas Aquinas"
        assert ref.work == "Summa Theologica"
        assert ref.relevance_score == 0.88


class TestFindPatristicReferences:
    @pytest.mark.asyncio
    async def test_embedding_failure_returns_empty(self):
        embed = AsyncMock(side_effect=RuntimeError("embed failed"))
        agent = _patristic_agent(embed_fn=embed)
        result = await agent.find_patristic_references("John 14:6", "I am the way")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_failure_returns_empty(self):
        agent = _patristic_agent()
        agent._client.search = AsyncMock(side_effect=RuntimeError("qdrant down"))
        result = await agent.find_patristic_references("John 3:16", "God so loved")
        assert result == []

    @pytest.mark.asyncio
    async def test_success_returns_patristic_references(self):
        agent = _patristic_agent()
        hits = [
            _make_hit(0.88, {"father_name": "Augustine", "work": "Confessions", "text": "Our heart is restless"}),
            _make_hit(0.75, {"father_name": "Aquinas", "work": "Summa", "text": "Faith seeks understanding"}),
        ]
        agent._client.search = AsyncMock(return_value=hits)
        result = await agent.find_patristic_references("John 14:6", "Way, Truth, Life")
        assert len(result) == 2
        assert isinstance(result[0], PatristicReference)
        assert result[0].father_name == "Augustine"
        assert result[0].relevance_score == pytest.approx(0.88, abs=0.001)

    @pytest.mark.asyncio
    async def test_no_hits_returns_empty(self):
        agent = _patristic_agent()
        agent._client.search = AsyncMock(return_value=[])
        result = await agent.find_patristic_references("Romans 8", "nothing in common")
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_payload_uses_defaults(self):
        agent = _patristic_agent()
        hits = [_make_hit(0.80, {})]
        agent._client.search = AsyncMock(return_value=hits)
        result = await agent.find_patristic_references("Ps 23", "shepherd")
        assert result[0].father_name == "Unknown Father"
        assert result[0].work == "Unknown Work"

    @pytest.mark.asyncio
    async def test_scores_rounded_to_4_decimals(self):
        agent = _patristic_agent()
        hits = [_make_hit(0.8123456, {"father_name": "Jerome", "work": "Vulgate", "text": "In principio"})]
        agent._client.search = AsyncMock(return_value=hits)
        result = await agent.find_patristic_references("Gen 1:1", "In the beginning")
        assert result[0].relevance_score == round(0.8123456, 4)


# ===========================================================================
# MarriagePrepService
# ===========================================================================


class TestMarriagePrepSession:
    def test_exactly_8_values(self):
        assert len(MarriagePrepSession) == 8

    def test_sacrament(self):
        assert MarriagePrepSession.SACRAMENT == "sacrament"

    def test_love(self):
        assert MarriagePrepSession.LOVE == "love"

    def test_communication(self):
        assert MarriagePrepSession.COMMUNICATION == "communication"

    def test_theology_of_body(self):
        assert MarriagePrepSession.THEOLOGY_OF_BODY == "theology_of_body"

    def test_family_planning(self):
        assert MarriagePrepSession.FAMILY_PLANNING == "family_planning"

    def test_prayer_in_family(self):
        assert MarriagePrepSession.PRAYER_IN_FAMILY == "prayer_in_family"

    def test_modern_challenges(self):
        assert MarriagePrepSession.MODERN_CHALLENGES == "modern_challenges"

    def test_vision(self):
        assert MarriagePrepSession.VISION == "vision"


class TestSessions:
    def test_exactly_8_sessions(self):
        assert len(SESSIONS) == 8

    def test_unique_session_ids(self):
        ids = [s.session_id for s in SESSIONS]
        assert len(ids) == len(set(ids))

    def test_numbers_1_to_8(self):
        numbers = sorted(s.number for s in SESSIONS)
        assert numbers == list(range(1, 9))

    def test_all_have_non_empty_title(self):
        for s in SESSIONS:
            assert s.title.strip(), f"Session {s.session_id} has empty title"

    def test_all_have_non_empty_subtitle(self):
        for s in SESSIONS:
            assert s.subtitle.strip()

    def test_all_have_scripture_refs(self):
        for s in SESSIONS:
            assert len(s.scripture) >= 2, f"{s.session_id} needs scripture refs"

    def test_all_have_ccc_refs(self):
        for s in SESSIONS:
            assert len(s.ccc_refs) >= 1

    def test_all_have_key_questions(self):
        for s in SESSIONS:
            assert len(s.key_questions) >= 2

    def test_all_have_couple_exercise(self):
        for s in SESSIONS:
            assert s.couple_exercise.strip()

    def test_all_have_prayer(self):
        for s in SESSIONS:
            assert s.prayer.strip()

    def test_default_duration_1_5_hours(self):
        for s in SESSIONS:
            assert s.duration_hours == 1.5

    def test_humanae_vitae_session_present(self):
        docs = [s.key_document for s in SESSIONS]
        assert any("Humanae Vitae" in d for d in docs)

    def test_familiaris_consortio_session_present(self):
        docs = [s.key_document for s in SESSIONS]
        assert any("Familiaris Consortio" in d for d in docs)

    def test_theology_of_body_session_present(self):
        docs = [s.key_document for s in SESSIONS]
        assert any("Teologia Ciała" in d or "Theology of the Body" in d for d in docs)

    def test_amoris_laetitia_present(self):
        docs = [s.key_document for s in SESSIONS]
        assert any("Amoris Laetitia" in d for d in docs)

    def test_session_1_has_genesis(self):
        s1 = SESSIONS[0]
        assert any("Rdz" in ref for ref in s1.scripture)

    def test_session_5_has_genesis_1_28(self):
        # Family planning — Rdz 1,28 (be fruitful)
        s5 = next(s for s in SESSIONS if s.number == 5)
        assert any("Rdz 1,28" in ref for ref in s5.scripture)


class TestGetProgram:
    def test_returns_8_items(self):
        svc = _marriage_svc()
        program = svc.get_program()
        assert len(program) == 8

    def test_all_have_required_keys(self):
        svc = _marriage_svc()
        required = {
            "session_id", "number", "title", "subtitle",
            "scripture", "ccc_refs", "key_document",
            "key_questions", "couple_exercise", "prayer", "duration_hours",
        }
        for item in svc.get_program():
            assert required <= set(item.keys())

    def test_numbers_in_order(self):
        svc = _marriage_svc()
        numbers = [item["number"] for item in svc.get_program()]
        assert numbers == list(range(1, 9))

    def test_session_ids_unique(self):
        svc = _marriage_svc()
        ids = [item["session_id"] for item in svc.get_program()]
        assert len(ids) == len(set(ids))


class TestGetSession:
    def test_found_returns_dict(self):
        svc = _marriage_svc()
        result = svc.get_session("mp_01_sacrament")
        assert result is not None
        assert result["session_id"] == "mp_01_sacrament"

    def test_not_found_returns_none(self):
        svc = _marriage_svc()
        result = svc.get_session("nonexistent_session")
        assert result is None

    def test_returned_dict_has_all_required_keys(self):
        svc = _marriage_svc()
        result = svc.get_session("mp_04_tob")
        assert result is not None
        required = {
            "session_id", "number", "title", "subtitle",
            "scripture", "ccc_refs", "key_document",
            "key_questions", "couple_exercise", "prayer",
        }
        assert required <= set(result.keys())

    def test_theology_of_body_session_found(self):
        svc = _marriage_svc()
        result = svc.get_session("mp_04_tob")
        assert result is not None
        assert "Ciała" in result["title"] or "TOB" in result["title"] or "Teologia" in result["title"] or result["number"] == 4

    def test_all_sessions_retrievable_by_id(self):
        svc = _marriage_svc()
        for s in SESSIONS:
            result = svc.get_session(s.session_id)
            assert result is not None, f"{s.session_id} not retrievable"

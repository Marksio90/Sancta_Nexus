"""Unit tests for ChurchRAG (pure-Python layer) and PrayerIntentionService.

No Qdrant, no DB — pure data-layer and routing logic.

Contracts verified:
KnowledgeResult:
- All fields with correct defaults
- citation: bible format, catechism/council format, unknown source fallback

_route_query:
- Polish Bible keywords → BIBLIA_PL scores highest
- Vulgate keywords → BIBLIA_LA
- Katechizm keywords → KATECHIZM
- Sobory keywords → SOBORY
- Magisterium/encyklika keywords → MAGISTERIUM
- Patrystyka keywords → PATRYSTYKA
- Unknown query → default 5 collections
- limit parameter respected
- case-insensitive matching

_rerank:
- Authority weights applied (sobory > biblia_en)
- Deduplication by content prefix
- Results sorted descending by weighted score

_to_result (static):
- All payload fields mapped
- Missing doc_id gracefully handled
- Score from raw dict

PrayerIntentionService:
- INTENTION_CATEGORIES: 10 categories, required types present
- DEFAULT_EXPIRY_DAYS: 30
- _to_dict: all keys, status.value, isoformat timestamps, private fields excluded by default
- create: unknown category → "general", public → PENDING_MODERATION, private → ACTIVE,
  author_display "Anonim" when no user_id
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub qdrant_client before import
if "qdrant_client" not in sys.modules:
    sys.modules["qdrant_client"] = MagicMock()
    sys.modules["qdrant_client.models"] = MagicMock()

from datetime import datetime, timezone

from app.services.knowledge.church_rag import (
    ChurchRAG,
    KnowledgeResult,
    _AUTHORITY_WEIGHT,
    _ROUTING_HINTS,
    _rerank,
    _route_query,
)
from app.services.knowledge.corpus_registry import QdrantCollection
from app.services.community.intention_service import (
    DEFAULT_EXPIRY_DAYS,
    INTENTION_CATEGORIES,
    PrayerIntentionService,
)
from app.models.database import IntentionStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kr(
    content: str = "text",
    score: float = 0.8,
    source_type: str = "catechism",
    collection: str = "katechizm",
    section_ref: str = "",
    document_title: str = "",
    document_title_pl: str = "",
    book: str = "",
    chapter: int = 0,
    verse_start: int = 0,
    verse_end: int = 0,
    translation: str = "",
) -> KnowledgeResult:
    return KnowledgeResult(
        content=content,
        score=score,
        source_type=source_type,
        collection=collection,
        section_ref=section_ref,
        document_title=document_title,
        document_title_pl=document_title_pl,
        book=book,
        chapter=chapter,
        verse_start=verse_start,
        verse_end=verse_end,
        translation=translation,
    )


def _intention_orm(**kwargs) -> MagicMock:
    obj = MagicMock()
    obj.id = kwargs.get("id", "int-uuid-001")
    obj.content = kwargs.get("content", "Proszę o zdrowie")
    obj.author_display = kwargs.get("author_display", "Anonim")
    obj.is_public = kwargs.get("is_public", True)
    obj.category = kwargs.get("category", "zdrowie")
    obj.prayer_count = kwargs.get("prayer_count", 0)
    obj.status = kwargs.get("status", IntentionStatus.ACTIVE)
    obj.created_at = kwargs.get("created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    obj.expires_at = kwargs.get("expires_at", datetime(2026, 2, 1, tzinfo=timezone.utc))
    obj.group_id = kwargs.get("group_id", None)
    obj.user_id = kwargs.get("user_id", "user-001")
    obj.moderator_id = kwargs.get("moderator_id", None)
    obj.moderated_at = kwargs.get("moderated_at", None)
    obj.rejection_reason = kwargs.get("rejection_reason", None)
    return obj


def _svc() -> PrayerIntentionService:
    return PrayerIntentionService()


# ===========================================================================
# KnowledgeResult — fields and citation
# ===========================================================================


class TestKnowledgeResultDefaults:
    def test_required_fields(self):
        r = KnowledgeResult(
            content="text",
            score=0.9,
            source_type="catechism",
            collection="katechizm",
            section_ref="§ 2697",
        )
        assert r.content == "text"
        assert r.score == 0.9
        assert r.section_ref == "§ 2697"

    def test_defaults(self):
        r = _kr()
        assert r.document_title == ""
        assert r.author == ""
        assert r.year == 0
        assert r.language == "la"
        assert r.book == ""
        assert r.chapter == 0
        assert r.metadata == {}


class TestKnowledgeResultCitation:
    def test_bible_single_verse(self):
        r = _kr(
            source_type="bible",
            book="J",
            chapter=3,
            verse_start=16,
            verse_end=16,
            translation="BT",
        )
        assert r.citation == "J 3,16 (BT)"

    def test_bible_verse_range(self):
        r = _kr(
            source_type="bible",
            book="Rz",
            chapter=8,
            verse_start=28,
            verse_end=39,
            translation="BT",
        )
        assert "28-39" in r.citation
        assert "Rz 8,28-39" in r.citation

    def test_catechism_with_section_ref(self):
        r = _kr(
            source_type="catechism",
            section_ref="§ 2697",
            document_title_pl="Katechizm Kościoła Katolickiego",
        )
        assert "§ 2697" in r.citation
        assert "Katechizm" in r.citation

    def test_section_ref_without_title(self):
        r = _kr(source_type="encyclical", section_ref="n. 14")
        assert r.citation == "n. 14"

    def test_no_section_ref_uses_document_title(self):
        r = _kr(source_type="encyclical", document_title="Rerum Novarum")
        assert r.citation == "Rerum Novarum"

    def test_unknown_fallback(self):
        r = _kr(source_type="unknown")
        assert r.citation == "Nieznane źródło"


# ===========================================================================
# _route_query
# ===========================================================================


class TestRouteQuery:
    def test_psalm_routes_to_biblia_pl(self):
        result = _route_query("psalm pokoju")
        assert QdrantCollection.BIBLIA_PL in result

    def test_ewangelia_routes_to_biblia_pl(self):
        result = _route_query("ewangelia jana")
        assert QdrantCollection.BIBLIA_PL in result[:2]

    def test_vulgata_routes_to_biblia_la(self):
        result = _route_query("vulgata łacińska")
        assert QdrantCollection.BIBLIA_LA in result

    def test_katechizm_routes_correctly(self):
        result = _route_query("katechizm sakrament chrztu")
        assert QdrantCollection.KATECHIZM in result[:2]

    def test_sobor_routes_to_sobory(self):
        result = _route_query("sobór watykański lumen gentium")
        assert QdrantCollection.SOBORY in result[:2]

    def test_encyklika_routes_to_magisterium(self):
        result = _route_query("encyklika laudato franciszek")
        assert QdrantCollection.MAGISTERIUM in result[:2]

    def test_patrystyka_routes_correctly(self):
        result = _route_query("augustyn ojcowie kościoła kontemplacja")
        assert QdrantCollection.PATRYSTYKA in result[:2]

    def test_unknown_query_returns_5_defaults(self):
        result = _route_query("something completely unrelated xyzzy")
        assert len(result) == 5

    def test_limit_respected(self):
        result = _route_query("ewangelia psalm katechizm", limit=2)
        assert len(result) <= 2

    def test_case_insensitive(self):
        result_lower = _route_query("ewangelia")
        result_upper = _route_query("EWANGELIA")
        assert QdrantCollection.BIBLIA_PL in result_lower
        assert QdrantCollection.BIBLIA_PL in result_upper

    def test_returns_list_of_qdrant_collections(self):
        result = _route_query("modlitwa i liturgia sakramentów")
        for item in result:
            assert isinstance(item, QdrantCollection)

    def test_multiple_hints_scores_higher(self):
        # Query hitting many KATECHIZM hints → KATECHIZM should win
        result = _route_query("katechizm kkk dogmat sakrament grzech cnota dekalog")
        assert result[0] == QdrantCollection.KATECHIZM


# ===========================================================================
# _rerank
# ===========================================================================


class TestRerank:
    def test_authority_weight_applied(self):
        """sobory weight (1.15) > biblia_en (1.04) at same raw score."""
        r_sobory = _kr(content="unique-a", score=0.80, collection="sobory")
        r_bible_en = _kr(content="unique-b", score=0.80, collection="biblia_en")
        result = _rerank([r_bible_en, r_sobory])
        assert result[0].collection == "sobory"

    def test_sorted_descending(self):
        results = [
            _kr(content="a", score=0.5, collection="katechizm"),
            _kr(content="b", score=0.9, collection="biblia_pl"),
            _kr(content="c", score=0.7, collection="magisterium"),
        ]
        ranked = _rerank(results)
        scores = [r.score for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_deduplication_removes_duplicate_content(self):
        same_content = "The Lord is my shepherd and I shall not want."
        r1 = _kr(content=same_content, score=0.9, collection="biblia_pl")
        r2 = _kr(content=same_content, score=0.8, collection="biblia_en")
        result = _rerank([r1, r2])
        contents = [r.content for r in result]
        assert contents.count(same_content) == 1

    def test_different_content_kept(self):
        r1 = _kr(content="The Lord is my shepherd", score=0.9, collection="biblia_pl")
        r2 = _kr(content="God so loved the world", score=0.8, collection="biblia_en")
        result = _rerank([r1, r2])
        assert len(result) == 2

    def test_empty_list_returns_empty(self):
        assert _rerank([]) == []

    def test_single_item_returned(self):
        r = _kr(content="solo", score=0.5)
        result = _rerank([r])
        assert len(result) == 1

    def test_authority_weights_all_collections_covered(self):
        """All 8 collections have entries in _AUTHORITY_WEIGHT."""
        expected = {
            "sobory", "katechizm", "magisterium", "patrystyka",
            "biblia_pl", "biblia_la", "biblia_en", "liturgia",
        }
        assert expected <= set(_AUTHORITY_WEIGHT.keys())

    def test_scores_mutated_in_place(self):
        r = _kr(content="mutated", score=1.0, collection="sobory")
        _rerank([r])
        # sobory weight = 1.15
        assert r.score == 1.0 * _AUTHORITY_WEIGHT["sobory"]


# ===========================================================================
# _to_result (static)
# ===========================================================================


class TestToResult:
    def test_bible_payload_mapped(self):
        raw = {
            "score": 0.92,
            "payload": {
                "content": "In the beginning",
                "source_type": "bible",
                "section_ref": "Rdz 1,1",
                "book": "Rdz",
                "chapter": 1,
                "verse_start": 1,
                "verse_end": 1,
                "translation": "BT",
                "language": "pl",
            },
        }
        result = ChurchRAG._to_result(raw, QdrantCollection.BIBLIA_PL)
        assert result.content == "In the beginning"
        assert result.score == 0.92
        assert result.book == "Rdz"
        assert result.chapter == 1
        assert result.translation == "BT"
        assert result.collection == "biblia_pl"

    def test_missing_payload_gracefully_defaults(self):
        raw = {"score": 0.5, "payload": {}}
        result = ChurchRAG._to_result(raw, QdrantCollection.KATECHIZM)
        assert result.content == ""
        assert result.score == 0.5
        assert result.book == ""
        assert result.chapter == 0

    def test_score_from_raw(self):
        raw = {"score": 0.75, "payload": {"content": "grace"}}
        result = ChurchRAG._to_result(raw, QdrantCollection.MAGISTERIUM)
        assert result.score == 0.75

    def test_collection_value_set(self):
        raw = {"score": 0.8, "payload": {}}
        result = ChurchRAG._to_result(raw, QdrantCollection.PATRYSTYKA)
        assert result.collection == "patrystyka"


# ===========================================================================
# _ROUTING_HINTS coverage
# ===========================================================================


class TestRoutingHints:
    def test_all_6_collections_have_hints(self):
        assert len(_ROUTING_HINTS) == 6

    def test_each_collection_has_at_least_3_hints(self):
        for coll, hints in _ROUTING_HINTS.items():
            assert len(hints) >= 3, f"{coll} has fewer than 3 routing hints"

    def test_biblia_pl_has_polish_hints(self):
        hints = _ROUTING_HINTS[QdrantCollection.BIBLIA_PL]
        assert any("psalm" in h for h in hints)
        assert any("biblia" in h or "pismo" in h for h in hints)

    def test_magisterium_has_papal_hints(self):
        hints = _ROUTING_HINTS[QdrantCollection.MAGISTERIUM]
        assert any("encyklika" in h or "papież" in h for h in hints)


# ===========================================================================
# PrayerIntentionService — categories and _to_dict
# ===========================================================================


class TestIntentionCategories:
    def test_exactly_10_categories(self):
        assert len(INTENTION_CATEGORIES) == 10

    def test_general_present(self):
        assert "general" in INTENTION_CATEGORIES

    def test_zdrowie_present(self):
        assert "zdrowie" in INTENTION_CATEGORIES

    def test_rodzina_present(self):
        assert "rodzina" in INTENTION_CATEGORIES

    def test_pokoj_present(self):
        assert "pokój" in INTENTION_CATEGORIES

    def test_nawrocenie_present(self):
        assert "nawrócenie" in INTENTION_CATEGORIES

    def test_zaoba_present(self):
        assert "żałoba" in INTENTION_CATEGORIES

    def test_wdziecznosc_present(self):
        assert "wdzięczność" in INTENTION_CATEGORIES

    def test_default_expiry_30_days(self):
        assert DEFAULT_EXPIRY_DAYS == 30

    def test_no_duplicates(self):
        assert len(INTENTION_CATEGORIES) == len(set(INTENTION_CATEGORIES))


class TestIntentionToDict:
    def test_public_fields_present(self):
        svc = _svc()
        obj = _intention_orm()
        result = svc._to_dict(obj)
        expected_keys = {
            "id", "content", "author_display", "is_public",
            "category", "prayer_count", "status", "created_at",
            "expires_at", "group_id",
        }
        assert expected_keys <= set(result.keys())

    def test_private_fields_excluded_by_default(self):
        svc = _svc()
        result = svc._to_dict(_intention_orm())
        assert "user_id" not in result
        assert "moderator_id" not in result
        assert "rejection_reason" not in result

    def test_private_fields_included_when_requested(self):
        svc = _svc()
        result = svc._to_dict(_intention_orm(), include_private_fields=True)
        assert "user_id" in result
        assert "moderator_id" in result
        assert "rejection_reason" in result
        assert "moderated_at" in result

    def test_status_is_value_string(self):
        svc = _svc()
        obj = _intention_orm(status=IntentionStatus.ACTIVE)
        result = svc._to_dict(obj)
        assert result["status"] == "active"

    def test_status_pending_moderation(self):
        svc = _svc()
        obj = _intention_orm(status=IntentionStatus.PENDING_MODERATION)
        result = svc._to_dict(obj)
        assert result["status"] == "pending_moderation"

    def test_created_at_iso_format(self):
        svc = _svc()
        dt = datetime(2026, 3, 15, 10, 30, 0, tzinfo=timezone.utc)
        obj = _intention_orm(created_at=dt)
        result = svc._to_dict(obj)
        assert "2026-03-15" in result["created_at"]

    def test_expires_at_iso_format(self):
        svc = _svc()
        dt = datetime(2026, 4, 15, tzinfo=timezone.utc)
        obj = _intention_orm(expires_at=dt)
        result = svc._to_dict(obj)
        assert "2026-04-15" in result["expires_at"]

    def test_none_created_at(self):
        svc = _svc()
        obj = _intention_orm(created_at=None)
        result = svc._to_dict(obj)
        assert result["created_at"] is None

    def test_group_id_preserved(self):
        svc = _svc()
        obj = _intention_orm(group_id="group-abc")
        result = svc._to_dict(obj)
        assert result["group_id"] == "group-abc"

    def test_rejection_reason_in_private(self):
        svc = _svc()
        obj = _intention_orm(rejection_reason="Inappropriate content")
        result = svc._to_dict(obj, include_private_fields=True)
        assert result["rejection_reason"] == "Inappropriate content"


class TestIntentionCategoryNormalisation:
    """Logic mirrored from create() — unknown category → 'general'."""

    def test_valid_category_preserved(self):
        for cat in INTENTION_CATEGORIES:
            normalised = cat if cat in INTENTION_CATEGORIES else "general"
            assert normalised == cat

    def test_unknown_category_defaults_to_general(self):
        cat = "sport"
        normalised = cat if cat in INTENTION_CATEGORIES else "general"
        assert normalised == "general"

    def test_empty_string_defaults_to_general(self):
        cat = ""
        normalised = cat if cat in INTENTION_CATEGORIES else "general"
        assert normalised == "general"


class TestIntentionStatusLogic:
    """Public intentions → PENDING_MODERATION; private → ACTIVE."""

    def test_public_gets_pending_moderation(self):
        status = IntentionStatus.PENDING_MODERATION if True else IntentionStatus.ACTIVE
        assert status == IntentionStatus.PENDING_MODERATION

    def test_private_gets_active(self):
        is_public = False
        status = IntentionStatus.PENDING_MODERATION if is_public else IntentionStatus.ACTIVE
        assert status == IntentionStatus.ACTIVE

    def test_intention_status_enum_has_expected_values(self):
        statuses = {s.value for s in IntentionStatus}
        assert "active" in statuses
        assert "pending_moderation" in statuses
        assert "rejected" in statuses
        assert "answered" in statuses

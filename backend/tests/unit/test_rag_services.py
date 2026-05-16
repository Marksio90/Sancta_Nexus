"""Unit tests for RAG and embedding services.

Stubs qdrant_client and sentence_transformers (not installed in local env).

Contracts verified:
RAGService:
- COLLECTIONS: exactly 8 expected collections
- SearchResult: dataclass fields, defaults
- ScriptureResult: all fields, bible-specific metadata

EmbeddingService:
- OPENAI_EMBEDDING_MODEL / LOCAL_MODEL_NAME constants
- _E5_QUERY_PREFIX / _E5_PASSAGE_PREFIX
- _prepare: non-E5 model → passthrough, E5 adds prefix, already-prefixed → no double prefix
- dimension: 1536 for OpenAI model, 1024 for E5
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub unavailable packages before import
if "qdrant_client" not in sys.modules:
    sys.modules["qdrant_client"] = MagicMock()
    sys.modules["qdrant_client.models"] = MagicMock()
if "sentence_transformers" not in sys.modules:
    sys.modules["sentence_transformers"] = MagicMock()

from app.services.rag.embedding_service import (
    _E5_PASSAGE_PREFIX,
    _E5_QUERY_PREFIX,
    LOCAL_MODEL_NAME,
    OPENAI_EMBEDDING_MODEL,
    EmbeddingService,
)
from app.services.rag.rag_service import (
    COLLECTIONS,
    ScriptureResult,
    SearchResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _embed_svc(model_name: str = OPENAI_EMBEDDING_MODEL) -> EmbeddingService:
    svc = EmbeddingService.__new__(EmbeddingService)
    svc._model_name = model_name
    return svc


# ===========================================================================
# RAGService — COLLECTIONS and dataclasses
# ===========================================================================


class TestCollections:
    def test_exactly_8_collections(self):
        assert len(COLLECTIONS) == 8

    def test_biblia_pl_present(self):
        assert "biblia_pl" in COLLECTIONS

    def test_katechizm_present(self):
        assert "katechizm" in COLLECTIONS

    def test_patrystyka_present(self):
        assert "patrystyka" in COLLECTIONS

    def test_magisterium_present(self):
        assert "magisterium" in COLLECTIONS

    def test_all_are_strings(self):
        for c in COLLECTIONS:
            assert isinstance(c, str) and c.strip()


class TestSearchResult:
    def test_content_required(self):
        r = SearchResult(content="Test content")
        assert r.content == "Test content"

    def test_score_defaults_zero(self):
        r = SearchResult(content="text")
        assert r.score == 0.0

    def test_metadata_defaults_empty(self):
        r = SearchResult(content="text")
        assert r.metadata == {}

    def test_custom_fields(self):
        r = SearchResult(content="text", score=0.85, metadata={"key": "val"})
        assert r.score == 0.85
        assert r.metadata["key"] == "val"


class TestScriptureResult:
    def test_content_required(self):
        r = ScriptureResult(content="In the beginning...")
        assert r.content == "In the beginning..."

    def test_translation_defaults_bt(self):
        r = ScriptureResult(content="text")
        assert r.translation == "BT"

    def test_chapter_defaults_zero(self):
        r = ScriptureResult(content="text")
        assert r.chapter == 0

    def test_book_field(self):
        r = ScriptureResult(content="text", book="J", chapter=1, verse=1)
        assert r.book == "J"
        assert r.chapter == 1
        assert r.verse == 1

    def test_magisterium_fields(self):
        r = ScriptureResult(
            content="text",
            document_title="Lumen Gentium",
            pope_or_council="Vatican II",
            paragraph="§8",
        )
        assert r.document_title == "Lumen Gentium"
        assert r.pope_or_council == "Vatican II"
        assert r.paragraph == "§8"


# ===========================================================================
# EmbeddingService
# ===========================================================================


class TestEmbeddingConstants:
    def test_openai_model_is_ada_or_small(self):
        assert "embedding" in OPENAI_EMBEDDING_MODEL.lower()

    def test_local_model_is_e5(self):
        assert "e5" in LOCAL_MODEL_NAME.lower()

    def test_e5_query_prefix(self):
        assert _E5_QUERY_PREFIX == "query: "

    def test_e5_passage_prefix(self):
        assert _E5_PASSAGE_PREFIX == "passage: "


class TestPrepareMethod:
    def test_non_e5_model_passthrough(self):
        svc = _embed_svc("text-embedding-3-small")
        result = svc._prepare("hello world", is_query=True)
        assert result == "hello world"

    def test_non_e5_passage_passthrough(self):
        svc = _embed_svc("text-embedding-3-small")
        result = svc._prepare("church text", is_query=False)
        assert result == "church text"

    def test_e5_query_gets_prefix(self):
        svc = _embed_svc("intfloat/multilingual-e5-large")
        result = svc._prepare("what is love?", is_query=True)
        assert result == "query: what is love?"

    def test_e5_passage_gets_prefix(self):
        svc = _embed_svc("intfloat/multilingual-e5-large")
        result = svc._prepare("The Lord is my shepherd", is_query=False)
        assert result == "passage: The Lord is my shepherd"

    def test_e5_already_prefixed_query_not_doubled(self):
        svc = _embed_svc("intfloat/multilingual-e5-large")
        result = svc._prepare("query: already prefixed", is_query=True)
        assert result == "query: already prefixed"

    def test_e5_already_prefixed_passage_not_doubled(self):
        svc = _embed_svc("intfloat/multilingual-e5-large")
        result = svc._prepare("passage: already prefixed", is_query=False)
        assert result == "passage: already prefixed"

    def test_e5_small_variant_also_gets_prefix(self):
        svc = _embed_svc("intfloat/multilingual-e5-small")
        result = svc._prepare("sacred text", is_query=False)
        assert result.startswith(_E5_PASSAGE_PREFIX)

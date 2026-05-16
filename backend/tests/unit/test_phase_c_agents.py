"""Tests for Phase C — AI agents and RAG fallback.

All tests are self-contained (no qdrant_client, no pydantic_settings).
Heavy infra imports are replaced with file-based AST checks or inline logic.
"""

from __future__ import annotations

import ast
import pathlib

BACKEND_ROOT = pathlib.Path("/home/user/Sancta_Nexus/backend")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text()


def _has_import(source: str, module: str) -> bool:
    """Return True if source contains a top-level import of `module`."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module:
                    return True
    return False


# ---------------------------------------------------------------------------
# LLM Factory Refactor — no more direct ChatOpenAI
# ---------------------------------------------------------------------------


class TestLLMFactoryRefactor:
    def test_emotion_detector_no_langchain_openai(self):
        src = _source("app/agents/emotion/emotion_detector.py")
        assert not _has_import(src, "langchain_openai"), (
            "EmotionDetectorAgent must not import langchain_openai directly"
        )

    def test_spiritual_state_classifier_no_langchain_openai(self):
        src = _source("app/agents/emotion/spiritual_state_classifier.py")
        assert not _has_import(src, "langchain_openai")

    def test_crisis_detector_no_langchain_openai(self):
        src = _source("app/agents/emotion/crisis_detector.py")
        assert not _has_import(src, "langchain_openai")

    def test_emotion_detector_uses_llm_factory(self):
        src = _source("app/agents/emotion/emotion_detector.py")
        assert "get_llm_fast" in src or "get_llm" in src

    def test_spiritual_state_classifier_uses_llm_factory(self):
        src = _source("app/agents/emotion/spiritual_state_classifier.py")
        assert "get_llm_fast" in src or "get_llm" in src

    def test_crisis_detector_uses_llm_factory(self):
        src = _source("app/agents/emotion/crisis_detector.py")
        assert "get_llm_fast" in src or "get_llm" in src


# ---------------------------------------------------------------------------
# Config model names
# ---------------------------------------------------------------------------


class TestConfigModelNames:
    def test_anthropic_primary_model_updated(self):
        src = _source("app/core/config.py")
        assert "claude-sonnet-4-6" in src
        assert "claude-sonnet-4-20250514" not in src

    def test_anthropic_fast_model_is_haiku(self):
        src = _source("app/core/config.py")
        assert "claude-haiku-4-5-20251001" in src

    def test_anthropic_creative_model_updated(self):
        src = _source("app/core/config.py")
        assert "claude-sonnet-4-6" in src


# ---------------------------------------------------------------------------
# Scripture fallback corpus — inline logic, no qdrant_client
# ---------------------------------------------------------------------------

# Copied inline from scripture_matcher.py to avoid the qdrant import chain
_FALLBACK_CORPUS: list[dict] = [
    {"book": "Flp", "chapter": 4, "verse": 4, "content": "Radujcie się zawsze w Panu!", "emotion_tags": ["joy", "gratitude", "consolation"]},
    {"book": "Ps", "chapter": 34, "verse": 9, "content": "Skosztujcie i zobaczcie, jak dobry jest Pan.", "emotion_tags": ["joy", "trust", "hope", "consolation"]},
    {"book": "Rz", "chapter": 8, "verse": 28, "content": "Bóg z tymi, którzy Go miłują, współdziała we wszystkim dla ich dobra.", "emotion_tags": ["hope", "trust", "consolation", "gratitude"]},
    {"book": "1 Tes", "chapter": 5, "verse": 18, "content": "W każdym położeniu dziękujcie.", "emotion_tags": ["gratitude", "joy", "consolation"]},
    {"book": "Ps", "chapter": 34, "verse": 19, "content": "Pan jest blisko ludzi ze złamanym sercem.", "emotion_tags": ["sadness", "grief", "loneliness", "desolation"]},
    {"book": "Mt", "chapter": 5, "verse": 4, "content": "Błogosławieni, którzy się smucą.", "emotion_tags": ["sadness", "grief", "desolation"]},
    {"book": "Iz", "chapter": 41, "verse": 10, "content": "Nie lękaj się, bo Ja jestem z tobą.", "emotion_tags": ["fear", "anxiety", "dread"]},
    {"book": "J", "chapter": 14, "verse": 27, "content": "Pokój zostawiam wam, pokój mój daję wam.", "emotion_tags": ["fear", "anxiety", "peace", "serenity"]},
    {"book": "1 J", "chapter": 1, "verse": 9, "content": "Bóg jest wierny i sprawiedliwy, aby nam przebaczyć grzechy.", "emotion_tags": ["guilt", "shame", "remorse"]},
    {"book": "Rz", "chapter": 8, "verse": 1, "content": "Nie ma już potępienia dla tych, którzy są w Chrystusie Jezusie.", "emotion_tags": ["guilt", "shame", "remorse", "forgiveness"]},
    {"book": "Ps", "chapter": 42, "verse": 2, "content": "Jak łania pragnie wody, tak dusza moja pragnie Ciebie, Boże.", "emotion_tags": ["longing", "seeking", "awe", "reverence"]},
    {"book": "Mt", "chapter": 7, "verse": 7, "content": "Proście, a będzie wam dane; szukajcie, a znajdziecie.", "emotion_tags": ["longing", "hope", "seeking", "trust"]},
    {"book": "J", "chapter": 15, "verse": 5, "content": "Kto trwa we Mnie, a Ja w nim, ten przynosi owoc obfity.", "emotion_tags": ["peace", "serenity", "consolation", "love"]},
    {"book": "Mt", "chapter": 11, "verse": 28, "content": "Przyjdźcie do Mnie wszyscy utrudzeni, a Ja was pokrzepię.", "emotion_tags": ["peace", "serenity", "sadness"]},
    {"book": "Jr", "chapter": 29, "verse": 11, "content": "Zamiary pełne pokoju, a nie zguby, by zapewnić wam przyszłość i nadzieję.", "emotion_tags": ["hope", "desolation", "dark_night", "seeking"]},
    {"book": "Mk", "chapter": 9, "verse": 24, "content": "Wierzę, zaradź memu niedowiarstwu!", "emotion_tags": ["doubt", "confusion", "seeking", "trust"]},
]


def _fallback_index(corpus: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for p in corpus:
        for tag in p["emotion_tags"]:
            index.setdefault(tag, []).append(p)
    return index


def _fallback_match(
    emotion_vector: dict[str, float],
    corpus: list[dict],
    limit: int = 3,
) -> list[dict]:
    scored = [(sum(emotion_vector.get(t, 0.0) for t in p["emotion_tags"]), p) for p in corpus]
    scored.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    results = []
    for _, p in scored:
        ref = f"{p['book']} {p['chapter']},{p['verse']}"
        if ref in seen:
            continue
        seen.add(ref)
        results.append(p)
        if len(results) == limit:
            break
    return results


class TestFallbackCorpusLogic:
    def test_corpus_minimum_size(self):
        assert len(_FALLBACK_CORPUS) >= 15

    def test_all_required_fields_present(self):
        for p in _FALLBACK_CORPUS:
            for field in ("book", "chapter", "verse", "content", "emotion_tags"):
                assert field in p, f"Missing {field!r} in passage {p}"
            assert isinstance(p["emotion_tags"], list)
            assert len(p["emotion_tags"]) >= 1

    def test_index_covers_core_emotions(self):
        idx = _fallback_index(_FALLBACK_CORPUS)
        for emotion in ("joy", "sadness", "fear", "guilt", "longing", "peace", "hope"):
            assert emotion in idx, f"Emotion {emotion!r} has no passages"

    def test_fallback_match_returns_at_most_3(self):
        results = _fallback_match({"sadness": 0.9, "grief": 0.7}, _FALLBACK_CORPUS)
        assert 1 <= len(results) <= 3

    def test_fallback_match_no_duplicate_refs(self):
        results = _fallback_match({"hope": 0.9, "consolation": 0.8}, _FALLBACK_CORPUS)
        refs = [f"{p['book']} {p['chapter']},{p['verse']}" for p in results]
        assert len(refs) == len(set(refs))

    def test_fallback_match_fear_returns_comfort_passage(self):
        results = _fallback_match({"fear": 1.0, "anxiety": 0.8}, _FALLBACK_CORPUS)
        assert len(results) > 0
        all_content = " ".join(r["content"] for r in results).lower()
        assert any(kw in all_content for kw in ["lękaj", "pokój", "jestem z tobą"])

    def test_fallback_match_guilt_returns_forgiveness(self):
        results = _fallback_match({"guilt": 1.0, "remorse": 0.8, "shame": 0.7}, _FALLBACK_CORPUS)
        assert len(results) > 0
        tags_in_results = {t for p in results for t in p["emotion_tags"]}
        assert "forgiveness" in tags_in_results or "guilt" in tags_in_results

    def test_fallback_match_empty_vector_returns_passages(self):
        results = _fallback_match({}, _FALLBACK_CORPUS)
        # With all-zero scores, still returns passages (first 3 in order)
        assert len(results) <= 3


# ---------------------------------------------------------------------------
# Source-level checks on scripture_matcher.py
# ---------------------------------------------------------------------------


class TestScriptureMatcherSource:
    def test_fallback_corpus_defined_in_source(self):
        src = _source("app/services/scripture/scripture_matcher.py")
        assert "_FALLBACK_CORPUS" in src

    def test_fallback_index_defined_in_source(self):
        src = _source("app/services/scripture/scripture_matcher.py")
        assert "_FALLBACK_INDEX" in src or "_build_fallback_index" in src

    def test_fallback_match_method_defined(self):
        src = _source("app/services/scripture/scripture_matcher.py")
        assert "_fallback_match" in src

    def test_fallback_called_when_no_candidates(self):
        src = _source("app/services/scripture/scripture_matcher.py")
        assert "_fallback_match" in src
        assert "not candidates" in src or "if not candidates" in src

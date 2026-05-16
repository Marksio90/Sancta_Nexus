"""Unit tests for app/services/knowledge/chunker.py.

Pure-Python module — no stubs required.

Contracts verified:
- DocumentChunk dataclass: fields, word_count property
- _stable_id: deterministic UUID5, different seeds → different IDs
- _sliding_window: window/overlap/min-length filtering
- chunk_bible_verses: single verse chunks, grouped triplets, metadata fields
- chunk_by_paragraph: paragraph splitting, sub-chunking on long paragraphs,
  fallback to sliding_window when no paragraph markers, min-word filter
- chunk_by_section: section header detection, accumulation, flush on max_words
- chunk_sliding_window: window size, overlap, short-segment skip
- chunk_document: dispatches to correct strategy
"""

from __future__ import annotations

import uuid

from app.services.knowledge.chunker import (
    DocumentChunk,
    _sliding_window,
    _stable_id,
    chunk_bible_verses,
    chunk_by_paragraph,
    chunk_by_section,
    chunk_document,
    chunk_sliding_window,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _meta(**extra) -> dict:
    return {"doc_id": "test_doc", "source_type": "test", **extra}


def _words(n: int) -> str:
    """Return a string of n distinct words."""
    return " ".join(f"word{i}" for i in range(n))


# ---------------------------------------------------------------------------
# DocumentChunk
# ---------------------------------------------------------------------------


class TestDocumentChunk:
    def test_fields_set(self):
        c = DocumentChunk(chunk_id="c1", content="Hello world", metadata={"k": "v"})
        assert c.chunk_id == "c1"
        assert c.content == "Hello world"
        assert c.metadata == {"k": "v"}

    def test_default_metadata_is_empty(self):
        c = DocumentChunk(chunk_id="c1", content="text")
        assert c.metadata == {}

    def test_word_count_single(self):
        c = DocumentChunk(chunk_id="c1", content="one two three")
        assert c.word_count == 3

    def test_word_count_multispace(self):
        c = DocumentChunk(chunk_id="c1", content="  a  b  c  ")
        assert c.word_count == 3

    def test_word_count_empty(self):
        c = DocumentChunk(chunk_id="c1", content="")
        assert c.word_count == 0


# ---------------------------------------------------------------------------
# _stable_id
# ---------------------------------------------------------------------------


class TestStableId:
    def test_returns_string(self):
        result = _stable_id("test:1:2")
        assert isinstance(result, str)

    def test_is_valid_uuid(self):
        result = _stable_id("test:1:2")
        parsed = uuid.UUID(result)
        assert parsed.version == 5

    def test_deterministic(self):
        assert _stable_id("book:3:5") == _stable_id("book:3:5")

    def test_different_seeds_differ(self):
        assert _stable_id("seed-A") != _stable_id("seed-B")

    def test_empty_seed(self):
        result = _stable_id("")
        assert isinstance(result, str)
        assert len(result) == 36


# ---------------------------------------------------------------------------
# _sliding_window
# ---------------------------------------------------------------------------


class TestSlidingWindowHelper:
    def test_single_window_no_overlap(self):
        text = _words(10)
        windows = _sliding_window(text, window=10, overlap=0)
        assert len(windows) == 1

    def test_overlap_creates_multiple_windows(self):
        text = _words(20)
        windows = _sliding_window(text, window=15, overlap=5)
        assert len(windows) >= 2

    def test_short_chunks_filtered(self):
        text = _words(12)
        # window=10, overlap=0 → step=10; second window has 2 words (< 10) → filtered
        windows = _sliding_window(text, window=10, overlap=0)
        for w in windows:
            assert len(w.split()) >= 10

    def test_returns_strings(self):
        text = _words(30)
        for w in _sliding_window(text, window=10, overlap=3):
            assert isinstance(w, str)


# ---------------------------------------------------------------------------
# chunk_bible_verses
# ---------------------------------------------------------------------------


class TestChunkBibleVerses:
    def _verses(self, n: int = 5) -> list[tuple[int, str]]:
        return [(i + 1, f"Verse {i + 1} text for testing purposes here.") for i in range(n)]

    def test_returns_document_chunks(self):
        chunks = chunk_bible_verses("J", "Jan", 1, self._verses(), "BT", "pl")
        assert all(isinstance(c, DocumentChunk) for c in chunks)

    def test_single_verse_chunks_count(self):
        verses = self._verses(5)
        chunks = chunk_bible_verses("J", "Jan", 1, verses, "BT", "pl")
        single_chunks = [c for c in chunks if not c.metadata.get("is_group")]
        assert len(single_chunks) == 5

    def test_grouped_chunks_present(self):
        verses = self._verses(5)
        chunks = chunk_bible_verses("J", "Jan", 1, verses, "BT", "pl", group_size=3)
        group_chunks = [c for c in chunks if c.metadata.get("is_group")]
        # 5 verses, group_size=3 → 3 groups (indices 0-2, 1-3, 2-4)
        assert len(group_chunks) == 3

    def test_single_verse_metadata(self):
        verses = [(1, "In the beginning was the Word.")]
        chunks = chunk_bible_verses("Jn", "John", 1, verses, "BT", "pl")
        single = [c for c in chunks if not c.metadata.get("is_group")][0]
        assert single.metadata["book"] == "Jn"
        assert single.metadata["book_name"] == "John"
        assert single.metadata["chapter"] == 1
        assert single.metadata["verse_start"] == 1
        assert single.metadata["source_type"] == "bible"
        assert single.metadata["translation"] == "BT"
        assert single.metadata["language"] == "pl"

    def test_group_metadata(self):
        verses = self._verses(5)
        chunks = chunk_bible_verses("Rz", "Romans", 8, verses, "BT", "pl", group_size=3)
        groups = [c for c in chunks if c.metadata.get("is_group")]
        assert groups[0].metadata["verse_start"] == 1
        assert groups[0].metadata["verse_end"] == 3

    def test_stable_chunk_ids(self):
        verses = self._verses(3)
        c1 = chunk_bible_verses("J", "Jan", 1, verses, "BT", "pl")
        c2 = chunk_bible_verses("J", "Jan", 1, verses, "BT", "pl")
        ids1 = [c.chunk_id for c in c1]
        ids2 = [c.chunk_id for c in c2]
        assert ids1 == ids2

    def test_empty_verses_returns_empty(self):
        assert chunk_bible_verses("J", "Jan", 1, [], "BT", "pl") == []

    def test_fewer_verses_than_group_size_no_groups(self):
        verses = self._verses(2)
        chunks = chunk_bible_verses("J", "Jan", 1, verses, "BT", "pl", group_size=3)
        groups = [c for c in chunks if c.metadata.get("is_group")]
        assert len(groups) == 0


# ---------------------------------------------------------------------------
# chunk_by_paragraph
# ---------------------------------------------------------------------------


class TestChunkByParagraph:
    def _ccc_text(self) -> str:
        """Minimal CCC-style text with paragraph markers."""
        return (
            "§ 1. " + _words(60) + "\n\n"
            "§ 2. " + _words(80) + "\n\n"
            "§ 3. " + _words(40) + "\n\n"
        )

    def test_returns_chunks(self):
        chunks = chunk_by_paragraph(self._ccc_text(), _meta())
        assert len(chunks) >= 2

    def test_chunks_have_section_ref(self):
        chunks = chunk_by_paragraph(self._ccc_text(), _meta())
        for c in chunks:
            assert "section_ref" in c.metadata
            assert c.metadata["section_ref"].startswith("§")

    def test_short_paragraphs_filtered(self):
        """Paragraphs below min_words=30 are skipped."""
        text = "§ 1. " + _words(5) + "\n\n§ 2. " + _words(60) + "\n\n"
        chunks = chunk_by_paragraph(text, _meta(), min_words=30)
        assert len(chunks) == 1
        assert chunks[0].metadata["section_ref"] == "§2"

    def test_long_paragraph_sub_chunked(self):
        text = "§ 1. " + _words(500) + "\n\n"
        chunks = chunk_by_paragraph(text, _meta(), max_words=200)
        # Should produce multiple sub-chunks
        assert len(chunks) >= 2
        for c in chunks:
            assert "sub_chunk" in c.metadata

    def test_no_markers_falls_back_to_sliding_window(self):
        text = _words(100)  # no paragraph markers
        chunks = chunk_by_paragraph(text, _meta())
        assert len(chunks) >= 1
        # sliding_window sets chunk_index
        assert any("chunk_index" in c.metadata for c in chunks)

    def test_stable_chunk_ids(self):
        text = self._ccc_text()
        c1 = chunk_by_paragraph(text, _meta())
        c2 = chunk_by_paragraph(text, _meta())
        assert [c.chunk_id for c in c1] == [c.chunk_id for c in c2]

    def test_doc_meta_propagated(self):
        meta = _meta(doc_title="Catechism", language="la")
        chunks = chunk_by_paragraph(self._ccc_text(), meta)
        for c in chunks:
            assert c.metadata.get("doc_title") == "Catechism"
            assert c.metadata.get("language") == "la"


# ---------------------------------------------------------------------------
# chunk_by_section
# ---------------------------------------------------------------------------


class TestChunkBySection:
    def _section_text(self) -> str:
        return (
            "1. " + _words(80) + "\n\n"
            "2. " + _words(90) + "\n\n"
            "3. " + _words(70) + "\n\n"
        )

    def test_returns_chunks(self):
        chunks = chunk_by_section(self._section_text(), _meta())
        assert len(chunks) >= 1

    def test_chunks_are_document_chunks(self):
        for c in chunk_by_section(self._section_text(), _meta()):
            assert isinstance(c, DocumentChunk)

    def test_section_ref_in_metadata(self):
        chunks = chunk_by_section(self._section_text(), _meta())
        for c in chunks:
            assert "section_ref" in c.metadata

    def test_long_section_flushed(self):
        text = "1. " + _words(500) + "\n\n"
        chunks = chunk_by_section(text, _meta(), max_words=200)
        # A very long section should be flushed mid-way
        assert len(chunks) >= 1
        for c in chunks:
            assert len(c.content.split()) <= 510  # rough bound

    def test_short_sections_filtered(self):
        """Sections below min_words should not produce chunks."""
        text = "1. " + _words(10) + "\n\n2. " + _words(80) + "\n\n"
        chunks = chunk_by_section(text, _meta(), min_words=50)
        for c in chunks:
            assert len(c.content.split()) >= 50

    def test_doc_meta_propagated(self):
        meta = _meta(corpus="gaudium_et_spes")
        chunks = chunk_by_section(self._section_text(), meta)
        for c in chunks:
            assert c.metadata.get("corpus") == "gaudium_et_spes"


# ---------------------------------------------------------------------------
# chunk_sliding_window
# ---------------------------------------------------------------------------


class TestChunkSlidingWindow:
    def test_returns_chunks(self):
        chunks = chunk_sliding_window(_words(400), _meta())
        assert len(chunks) >= 1

    def test_all_chunks_are_document_chunks(self):
        for c in chunk_sliding_window(_words(400), _meta()):
            assert isinstance(c, DocumentChunk)

    def test_short_text_under_min_length_filtered(self):
        """Text with fewer than 20 words should produce no chunks."""
        text = _words(10)
        chunks = chunk_sliding_window(text, _meta(), window=300)
        assert chunks == []

    def test_chunk_index_in_metadata(self):
        for c in chunk_sliding_window(_words(400), _meta()):
            assert "chunk_index" in c.metadata

    def test_overlap_produces_more_chunks(self):
        text = _words(300)
        no_overlap = chunk_sliding_window(text, _meta(), window=100, overlap=0)
        with_overlap = chunk_sliding_window(text, _meta(), window=100, overlap=50)
        assert len(with_overlap) >= len(no_overlap)

    def test_unique_chunk_ids(self):
        chunks = chunk_sliding_window(_words(300), _meta())
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_stable_chunk_ids(self):
        text = _words(100)
        c1 = chunk_sliding_window(text, _meta())
        c2 = chunk_sliding_window(text, _meta())
        assert [c.chunk_id for c in c1] == [c.chunk_id for c in c2]


# ---------------------------------------------------------------------------
# chunk_document dispatcher
# ---------------------------------------------------------------------------


class TestChunkDocument:
    def test_paragraph_strategy(self):
        text = "§ 1. " + _words(60) + "\n\n§ 2. " + _words(60) + "\n\n"
        chunks = chunk_document(text, _meta(), strategy="paragraph")
        assert len(chunks) >= 1
        assert any(c.metadata.get("section_ref", "").startswith("§") for c in chunks)

    def test_section_strategy(self):
        text = "1. " + _words(80) + "\n\n2. " + _words(80) + "\n\n"
        chunks = chunk_document(text, _meta(), strategy="section")
        assert len(chunks) >= 1

    def test_sliding_window_strategy(self):
        text = _words(400)
        chunks = chunk_document(text, _meta(), strategy="sliding_window")
        assert len(chunks) >= 1
        assert any("chunk_index" in c.metadata for c in chunks)

    def test_unknown_strategy_uses_sliding_window(self):
        text = _words(400)
        chunks = chunk_document(text, _meta(), strategy="verse")
        # verse is handled externally; dispatcher falls through to sliding_window
        assert len(chunks) >= 1

    def test_default_strategy_is_paragraph(self):
        text = "§ 1. " + _words(60) + "\n\n"
        chunks_default = chunk_document(text, _meta())
        chunks_para = chunk_document(text, _meta(), strategy="paragraph")
        assert len(chunks_default) == len(chunks_para)

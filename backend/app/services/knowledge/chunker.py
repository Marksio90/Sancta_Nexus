"""Theological document chunker.

Splits Church documents into Qdrant-ready chunks while preserving:
  - Section references (paragraph numbers, verse citations)
  - Structural context (document title, part heading, chapter)
  - Theological metadata per chunk
  - Appropriate chunk size for dense theological embedding

Chunking strategies:
  verse           — Bible: one chunk per verse (or verse group)
  paragraph       — CCC / encyclicals: one chunk per numbered paragraph
  section         — Council documents: one chunk per numbered article/section
  sliding_window  — Patristic / liturgical: overlapping windows
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Output model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DocumentChunk:
    """A single unit ready for embedding + Qdrant upsert."""
    chunk_id: str                       # UUID stable across re-ingestions
    content: str                        # text to embed
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.content.split())


# ─────────────────────────────────────────────────────────────────────────────
# Bible chunker
# ─────────────────────────────────────────────────────────────────────────────

def chunk_bible_verses(
    book_abbr: str,
    book_name: str,
    chapter: int,
    verses: list[tuple[int, str]],  # [(verse_num, text), ...]
    translation: str,
    language: str,
    *,
    group_size: int = 3,             # group consecutive verses for context
) -> list[DocumentChunk]:
    """One chunk per verse, plus overlapping triplet-groups for context."""
    chunks: list[DocumentChunk] = []

    # Single verse chunks
    for verse_num, verse_text in verses:
        ref = f"{book_abbr} {chapter},{verse_num}"
        chunk_id = _stable_id(f"{translation}:{book_abbr}:{chapter}:{verse_num}")
        chunks.append(DocumentChunk(
            chunk_id=chunk_id,
            content=verse_text.strip(),
            metadata={
                "source_type": "bible",
                "translation": translation,
                "language": language,
                "book": book_abbr,
                "book_name": book_name,
                "chapter": chapter,
                "verse_start": verse_num,
                "verse_end": verse_num,
                "section_ref": ref,
                "display_ref": ref,
            },
        ))

    # Grouped verse windows for context-rich retrieval
    for i in range(len(verses) - group_size + 1):
        group = verses[i:i + group_size]
        v_start = group[0][0]
        v_end = group[-1][0]
        ref = f"{book_abbr} {chapter},{v_start}-{v_end}"
        combined = " ".join(v[1] for v in group).strip()
        chunk_id = _stable_id(f"{translation}:{book_abbr}:{chapter}:{v_start}-{v_end}")
        chunks.append(DocumentChunk(
            chunk_id=chunk_id,
            content=combined,
            metadata={
                "source_type": "bible",
                "translation": translation,
                "language": language,
                "book": book_abbr,
                "book_name": book_name,
                "chapter": chapter,
                "verse_start": v_start,
                "verse_end": v_end,
                "section_ref": ref,
                "display_ref": ref,
                "is_group": True,
            },
        ))

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# CCC / Encyclical paragraph chunker
# ─────────────────────────────────────────────────────────────────────────────

# Pattern: numbered paragraph — "§ 1234", "n. 14", "14.", "[14]"
_PARA_NUM_RE = re.compile(
    r"^(?:§\s*|n\.\s*|\[)(\d{1,4})[.\]]\s*",
    re.MULTILINE,
)

def chunk_by_paragraph(
    text: str,
    doc_meta: dict[str, Any],
    *,
    min_words: int = 30,
    max_words: int = 350,
) -> list[DocumentChunk]:
    """Split a document by numbered paragraphs.

    Falls back to sliding_window if no paragraph markers found.
    """
    # Try to split on explicit paragraph numbers
    segments = _PARA_NUM_RE.split(text)
    chunks: list[DocumentChunk] = []

    if len(segments) > 1:
        # segments: [preamble, para_num, para_text, para_num, para_text, ...]
        # preamble is index 0 (often empty)
        i = 1
        while i < len(segments) - 1:
            para_num = segments[i].strip()
            para_body = segments[i + 1].strip()
            i += 2

            if not para_body or len(para_body.split()) < min_words:
                continue

            # If paragraph is very long, sub-split it
            if len(para_body.split()) > max_words:
                sub_chunks = _sliding_window(para_body, window=max_words, overlap=50)
                for j, sub in enumerate(sub_chunks):
                    chunks.append(DocumentChunk(
                        chunk_id=_stable_id(f"{doc_meta['doc_id']}:{para_num}:{j}"),
                        content=sub,
                        metadata={**doc_meta, "section_ref": f"§{para_num}", "sub_chunk": j},
                    ))
            else:
                chunks.append(DocumentChunk(
                    chunk_id=_stable_id(f"{doc_meta['doc_id']}:{para_num}"),
                    content=para_body,
                    metadata={**doc_meta, "section_ref": f"§{para_num}"},
                ))
    else:
        # Fallback: sliding window
        chunks = chunk_sliding_window(text, doc_meta)

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Council document section chunker
# ─────────────────────────────────────────────────────────────────────────────

# Pattern: article numbers "1.", "14.", roman numerals "IV.", heading lines
_SECTION_BREAK_RE = re.compile(
    r"\n{2,}|\n(?=[A-Z\d]{1,4}[.)]\s)",
)

def chunk_by_section(
    text: str,
    doc_meta: dict[str, Any],
    *,
    min_words: int = 50,
    max_words: int = 400,
) -> list[DocumentChunk]:
    """Split council documents by sections/articles."""
    raw_sections = _SECTION_BREAK_RE.split(text)
    chunks: list[DocumentChunk] = []

    # Accumulate short sections together
    buffer = ""
    section_num = 0

    for raw in raw_sections:
        raw = raw.strip()
        if not raw:
            continue

        # Detect section header
        header_match = re.match(r"^(\d{1,3})\.\s", raw)
        if header_match:
            if buffer and len(buffer.split()) >= min_words:
                chunks.append(DocumentChunk(
                    chunk_id=_stable_id(f"{doc_meta['doc_id']}:s{section_num}"),
                    content=buffer.strip(),
                    metadata={**doc_meta, "section_ref": str(section_num) if section_num else "intro"},
                ))
            section_num = int(header_match.group(1))
            buffer = raw
        else:
            buffer = f"{buffer}\n{raw}".strip()

        # Flush if too long
        if len(buffer.split()) > max_words:
            chunks.append(DocumentChunk(
                chunk_id=_stable_id(f"{doc_meta['doc_id']}:s{section_num}x"),
                content=buffer.strip(),
                metadata={**doc_meta, "section_ref": str(section_num)},
            ))
            buffer = ""

    if buffer and len(buffer.split()) >= min_words:
        chunks.append(DocumentChunk(
            chunk_id=_stable_id(f"{doc_meta['doc_id']}:s{section_num}f"),
            content=buffer.strip(),
            metadata={**doc_meta, "section_ref": str(section_num)},
        ))

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Sliding window chunker (general purpose)
# ─────────────────────────────────────────────────────────────────────────────

def chunk_sliding_window(
    text: str,
    doc_meta: dict[str, Any],
    *,
    window: int = 300,
    overlap: int = 60,
) -> list[DocumentChunk]:
    """Fixed-size overlapping word windows for prose texts."""
    chunks: list[DocumentChunk] = []
    words = text.split()
    step = window - overlap
    total = len(words)

    for i, start in enumerate(range(0, total, step)):
        segment = " ".join(words[start:start + window])
        if len(segment.split()) < 20:
            continue
        chunks.append(DocumentChunk(
            chunk_id=_stable_id(f"{doc_meta['doc_id']}:w{i}"),
            content=segment,
            metadata={**doc_meta, "section_ref": f"w{i}", "chunk_index": i},
        ))

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────────────

def chunk_document(
    text: str,
    doc_meta: dict[str, Any],
    strategy: str = "paragraph",
) -> list[DocumentChunk]:
    """Route to the correct chunker based on strategy."""
    if strategy == "paragraph":
        return chunk_by_paragraph(text, doc_meta)
    elif strategy == "section":
        return chunk_by_section(text, doc_meta)
    elif strategy == "sliding_window":
        return chunk_sliding_window(text, doc_meta)
    else:
        # 'verse' strategy is handled by chunk_bible_verses directly
        return chunk_sliding_window(text, doc_meta)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _stable_id(seed: str) -> str:
    """Generate a deterministic UUID from a seed string."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def _sliding_window(text: str, window: int = 300, overlap: int = 50) -> list[str]:
    words = text.split()
    step = window - overlap
    return [
        " ".join(words[i:i + window])
        for i in range(0, len(words), step)
        if len(words[i:i + window]) >= 10
    ]

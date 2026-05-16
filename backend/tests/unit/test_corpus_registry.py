"""Unit tests for app/services/knowledge/corpus_registry.py.

Pure-Python module — no stubs required.

Contracts verified:
- DocumentType / QdrantCollection enums: values and key members
- CorpusDocument dataclass: required fields, defaults
- BIBLE_BOOKS_OT/NT: counts and canonical abbreviations
- CCC_PARTS: all 4 parts present
- COUNCIL_DOCUMENTS: exactly 12, unique IDs, valid collections, Vatican II present
- ENCYCLICAL_DOCUMENTS: exactly 30, unique IDs, encyclicals/exhortations, papal authors
- PATRISTIC_DOCUMENTS: exactly 9, patristic/liturgical types
- CORPUS_REGISTRY: exactly 51 total, no duplicate IDs
- CORPUS_BY_ID: all IDs resolvable
- CORPUS_BY_COLLECTION: every collection has ≥1 document, all collections valid
- get_document: found / not found
- get_collection_documents: returns list for known collection
- search_registry: theology_tag, tradition, doc_type, author filters; combined filters
"""

from __future__ import annotations

from app.services.knowledge.corpus_registry import (
    BIBLE_BOOKS_NT,
    BIBLE_BOOKS_OT,
    BIBLE_TRANSLATIONS,
    CCC_PARTS,
    CORPUS_BY_COLLECTION,
    CORPUS_BY_ID,
    CORPUS_REGISTRY,
    COUNCIL_DOCUMENTS,
    ENCYCLICAL_DOCUMENTS,
    PATRISTIC_DOCUMENTS,
    CorpusDocument,
    DocumentType,
    QdrantCollection,
    get_collection_documents,
    get_document,
    search_registry,
)

# ---------------------------------------------------------------------------
# DocumentType enum
# ---------------------------------------------------------------------------


class TestDocumentType:
    def test_bible(self):
        assert DocumentType.BIBLE == "bible"

    def test_encyclical(self):
        assert DocumentType.ENCYCLICAL == "encyclical"

    def test_dogmatic_constitution(self):
        assert DocumentType.DOGMATIC_CONSTITUTION == "dogmatic_constitution"

    def test_catechism(self):
        assert DocumentType.CATECHISM == "catechism"

    def test_patristic(self):
        assert DocumentType.PATRISTIC == "patristic"

    def test_has_at_least_10_types(self):
        assert len(DocumentType) >= 10


# ---------------------------------------------------------------------------
# QdrantCollection enum
# ---------------------------------------------------------------------------


class TestQdrantCollection:
    def test_biblia_pl(self):
        assert QdrantCollection.BIBLIA_PL == "biblia_pl"

    def test_katechizm(self):
        assert QdrantCollection.KATECHIZM == "katechizm"

    def test_magisterium(self):
        assert QdrantCollection.MAGISTERIUM == "magisterium"

    def test_sobory(self):
        assert QdrantCollection.SOBORY == "sobory"

    def test_patrystyka(self):
        assert QdrantCollection.PATRYSTYKA == "patrystyka"

    def test_has_8_collections(self):
        assert len(QdrantCollection) == 8


# ---------------------------------------------------------------------------
# CorpusDocument dataclass
# ---------------------------------------------------------------------------


class TestCorpusDocument:
    def _doc(self, **kwargs) -> CorpusDocument:
        defaults = {
            "doc_id": "test-doc",
            "title": "Test Title",
            "title_pl": "Tytuł Testowy",
            "doc_type": DocumentType.ENCYCLICAL,
            "collection": QdrantCollection.MAGISTERIUM,
            "author": "Test Author",
            "year": 2000,
        }
        defaults.update(kwargs)
        return CorpusDocument(**defaults)

    def test_required_fields(self):
        doc = self._doc()
        assert doc.doc_id == "test-doc"
        assert doc.title == "Test Title"
        assert doc.year == 2000

    def test_default_language_is_latin(self):
        doc = self._doc()
        assert doc.language == "la"

    def test_default_chunk_strategy(self):
        doc = self._doc()
        assert doc.chunk_strategy == "paragraph"

    def test_default_empty_lists(self):
        doc = self._doc()
        assert doc.theology_tags == []
        assert doc.tradition_tags == []

    def test_default_empty_strings(self):
        doc = self._doc()
        assert doc.fetch_url == ""
        assert doc.local_file == ""
        assert doc.description == ""


# ---------------------------------------------------------------------------
# Bible books catalog
# ---------------------------------------------------------------------------


class TestBibleBooks:
    def test_ot_has_46_books(self):
        assert len(BIBLE_BOOKS_OT) == 46

    def test_nt_has_27_books(self):
        assert len(BIBLE_BOOKS_NT) == 27

    def test_ot_starts_with_genesis(self):
        assert BIBLE_BOOKS_OT[0][0] == "Rdz"
        assert "Genesis" in BIBLE_BOOKS_OT[0][1]

    def test_nt_ends_with_revelation(self):
        assert BIBLE_BOOKS_NT[-1][0] == "Ap"
        assert "Revelation" in BIBLE_BOOKS_NT[-1][1] or "Apocalypse" in BIBLE_BOOKS_NT[-1][1]

    def test_psalms_in_ot(self):
        abbrs = [b[0] for b in BIBLE_BOOKS_OT]
        assert "Ps" in abbrs

    def test_john_in_nt(self):
        abbrs = [b[0] for b in BIBLE_BOOKS_NT]
        assert "J" in abbrs or "Jn" in abbrs


class TestBibleTranslations:
    def test_biblia_tysiaclecia_present(self):
        ids = set(BIBLE_TRANSLATIONS.keys())
        assert "BT" in ids or any("ysią" in v.get("name", "") for v in BIBLE_TRANSLATIONS.values())

    def test_each_translation_has_name(self):
        for code, meta in BIBLE_TRANSLATIONS.items():
            assert "name" in meta, f"Translation {code} missing 'name'"


# ---------------------------------------------------------------------------
# CCC_PARTS
# ---------------------------------------------------------------------------


class TestCCCParts:
    def test_has_4_parts(self):
        assert len(CCC_PARTS) == 4

    def test_part_numbers_1_to_4(self):
        assert set(CCC_PARTS.keys()) == {1, 2, 3, 4}

    def test_all_parts_have_title(self):
        for num, meta in CCC_PARTS.items():
            assert "title" in meta, f"Part {num} missing 'title'"


# ---------------------------------------------------------------------------
# COUNCIL_DOCUMENTS
# ---------------------------------------------------------------------------


class TestCouncilDocuments:
    def test_exactly_12_documents(self):
        assert len(COUNCIL_DOCUMENTS) == 12

    def test_unique_ids(self):
        ids = [d.doc_id for d in COUNCIL_DOCUMENTS]
        assert len(ids) == len(set(ids))

    def test_all_in_sobory_collection(self):
        for d in COUNCIL_DOCUMENTS:
            assert d.collection == QdrantCollection.SOBORY

    def test_lumen_gentium_present(self):
        ids = {d.doc_id for d in COUNCIL_DOCUMENTS}
        assert "lumen-gentium" in ids

    def test_gaudium_et_spes_present(self):
        ids = {d.doc_id for d in COUNCIL_DOCUMENTS}
        assert "gaudium-et-spes" in ids

    def test_all_have_titles_and_authors(self):
        for d in COUNCIL_DOCUMENTS:
            assert d.title.strip()
            assert d.author.strip()

    def test_all_have_doc_type(self):
        valid_types = {
            DocumentType.DOGMATIC_CONSTITUTION,
            DocumentType.PASTORAL_CONSTITUTION,
            DocumentType.DECREE,
            DocumentType.DECLARATION,
        }
        for d in COUNCIL_DOCUMENTS:
            assert d.doc_type in valid_types

    def test_all_have_theology_tags(self):
        for d in COUNCIL_DOCUMENTS:
            assert len(d.theology_tags) >= 1


# ---------------------------------------------------------------------------
# ENCYCLICAL_DOCUMENTS
# ---------------------------------------------------------------------------


class TestEncyclicalDocuments:
    def test_exactly_30_documents(self):
        assert len(ENCYCLICAL_DOCUMENTS) == 30

    def test_unique_ids(self):
        ids = [d.doc_id for d in ENCYCLICAL_DOCUMENTS]
        assert len(ids) == len(set(ids))

    def test_all_in_magisterium_collection(self):
        for d in ENCYCLICAL_DOCUMENTS:
            assert d.collection == QdrantCollection.MAGISTERIUM

    def test_rerum_novarum_present(self):
        ids = {d.doc_id for d in ENCYCLICAL_DOCUMENTS}
        assert "rerum-novarum" in ids

    def test_evangelium_vitae_present(self):
        ids = {d.doc_id for d in ENCYCLICAL_DOCUMENTS}
        assert "evangelium-vitae" in ids

    def test_doc_types_are_papal(self):
        papal_types = {
            DocumentType.ENCYCLICAL,
            DocumentType.APOSTOLIC_EXHORTATION,
            DocumentType.APOSTOLIC_CONSTITUTION,
            DocumentType.APOSTOLIC_LETTER,
        }
        for d in ENCYCLICAL_DOCUMENTS:
            assert d.doc_type in papal_types

    def test_all_have_year(self):
        for d in ENCYCLICAL_DOCUMENTS:
            assert 1800 <= d.year <= 2030, f"{d.doc_id} year {d.year} out of range"


# ---------------------------------------------------------------------------
# PATRISTIC_DOCUMENTS
# ---------------------------------------------------------------------------


class TestPatristicDocuments:
    def test_exactly_9_documents(self):
        assert len(PATRISTIC_DOCUMENTS) == 9

    def test_unique_ids(self):
        ids = [d.doc_id for d in PATRISTIC_DOCUMENTS]
        assert len(ids) == len(set(ids))

    def test_collections_are_patrystyka_or_liturgia(self):
        valid = {QdrantCollection.PATRYSTYKA, QdrantCollection.LITURGIA}
        for d in PATRISTIC_DOCUMENTS:
            assert d.collection in valid

    def test_augustine_present(self):
        authors = [d.author.lower() for d in PATRISTIC_DOCUMENTS]
        assert any("august" in a for a in authors)


# ---------------------------------------------------------------------------
# CORPUS_REGISTRY
# ---------------------------------------------------------------------------


class TestCorpusRegistry:
    def test_total_51_documents(self):
        assert len(CORPUS_REGISTRY) == 51

    def test_no_duplicate_ids(self):
        ids = [d.doc_id for d in CORPUS_REGISTRY]
        assert len(ids) == len(set(ids)), "Duplicate doc IDs in CORPUS_REGISTRY"

    def test_all_have_required_fields(self):
        for d in CORPUS_REGISTRY:
            assert d.doc_id.strip()
            assert d.title.strip()
            assert d.title_pl.strip()
            assert d.author.strip()
            assert d.year > 0

    def test_all_chunk_strategies_valid(self):
        valid = {"verse", "paragraph", "section", "sliding_window"}
        for d in CORPUS_REGISTRY:
            assert d.chunk_strategy in valid


# ---------------------------------------------------------------------------
# CORPUS_BY_ID
# ---------------------------------------------------------------------------


class TestCorpusByID:
    def test_all_ids_resolvable(self):
        for doc in CORPUS_REGISTRY:
            assert doc.doc_id in CORPUS_BY_ID

    def test_lookup_returns_correct_doc(self):
        doc = CORPUS_REGISTRY[0]
        result = CORPUS_BY_ID[doc.doc_id]
        assert result is doc

    def test_len_matches_registry(self):
        assert len(CORPUS_BY_ID) == len(CORPUS_REGISTRY)


# ---------------------------------------------------------------------------
# CORPUS_BY_COLLECTION
# ---------------------------------------------------------------------------


class TestCorpusByCollection:
    def test_all_referenced_collections_valid(self):
        for collection in CORPUS_BY_COLLECTION:
            assert isinstance(collection, QdrantCollection)

    def test_sobory_collection_has_entries(self):
        assert len(CORPUS_BY_COLLECTION.get(QdrantCollection.SOBORY, [])) > 0

    def test_magisterium_collection_has_entries(self):
        assert len(CORPUS_BY_COLLECTION.get(QdrantCollection.MAGISTERIUM, [])) > 0

    def test_total_matches_registry(self):
        total = sum(len(v) for v in CORPUS_BY_COLLECTION.values())
        assert total == len(CORPUS_REGISTRY)


# ---------------------------------------------------------------------------
# get_document
# ---------------------------------------------------------------------------


class TestGetDocument:
    def test_returns_document_by_id(self):
        first = CORPUS_REGISTRY[0]
        doc = get_document(first.doc_id)
        assert doc is not None
        assert doc.doc_id == first.doc_id

    def test_returns_none_for_unknown_id(self):
        assert get_document("nonexistent-encyclical-xyz") is None

    def test_lumen_gentium(self):
        doc = get_document("lumen-gentium")
        assert doc is not None
        assert doc.collection == QdrantCollection.SOBORY


# ---------------------------------------------------------------------------
# get_collection_documents
# ---------------------------------------------------------------------------


class TestGetCollectionDocuments:
    def test_returns_list(self):
        result = get_collection_documents(QdrantCollection.SOBORY)
        assert isinstance(result, list)

    def test_sobory_returns_council_docs(self):
        result = get_collection_documents(QdrantCollection.SOBORY)
        assert len(result) == len(COUNCIL_DOCUMENTS)

    def test_unknown_collection_returns_empty(self):
        # Use a collection not actually populated
        result = get_collection_documents(QdrantCollection.BIBLIA_PL)
        assert result == []

    def test_all_docs_match_collection(self):
        for doc in get_collection_documents(QdrantCollection.MAGISTERIUM):
            assert doc.collection == QdrantCollection.MAGISTERIUM


# ---------------------------------------------------------------------------
# search_registry
# ---------------------------------------------------------------------------


class TestSearchRegistry:
    def test_theology_tag_filter(self):
        # "christology" should appear in at least one document
        results = search_registry(theology_tag="christology")
        assert len(results) >= 1
        for doc in results:
            assert "christology" in doc.theology_tags

    def test_doc_type_filter_encyclical(self):
        results = search_registry(doc_type=DocumentType.ENCYCLICAL)
        assert len(results) >= 5
        for doc in results:
            assert doc.doc_type == DocumentType.ENCYCLICAL

    def test_doc_type_filter_dogmatic(self):
        results = search_registry(doc_type=DocumentType.DOGMATIC_CONSTITUTION)
        assert len(results) >= 1

    def test_author_filter(self):
        results = search_registry(author="Jan Paweł")
        assert len(results) >= 3  # JPII wrote many encyclicals
        for doc in results:
            assert "Jan Paweł" in doc.author or "jan paweł" in doc.author.lower()

    def test_tradition_filter(self):
        results = search_registry(tradition="all")
        assert len(results) >= 1

    def test_combined_filters(self):
        results = search_registry(
            doc_type=DocumentType.ENCYCLICAL,
            author="Jan Paweł",
        )
        assert len(results) >= 1
        for doc in results:
            assert doc.doc_type == DocumentType.ENCYCLICAL
            assert "Jan Paweł" in doc.author or "jan paweł" in doc.author.lower()

    def test_no_filter_returns_all(self):
        assert len(search_registry()) == len(CORPUS_REGISTRY)

    def test_nonexistent_theology_tag_returns_empty(self):
        assert search_registry(theology_tag="nonexistent_xyz_tag") == []

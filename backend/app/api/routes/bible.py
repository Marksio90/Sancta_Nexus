"""Bible API routes.

Provides endpoints for querying scripture with 4-dimensional responses
(literal, allegorical, moral, anagogical), passage retrieval and
full-text search.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AskRequest(BaseModel):
    """Request body for asking a question about scripture."""

    question: str
    translation: str = "BT"
    include_magisterium: bool = True
    include_patristic: bool = True
    max_passages: int = Field(default=5, ge=1, le=20)


class FourDimensionalResponse(BaseModel):
    """A 4-dimensional scripture response following patristic exegesis.

    The four senses of scripture:
    - Literal (historical): what the text says
    - Allegorical (typological): what the text means for faith
    - Moral (tropological): what the text means for behaviour
    - Anagogical (eschatological): what the text means for ultimate destiny
    """

    question: str
    passages: list[dict[str, Any]] = Field(default_factory=list)
    literal_sense: str = ""
    allegorical_sense: str = ""
    moral_sense: str = ""
    anagogical_sense: str = ""
    magisterium_references: list[dict[str, Any]] = Field(default_factory=list)
    patristic_references: list[dict[str, Any]] = Field(default_factory=list)


class PassageResponse(BaseModel):
    """Response containing a specific scripture passage."""

    book: str
    chapter: int
    verses: list[dict[str, Any]] = Field(default_factory=list)
    translation: str = "BT"
    context: dict[str, Any] = Field(default_factory=dict)


class SearchResultItem(BaseModel):
    """A single scripture search result."""

    reference: str
    content: str
    score: float
    book: str = ""
    chapter: int = 0
    verse: int = 0


class SearchResponse(BaseModel):
    """Response for scripture search queries."""

    query: str
    total_results: int
    results: list[SearchResultItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/ask", response_model=FourDimensionalResponse)
async def ask_scripture(request: AskRequest) -> FourDimensionalResponse:
    """Ask a question about scripture and receive a 4-dimensional response.

    Uses ExegesisAgent (A-018) for genuine multi-dimensional biblical analysis
    and DoctrineGuardAgent (A-021) for doctrinal safety validation.
    The response follows the traditional Catholic four senses of
    scripture (literal, allegorical, moral, anagogical).
    """
    from app.services.rag.rag_service import RAGService
    from app.agents.theology.exegesis_agent import ExegesisAgent
    from app.agents.theology.doctrine_guard import DoctrineGuardAgent
    from app.agents.theology.theology_pipeline import TheologicalValidationPipeline

    rag = RAGService()

    # Search biblical collection
    scripture_results = rag.search("biblia_pl", request.question, limit=request.max_passages)

    passages = [
        {
            "content": r.content,
            "score": r.score,
            "metadata": r.metadata,
        }
        for r in scripture_results
    ]

    # Search Magisterium if requested
    magisterium_refs: list[dict[str, Any]] = []
    if request.include_magisterium:
        mag_results = rag.search_magisterium(request.question, limit=3)
        magisterium_refs = [
            {
                "content": r.content,
                "document_title": r.document_title,
                "paragraph": r.paragraph,
                "pope_or_council": r.pope_or_council,
                "score": r.score,
            }
            for r in mag_results
        ]

    # Search patristic if requested
    patristic_refs: list[dict[str, Any]] = []
    if request.include_patristic:
        pat_results = rag.search("patrystyka", request.question, limit=3)
        patristic_refs = [
            {
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in pat_results
        ]

    # ── Run ExegesisAgent (A-018) on the top matching passage ─────────────
    top_passage = scripture_results[0] if scripture_results else None
    exegesis_dims: dict[str, str] = {}

    if top_passage:
        try:
            exegesis_agent = ExegesisAgent()
            exegesis_dims = await exegesis_agent.analyze(
                book=top_passage.book or "Unknown",
                chapter=top_passage.chapter or 1,
                verse_start=top_passage.verse or 1,
                verse_end=top_passage.verse or 1,
                text=top_passage.content,
            )
        except Exception:
            logger.exception("ExegesisAgent failed; falling back to stub responses.")

    # Map exegesis dimensions → 4 traditional senses of scripture
    combined_text = " ".join(r.content for r in scripture_results[:3])
    literal_sense = exegesis_dims.get(
        "historical_critical"
    ) or _generate_literal_sense(request.question, combined_text)
    allegorical_sense = exegesis_dims.get(
        "canonical"
    ) or _generate_allegorical_sense(request.question, combined_text)
    moral_sense = exegesis_dims.get(
        "theological"
    ) or _generate_moral_sense(request.question, combined_text)
    anagogical_sense = exegesis_dims.get(
        "literary"
    ) or _generate_anagogical_sense(request.question, combined_text)

    # ── DoctrineGuardAgent (A-021) via TheologicalValidationPipeline ──────
    # Validate the generated response for doctrinal fidelity before returning.
    full_response_text = " ".join([literal_sense, allegorical_sense, moral_sense, anagogical_sense])
    scripture_ref = (
        f"{top_passage.book} {top_passage.chapter},{top_passage.verse}"
        if top_passage and top_passage.book
        else request.question[:80]
    )

    try:
        pipeline = TheologicalValidationPipeline(
            exegesis_agent=ExegesisAgent(),
            doctrine_guard=DoctrineGuardAgent(),
        )
        validation = await pipeline.validate(full_response_text, scripture_ref)
        if not validation.passed and validation.fallback_content:
            logger.warning(
                "Theological validation failed (score=%.2f); using fallback content.",
                validation.aggregate_score,
            )
            fallback = validation.fallback_content
            # Replace each sense with the fallback notice
            literal_sense = fallback
            allegorical_sense = fallback
            moral_sense = fallback
            anagogical_sense = fallback
    except Exception:
        logger.exception("TheologicalValidationPipeline failed; serving unvalidated content.")

    return FourDimensionalResponse(
        question=request.question,
        passages=passages,
        literal_sense=literal_sense,
        allegorical_sense=allegorical_sense,
        moral_sense=moral_sense,
        anagogical_sense=anagogical_sense,
        magisterium_references=magisterium_refs,
        patristic_references=patristic_refs,
    )


@router.get("/passage/{book}/{chapter}", response_model=PassageResponse)
async def get_passage(
    book: str,
    chapter: int,
    verse_start: int | None = Query(default=None, description="Starting verse"),
    verse_end: int | None = Query(default=None, description="Ending verse"),
    translation: str = Query(default="BT", description="Bible translation code"),
) -> PassageResponse:
    """Retrieve a specific scripture passage by book and chapter.

    Optionally filter by verse range.
    """
    from app.services.rag.rag_service import RAGService

    rag = RAGService()

    query = f"{book} {chapter}"
    if verse_start:
        query += f",{verse_start}"
        if verse_end:
            query += f"-{verse_end}"

    results = rag.search_scripture(query, limit=20)

    verses = []
    for r in results:
        if r.book.lower() == book.lower() and r.chapter == chapter:
            if verse_start and r.verse < verse_start:
                continue
            if verse_end and r.verse > verse_end:
                continue
            verses.append({
                "verse": r.verse,
                "content": r.content,
                "translation": r.translation,
            })

    verses.sort(key=lambda v: v["verse"])

    return PassageResponse(
        book=book,
        chapter=chapter,
        verses=verses,
        translation=translation,
        context={
            "total_verses_found": len(verses),
            "verse_range": f"{verse_start or 1}-{verse_end or 'end'}",
        },
    )


@router.get("/search", response_model=SearchResponse)
async def search_scripture(
    q: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
    book: str | None = Query(default=None, description="Filter by book"),
) -> SearchResponse:
    """Full-text semantic search across scripture."""
    from app.services.rag.rag_service import RAGService

    rag = RAGService()

    emotion_filter: dict[str, Any] | None = None
    if book:
        emotion_filter = {"book": book}

    results = rag.search_scripture(q, emotion_filter=emotion_filter, limit=limit)

    items = [
        SearchResultItem(
            reference=f"{r.book} {r.chapter},{r.verse}",
            content=r.content,
            score=r.score,
            book=r.book,
            chapter=r.chapter,
            verse=r.verse,
        )
        for r in results
    ]

    return SearchResponse(
        query=q,
        total_results=len(items),
        results=items,
    )


@router.get("/random-verse")
async def get_random_verse() -> dict:
    """Return a random verse from the full 31 102-verse Polish Bible corpus.

    Picks a random spiritual theme, runs a semantic vector search, then
    returns one randomly-selected verse from the top results.  Falls back to
    a curated list when Qdrant is unavailable.
    """
    import random

    SPIRITUAL_QUERIES = [
        "miłość Boga do człowieka", "zbawienie i odkupienie", "nadzieja wieczna",
        "modlitwa i adoracja", "łaska Boża", "nawrócenie serca",
        "wiara i zaufanie", "pokój serca Boży", "przebaczenie win",
        "radość w Panu", "miłosierdzie Boże", "stworzenie świata",
        "zmartwychwstanie i życie", "Duch Święty", "prawda i mądrość",
        "sprawiedliwość Boża", "pokuta i pojednanie", "chwała Pańska",
        "przymierze z Bogiem", "misja i ewangelizacja",
        "cierpienie i krzyż", "uzdrowienie i zbawienie", "wierność Boga",
        "błogosławieństwo", "królestwo Boże", "Mesjasz i wybawiciel",
        "Słowo Boże jako pokarm", "światłość i ciemność", "droga oczyszczenia",
        "opatrzność Boża", "proroctwo i nadzieja", "ofiarowanie się Bogu",
        "miłość bliźniego", "pokora i służba", "wytrwałość w wierze",
        "modlitwa wstawiennicza", "chwała Trójcy Świętej", "łamanie chleba",
        "powołanie i wybranie", "świętość i uświęcenie", "zaufanie w próbie",
        "bojaźń Boża i mądrość", "szukanie Boga", "obecność Boga",
        "pielgrzymka duszy", "nowe stworzenie", "zmartwychwstanie ciała",
        "miłość jako fundament", "modlitwa psalmów", "Słowo stało się ciałem",
        "naśladowanie Chrystusa", "misericordia Dei", "ogień Ducha",
        "pokój który świat dać nie może", "tajemnica Kościoła", "Eucharystia",
        "woda żywa", "chleb życia", "dobry pasterz", "droga do ojca",
        "syn marnotrawny", "kobieta z krwotokiem", "uzdrowienie niewidomego",
        "kazanie na górze", "błogosławieństwa ewangeliczne", "modlitwa Ojcze Nasz",
        "Magnificat Maryi", "zwiastowanie", "narodzenie Pańskie", "Getsemani",
        "droga krzyżowa", "zesłanie Ducha", "Apokalipsa nadzieja",
        "trwałość miłości Bożej", "wierność przymierza", "serce contrite",
    ]

    FALLBACK_VERSES = [
        {"text": "Bóg jest miłością", "ref": "1 J 4,8"},
        {"text": "Nie lękaj się, bo Ja jestem z tobą", "ref": "Iz 41,10"},
        {"text": "Pokój zostawiam wam, pokój mój daję wam", "ref": "J 14,27"},
        {"text": "Pan jest moim pasterzem, nie brak mi niczego", "ref": "Ps 23,1"},
        {"text": "Wszystko mogę w Tym, który mnie umacnia", "ref": "Flp 4,13"},
        {"text": "Miłujcie się wzajemnie, tak jak Ja was umiłowałem", "ref": "J 15,12"},
        {"text": "Kto we Mnie wierzy, ma życie wieczne", "ref": "J 6,47"},
        {"text": "W miłości nie ma lęku", "ref": "1 J 4,18"},
        {"text": "Słowo Twoje jest lampą dla moich kroków", "ref": "Ps 119,105"},
        {"text": "Jam jest zmartwychwstanie i życie", "ref": "J 11,25"},
        {"text": "Miłość nigdy nie ustaje", "ref": "1 Kor 13,8"},
        {"text": "Trwajcie w miłości mojej", "ref": "J 15,9"},
    ]

    from app.services.rag.rag_service import RAGService

    query = random.choice(SPIRITUAL_QUERIES)
    rag = RAGService()
    results = rag.search_scripture(query, limit=10)

    if results:
        pick = random.choice(results[:5])
        ref = pick.book
        if pick.chapter:
            ref += f" {pick.chapter}"
            if pick.verse:
                ref += f",{pick.verse}"
        return {"text": pick.content, "ref": ref, "source": "qdrant"}

    fallback = random.choice(FALLBACK_VERSES)
    return {**fallback, "source": "fallback"}


# ---------------------------------------------------------------------------
# Helpers for 4-dimensional response generation
# ---------------------------------------------------------------------------


def _generate_literal_sense(question: str, context: str) -> str:
    """Generate the literal/historical sense.

    In production, this would call an LLM with the retrieved context.
    """
    if not context:
        return "Brak wystarczajacego kontekstu dla interpretacji literalnej."
    return (
        f"Sens literalny: Na podstawie znalezionych fragmentow, "
        f"tekst odnosi sie bezposrednio do pytania: '{question}'. "
        f"Historyczny kontekst wymaga dalszej analizy."
    )


def _generate_allegorical_sense(question: str, context: str) -> str:
    """Generate the allegorical/typological sense."""
    if not context:
        return "Brak wystarczajacego kontekstu dla interpretacji alegorycznej."
    return (
        f"Sens alegoryczny: Fragment ten moze byc odczytany jako typ "
        f"lub figura wskazujaca na Chrystusa i Kosciol."
    )


def _generate_moral_sense(question: str, context: str) -> str:
    """Generate the moral/tropological sense."""
    if not context:
        return "Brak wystarczajacego kontekstu dla interpretacji moralnej."
    return (
        f"Sens moralny: Tekst wzywa do konkretnej odpowiedzi zyciowej, "
        f"do nawrocenia i przemiany serca."
    )


def _generate_anagogical_sense(question: str, context: str) -> str:
    """Generate the anagogical/eschatological sense."""
    if not context:
        return "Brak wystarczajacego kontekstu dla interpretacji anagogicznej."
    return (
        f"Sens anagogiczny: Fragment wskazuje na rzeczywistosc eschatologiczna, "
        f"na pelnie zbawienia i zycie wieczne."
    )

"""Knowledge Base API routes for Sancta Nexus.

Exposes the Church knowledge base (Bible, CCC, Vatican councils,
papal encyclicals, patristic texts) via a unified RAG search interface.

Endpoints
---------
POST /search              — Multi-collection semantic search
GET  /collections         — List Qdrant collections with stats
GET  /document/{doc_id}   — List all indexed chunks for a document
GET  /stats               — Overall knowledge base statistics
POST /cross-reference     — Find cross-references for a passage
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


class SearchRequest(BaseModel):
    """Request body for semantic knowledge search."""

    query: str = Field(..., min_length=3, max_length=1000, description="Search query in any language")
    collections: list[str] | None = Field(
        default=None,
        description=(
            "Limit search to specific collections. "
            "Valid: biblia_pl, biblia_la, biblia_en, katechizm, sobory, "
            "magisterium, patrystyka, liturgia. "
            "Omit or pass null for auto-routing."
        ),
    )
    limit: int = Field(default=5, ge=1, le=20, description="Max results per collection")
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Payload filters, e.g. {\"language\": \"pl\", \"theology_tags\": [\"prayer\"]}",
    )
    tradition: str | None = Field(
        default=None,
        description="Filter by spiritual tradition: benedictine, carmelite, jesuit, dominican, etc.",
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score (0-1)",
    )


class KnowledgeResult(BaseModel):
    """A single knowledge base search result."""

    id: str
    content: str
    score: float
    collection: str
    doc_id: str = ""
    doc_type: str = ""
    source_type: str = ""
    section_ref: str = ""
    document_title: str = ""
    author: str = ""
    year: int | None = None
    language: str = ""
    theology_tags: list[str] = []
    tradition_tags: list[str] = []
    citation: str = ""
    extra: dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Response for knowledge base search."""

    query: str
    total_results: int
    results: list[KnowledgeResult]
    collections_searched: list[str]
    routed_automatically: bool


class CrossReferenceRequest(BaseModel):
    """Request body for cross-reference lookup."""

    reference: str = Field(
        ...,
        description="Scripture or document reference, e.g. 'J 3,16' or 'KKK §1822'",
    )
    content: str | None = Field(
        default=None,
        description="Optional passage text for semantic cross-referencing",
    )
    include_collections: list[str] | None = Field(
        default=None,
        description="Collections to cross-reference against. Defaults to all.",
    )


# ---------------------------------------------------------------------------
# Helper: lazy RAG singleton
# ---------------------------------------------------------------------------


def _get_rag():
    """Lazily import and return the ChurchRAG singleton."""
    try:
        from app.services.knowledge.church_rag import get_church_rag
        return get_church_rag()
    except Exception as exc:
        logger.error("Failed to load ChurchRAG: %s", exc)
        return None


def _format_result(r) -> KnowledgeResult:
    """Convert a KnowledgeResult dataclass to a Pydantic model."""
    payload = r.payload if hasattr(r, "payload") else {}
    extra = {}

    # Bible-specific fields
    for key in ("book", "book_full", "chapter", "verse", "verse_end", "translation"):
        if key in payload:
            extra[key] = payload[key]

    # Catechism / council / encyclical specific
    for key in ("paragraph_ref", "part", "article", "paragraph", "document_title_pl"):
        if key in payload:
            extra[key] = payload[key]

    return KnowledgeResult(
        id=str(r.id) if hasattr(r, "id") else "",
        content=r.content,
        score=round(r.score, 4),
        collection=r.collection if hasattr(r, "collection") else payload.get("collection", ""),
        doc_id=r.doc_id if hasattr(r, "doc_id") else payload.get("doc_id", ""),
        doc_type=r.doc_type if hasattr(r, "doc_type") else payload.get("doc_type", ""),
        source_type=r.source_type if hasattr(r, "source_type") else payload.get("source_type", ""),
        section_ref=r.section_ref if hasattr(r, "section_ref") else payload.get("section_ref", ""),
        document_title=r.document_title if hasattr(r, "document_title") else payload.get("document_title", ""),
        author=r.author if hasattr(r, "author") else payload.get("author", ""),
        year=r.year if hasattr(r, "year") else payload.get("year"),
        language=r.language if hasattr(r, "language") else payload.get("language", ""),
        theology_tags=r.theology_tags if hasattr(r, "theology_tags") else payload.get("theology_tags", []),
        tradition_tags=r.tradition_tags if hasattr(r, "tradition_tags") else payload.get("tradition_tags", []),
        citation=r.citation if hasattr(r, "citation") else "",
        extra=extra,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(req: SearchRequest) -> SearchResponse:
    """Semantic search across the Church knowledge base.

    Automatically routes queries to the most relevant collections
    (Bible, Catechism, Councils, Encyclicals, Patristics) using
    keyword-based routing + authority re-ranking.
    """
    rag = _get_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base service is unavailable (Qdrant not connected).",
        )

    try:
        filters = req.filters or {}
        if req.tradition:
            filters["tradition"] = req.tradition

        results = await rag.search(
            query=req.query,
            collections=req.collections,
            limit=req.limit,
            filters=filters if filters else None,
        )

        if req.min_score > 0:
            results = [r for r in results if r.score >= req.min_score]

        routed = req.collections is None
        collections_searched = list({r.collection for r in results}) if results else []

        return SearchResponse(
            query=req.query,
            total_results=len(results),
            results=[_format_result(r) for r in results],
            collections_searched=collections_searched,
            routed_automatically=routed,
        )

    except Exception as exc:
        logger.error("Knowledge search error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        )


@router.get("/collections")
async def list_collections() -> dict[str, Any]:
    """List all Qdrant collections with document counts and metadata."""
    rag = _get_rag()
    if rag is None:
        return {
            "collections": [],
            "error": "Knowledge base unavailable (Qdrant not connected)",
        }

    try:
        stats = await rag.manager.collection_stats()
        return {
            "collections": [
                {
                    "name": name,
                    "vectors_count": info.get("vectors_count", 0),
                    "status": info.get("status", "unknown"),
                }
                for name, info in stats.items()
            ],
            "total_collections": len(stats),
        }
    except Exception as exc:
        logger.error("Collections list error: %s", exc)
        return {"collections": [], "error": str(exc)}


@router.get("/collections/{collection_name}")
async def get_collection(collection_name: str) -> dict[str, Any]:
    """Get stats for a specific Qdrant collection."""
    rag = _get_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base unavailable.",
        )

    valid_collections = [
        "biblia_pl", "biblia_la", "biblia_en",
        "katechizm", "sobory", "magisterium",
        "patrystyka", "liturgia",
    ]
    if collection_name not in valid_collections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown collection '{collection_name}'. Valid: {', '.join(valid_collections)}",
        )

    try:
        stats = await rag.manager.collection_stats()
        info = stats.get(collection_name)
        if info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found in Qdrant.",
            )
        return {"name": collection_name, **info}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/document/{doc_id}")
async def get_document_chunks(
    doc_id: str,
    collection: str | None = Query(default=None, description="Collection to search in"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """Retrieve all indexed chunks for a given document ID.

    Example doc_ids: ccc, biblia_bg, vulgata, lg, dv, gs,
    rerum_novarum, laudato_si, augustine_confessions
    """
    rag = _get_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base unavailable.",
        )

    try:
        results = await rag.search_by_document(
            doc_id=doc_id,
            collection=collection,
            limit=limit,
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No chunks found for document '{doc_id}'.",
            )

        return {
            "doc_id": doc_id,
            "total_chunks": len(results),
            "chunks": [_format_result(r) for r in results],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Document retrieval error for %s: %s", doc_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/stats")
async def knowledge_stats() -> dict[str, Any]:
    """Overall knowledge base statistics — total chunks per collection and corpus coverage."""
    rag = _get_rag()
    if rag is None:
        return {
            "status": "unavailable",
            "message": "Qdrant not connected. Run: python -m scripts.ingest_corpus --seed-only",
            "collections": {},
        }

    try:
        col_stats = await rag.manager.collection_stats()
        total_chunks = sum(
            v.get("vectors_count", 0) for v in col_stats.values()
        )

        return {
            "status": "available",
            "total_chunks": total_chunks,
            "collections": {
                name: {
                    "chunks": info.get("vectors_count", 0),
                    "status": info.get("status", "unknown"),
                }
                for name, info in col_stats.items()
            },
            "corpus_coverage": {
                "bible": ["BG (Biblia Gdańska)", "VUL (Vulgata)", "DRB (Douay-Rheims)"],
                "catechism": ["KKK — Katechizm Kościoła Katolickiego (1992)"],
                "councils": [
                    "Sobór Watykański I (Dei Filius, Pastor Aeternus)",
                    "Sobór Watykański II (LG, DV, SC, GS, UR, PO, AA, AG, NA, DH)",
                ],
                "encyclicals": [
                    "Leon XIII → Franciszek (~30 dokumentów)",
                    "Rerum Novarum, Fides et Ratio, Veritatis Splendor, Laudato Si', ...",
                ],
                "patristics": [
                    "Augustyn, Tomasz z Akwinu, Teresa z Ávila, Jan od Krzyża",
                    "Ignacy Loyola, Benedykt z Nursji, Guigo II",
                ],
            },
        }

    except Exception as exc:
        logger.error("Knowledge stats error: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
            "collections": {},
        }


@router.post("/cross-reference")
async def cross_reference(req: CrossReferenceRequest) -> dict[str, Any]:
    """Find cross-references for a scripture passage or church document citation.

    Given a reference like 'J 3,16' or 'KKK §1822', finds related passages
    in the Catechism, councils, encyclicals, and patristic texts.
    """
    rag = _get_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base unavailable.",
        )

    try:
        results = await rag.cross_reference(
            reference=req.reference,
            text=req.content,
            target_collections=req.include_collections,
        )

        return {
            "reference": req.reference,
            "cross_references": [_format_result(r) for r in results],
            "total": len(results),
        }

    except Exception as exc:
        logger.error("Cross-reference error for %s: %s", req.reference, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/scripture")
async def search_scripture(
    q: str = Query(..., min_length=3, description="Scripture search query"),
    translation: str = Query(default="pl", description="Language: pl, la, en"),
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, Any]:
    """Convenience endpoint: search Bible verses only."""
    rag = _get_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base unavailable.",
        )

    collection_map = {"pl": "biblia_pl", "la": "biblia_la", "en": "biblia_en"}
    collection = collection_map.get(translation, "biblia_pl")

    try:
        results = await rag.search_scripture(query=q, limit=limit)
        return {
            "query": q,
            "translation": translation,
            "results": [_format_result(r) for r in results],
            "total": len(results),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/catechism")
async def search_catechism(
    q: str = Query(..., min_length=3, description="Catechism search query"),
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, Any]:
    """Convenience endpoint: search the Catechism of the Catholic Church only."""
    rag = _get_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base unavailable.",
        )

    try:
        results = await rag.search_catechism(query=q, limit=limit)
        return {
            "query": q,
            "results": [_format_result(r) for r in results],
            "total": len(results),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/magisterium")
async def search_magisterium(
    q: str = Query(..., min_length=3, description="Magisterium search query"),
    limit: int = Query(default=5, ge=1, le=20),
    include_councils: bool = Query(default=True, description="Include council documents"),
) -> dict[str, Any]:
    """Convenience endpoint: search Church Magisterium (encyclicals + councils)."""
    rag = _get_rag()
    if rag is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base unavailable.",
        )

    try:
        collections = ["magisterium"]
        if include_councils:
            collections.append("sobory")

        results = await rag.search(
            query=q,
            collections=collections,
            limit=limit,
        )
        return {
            "query": q,
            "collections_searched": collections,
            "results": [_format_result(r) for r in results],
            "total": len(results),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

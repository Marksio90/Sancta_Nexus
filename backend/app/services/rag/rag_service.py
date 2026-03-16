"""RAG Service for Sancta Nexus - manages 8 Qdrant vector collections."""
import logging
from dataclasses import dataclass, field
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

COLLECTIONS = [
    "biblia_pl", "katechizm", "patrystyka", "magisterium",
    "liturgia", "duchowosc", "komentarze", "psychologia_duch",
]


@dataclass
class SearchResult:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


@dataclass
class ScriptureResult:
    """Search result with scripture-specific fields."""
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    book: str = ""
    chapter: int = 0
    verse: int = 0
    translation: str = "BT"
    document_title: str = ""
    paragraph: str = ""
    pope_or_council: str = ""


class RAGService:
    def __init__(self, host: str = "localhost", port: int = 6333, api_key: str | None = None):
        try:
            self.client = QdrantClient(host=host, port=port, api_key=api_key)
        except Exception:
            logger.warning("Could not connect to Qdrant at %s:%s - using offline mode", host, port)
            self.client = None
        self._embedding_service = None

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            from app.services.rag.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def search(self, collection: str, query: str, limit: int = 5, filters: dict[str, Any] | None = None) -> list[SearchResult]:
        if self.client is None:
            return []
        try:
            query_vector = self.embedding_service.embed_text(query)
            qdrant_filter = None
            if filters:
                conditions = [FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filters.items()]
                qdrant_filter = Filter(must=conditions)
            results = self.client.search(
                collection_name=collection, query_vector=query_vector,
                limit=limit, query_filter=qdrant_filter,
            )
            return [
                SearchResult(
                    content=r.payload.get("content", ""),
                    metadata=r.payload,
                    score=r.score,
                )
                for r in results
            ]
        except Exception as e:
            logger.error("RAG search error in %s: %s", collection, e)
            return []

    def search_scripture(self, query: str, emotion_filter: dict[str, Any] | None = None, limit: int = 5) -> list[ScriptureResult]:
        results = self.search("biblia_pl", query, limit=limit, filters=emotion_filter)
        return [
            ScriptureResult(
                content=r.content,
                score=r.score,
                metadata=r.metadata,
                book=r.metadata.get("book", ""),
                chapter=r.metadata.get("chapter", 0),
                verse=r.metadata.get("verse", 0),
                translation=r.metadata.get("translation", "BT"),
            )
            for r in results
        ]

    def search_magisterium(self, query: str, limit: int = 5) -> list[ScriptureResult]:
        results = self.search("magisterium", query, limit=limit)
        return [
            ScriptureResult(
                content=r.content,
                score=r.score,
                metadata=r.metadata,
                document_title=r.metadata.get("document_title", ""),
                paragraph=r.metadata.get("paragraph", ""),
                pope_or_council=r.metadata.get("pope_or_council", ""),
            )
            for r in results
        ]

    def search_patristic(self, query: str, limit: int = 5) -> list[SearchResult]:
        return self.search("patrystyka", query, limit=limit)

    def index_document(self, collection: str, doc_id: str, content: str, metadata: dict[str, Any]) -> bool:
        if self.client is None:
            return False
        try:
            vector = self.embedding_service.embed_text(content)
            self.client.upsert(collection_name=collection, points=[{
                "id": doc_id, "vector": vector,
                "payload": {"content": content, **metadata},
            }])
            return True
        except Exception as e:
            logger.error("Indexing error: %s", e)
            return False

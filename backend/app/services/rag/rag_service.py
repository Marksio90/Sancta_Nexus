"""RAG Service for Sancta Nexus - manages 8 Qdrant vector collections."""
import logging
from dataclasses import dataclass, field
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
    metadata: dict
    score: float

class RAGService:
    def __init__(self, host: str = "localhost", port: int = 6333, api_key: str | None = None):
        self.client = QdrantClient(host=host, port=port, api_key=api_key)
        self._embedding_service = None

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            from app.services.rag.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    async def search(self, collection: str, query: str, limit: int = 5, filters: dict | None = None) -> list[SearchResult]:
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
            return [SearchResult(content=r.payload.get("content", ""), metadata=r.payload, score=r.score) for r in results]
        except Exception as e:
            logger.error(f"RAG search error in {collection}: {e}")
            return []

    async def search_scripture(self, query: str, emotion_filter: dict | None = None, limit: int = 5) -> list[SearchResult]:
        return await self.search("biblia_pl", query, limit=limit)

    async def search_magisterium(self, query: str, limit: int = 5) -> list[SearchResult]:
        return await self.search("magisterium", query, limit=limit)

    async def search_patristic(self, query: str, limit: int = 5) -> list[SearchResult]:
        return await self.search("patrystyka", query, limit=limit)

    async def index_document(self, collection: str, doc_id: str, content: str, metadata: dict) -> bool:
        try:
            vector = self.embedding_service.embed_text(content)
            self.client.upsert(collection_name=collection, points=[{
                "id": doc_id, "vector": vector,
                "payload": {"content": content, **metadata},
            }])
            return True
        except Exception as e:
            logger.error(f"Indexing error: {e}")
            return False

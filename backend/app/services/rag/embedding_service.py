"""Embedding service with dual backend: OpenAI API (primary) or local sentence-transformers (fallback).

The OpenAI embedding backend is lightweight (no torch/CUDA required) and
produces high-quality vectors via ``text-embedding-3-small``.

The local sentence-transformers backend is available as an optional fallback
for offline/air-gapped deployments; it requires the ``[ml]`` optional
dependency group.

Usage::

    from app.services.rag.embedding_service import EmbeddingService

    # Uses OpenAI by default (reads OPENAI_API_KEY from settings)
    svc = EmbeddingService()
    vec = await svc.aembed_text("Pan jest moim pasterzem")
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Default models
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
LOCAL_MODEL_NAME = "intfloat/multilingual-e5-large"

_E5_QUERY_PREFIX = "query: "
_E5_PASSAGE_PREFIX = "passage: "


class EmbeddingService:
    """Generates text embeddings via OpenAI API or local sentence-transformers.

    Features:
        - OpenAI API as primary backend (no torch dependency)
        - Local sentence-transformers as optional fallback
        - Lazy model loading
        - LRU caching for repeated queries
        - Batch embedding support
        - Async API for OpenAI backend
    """

    def __init__(
        self,
        backend: str = "openai",
        model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        self._backend = backend
        self._device = device
        self._local_model: SentenceTransformer | None = None
        self._openai_client: Any = None

        if backend == "openai":
            self._model_name = model_name or OPENAI_EMBEDDING_MODEL
        else:
            self._model_name = model_name or LOCAL_MODEL_NAME

    # ------------------------------------------------------------------
    # OpenAI backend
    # ------------------------------------------------------------------

    def _get_openai_client(self) -> Any:
        if self._openai_client is None:
            from openai import OpenAI
            from app.core.config import settings
            self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY or None)
            logger.info("OpenAI embedding client initialised (model=%s)", self._model_name)
        return self._openai_client

    def _get_async_openai_client(self) -> Any:
        from openai import AsyncOpenAI
        from app.core.config import settings
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)

    async def aembed_text(self, text: str) -> list[float]:
        """Async embed a single text using OpenAI API."""
        if self._backend != "openai":
            return self.embed_text(text)

        client = self._get_async_openai_client()
        response = await client.embeddings.create(
            model=self._model_name,
            input=text,
        )
        return response.data[0].embedding

    async def aembed_batch(self, texts: list[str]) -> list[list[float]]:
        """Async embed a batch of texts using OpenAI API."""
        if not texts:
            return []

        if self._backend != "openai":
            return self.embed_batch(texts)

        client = self._get_async_openai_client()
        response = await client.embeddings.create(
            model=self._model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]

    # ------------------------------------------------------------------
    # Local sentence-transformers backend
    # ------------------------------------------------------------------

    def _load_local_model(self) -> SentenceTransformer:
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading local embedding model: %s", self._model_name)
                self._local_model = SentenceTransformer(
                    self._model_name, device=self._device
                )
                logger.info(
                    "Local embedding model loaded (dim=%d)",
                    self._local_model.get_sentence_embedding_dimension(),
                )
            except ImportError:
                raise ImportError(
                    "sentence-transformers is not installed. "
                    "Install with: pip install sentence-transformers torch"
                )
        return self._local_model

    # ------------------------------------------------------------------
    # Sync API (works with both backends)
    # ------------------------------------------------------------------

    def embed_text(self, text: str, *, is_query: bool = True) -> list[float]:
        """Embed a single text string and return the vector."""
        if self._backend == "openai":
            client = self._get_openai_client()
            response = client.embeddings.create(
                model=self._model_name,
                input=text,
            )
            return response.data[0].embedding

        return self._cached_local_embed(self._prepare(text, is_query=is_query))

    def embed_batch(
        self,
        texts: list[str],
        *,
        is_query: bool = True,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> list[list[float]]:
        """Embed a batch of texts."""
        if not texts:
            return []

        if self._backend == "openai":
            client = self._get_openai_client()
            response = client.embeddings.create(
                model=self._model_name,
                input=texts,
            )
            return [item.embedding for item in response.data]

        prepared = [self._prepare(t, is_query=is_query) for t in texts]
        model = self._load_local_model()
        embeddings = model.encode(
            prepared,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,
        )
        return [vec.tolist() for vec in embeddings]

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        if self._backend == "openai":
            # text-embedding-3-small = 1536 dims
            return 1536
        return int(self._load_local_model().get_sentence_embedding_dimension())

    # ------------------------------------------------------------------
    # Internal helpers (local backend)
    # ------------------------------------------------------------------

    def _prepare(self, text: str, *, is_query: bool) -> str:
        if "e5" in self._model_name.lower():
            prefix = _E5_QUERY_PREFIX if is_query else _E5_PASSAGE_PREFIX
            if not text.startswith(prefix):
                return f"{prefix}{text}"
        return text

    @lru_cache(maxsize=2048)
    def _cached_local_embed(self, text: str) -> list[float]:
        model = self._load_local_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

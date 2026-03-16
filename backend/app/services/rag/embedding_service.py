"""Embedding service wrapping sentence-transformers for vector generation."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "intfloat/multilingual-e5-large"
_E5_QUERY_PREFIX = "query: "
_E5_PASSAGE_PREFIX = "passage: "


class EmbeddingService:
    """Generates text embeddings using sentence-transformers.

    Features:
        - Lazy model loading (loaded on first use)
        - LRU caching for repeated queries
        - Configurable model name
        - Batch embedding support
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, device: str | None = None) -> None:
        self._model_name = model_name
        self._device = device
        self._model: SentenceTransformer | None = None

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def _load_model(self) -> SentenceTransformer:
        """Lazily load the sentence-transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model: %s", self._model_name)
                self._model = SentenceTransformer(self._model_name, device=self._device)
                logger.info(
                    "Embedding model loaded (dim=%d)",
                    self._model.get_sentence_embedding_dimension(),
                )
            except Exception:
                logger.exception("Failed to load embedding model %s", self._model_name)
                raise
        return self._model

    @property
    def model(self) -> SentenceTransformer:
        return self._load_model()

    @property
    def dimension(self) -> int:
        """Return the embedding dimension of the loaded model."""
        return int(self.model.get_sentence_embedding_dimension())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed_text(self, text: str, *, is_query: bool = True) -> list[float]:
        """Embed a single text string and return the vector.

        For E5-family models the text is automatically prefixed with the
        appropriate ``query: `` or ``passage: `` tag.

        Args:
            text: The input text to embed.
            is_query: If *True* (default) prefix with ``query: ``, otherwise
                use ``passage: ``.  Only relevant for E5 models.

        Returns:
            A list of floats representing the embedding vector.
        """
        return self._cached_embed(self._prepare(text, is_query=is_query))

    def embed_batch(
        self,
        texts: list[str],
        *,
        is_query: bool = True,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> list[list[float]]:
        """Embed a batch of texts.

        Args:
            texts: List of input strings.
            is_query: Whether to treat inputs as queries (prefix).
            batch_size: Encoding batch size forwarded to sentence-transformers.
            show_progress: Show a progress bar during encoding.

        Returns:
            A list of embedding vectors.
        """
        if not texts:
            return []

        prepared = [self._prepare(t, is_query=is_query) for t in texts]
        model = self._load_model()
        embeddings = model.encode(
            prepared,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,
        )
        return [vec.tolist() for vec in embeddings]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prepare(self, text: str, *, is_query: bool) -> str:
        """Add model-specific prefix when using E5 models."""
        if "e5" in self._model_name.lower():
            prefix = _E5_QUERY_PREFIX if is_query else _E5_PASSAGE_PREFIX
            if not text.startswith(prefix):
                return f"{prefix}{text}"
        return text

    @lru_cache(maxsize=2048)
    def _cached_embed(self, text: str) -> list[float]:
        """LRU-cached embedding computation."""
        model = self._load_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

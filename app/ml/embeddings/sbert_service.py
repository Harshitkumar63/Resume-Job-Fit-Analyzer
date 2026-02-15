"""
Sentence-BERT embedding service.

Wraps the sentence-transformers library with:
- Lazy model loading
- Batch encoding support
- Numpy output for downstream FAISS compatibility
- L2 normalization option for cosine similarity via inner product
"""
from __future__ import annotations

import logging
from typing import Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.exceptions import ModelLoadError

logger = logging.getLogger(__name__)


class SBERTService:
    """
    Embedding service backed by Sentence-BERT.

    Designed as a singleton (via DI) — the model is loaded once and reused.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        batch_size: int = 32,
        normalize: bool = True,
    ):
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._normalize = normalize
        self._model: Optional[SentenceTransformer] = None

    def _load_model(self) -> None:
        """Lazy-load the SBERT model."""
        if self._model is not None:
            return
        try:
            logger.info("Loading SBERT model: %s on %s", self._model_name, self._device)
            self._model = SentenceTransformer(self._model_name, device=self._device)
            logger.info("SBERT model loaded (dim=%d)", self.dimension)
        except Exception as exc:
            raise ModelLoadError(self._model_name, str(exc)) from exc

    @property
    def dimension(self) -> int:
        """Return the embedding dimensionality."""
        self._load_model()
        return self._model.get_sentence_embedding_dimension()

    def encode(
        self,
        texts: Union[str, list[str]],
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Encode text(s) into dense embeddings.

        Args:
            texts: Single string or list of strings.
            show_progress: Show tqdm progress bar.

        Returns:
            np.ndarray of shape (n, dim) with float32 dtype.
            If a single string is passed, shape is (1, dim).
        """
        self._load_model()

        if isinstance(texts, str):
            texts = [texts]

        embeddings = self._model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=self._normalize,
        )

        # Ensure float32 for FAISS compatibility
        embeddings = embeddings.astype(np.float32)

        logger.debug("Encoded %d texts → shape %s", len(texts), embeddings.shape)
        return embeddings

    def similarity(self, embeddings_a: np.ndarray, embeddings_b: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity matrix between two sets of embeddings.

        If embeddings are L2-normalized (default), dot product == cosine similarity.

        Args:
            embeddings_a: Shape (n, dim)
            embeddings_b: Shape (m, dim)

        Returns:
            Similarity matrix of shape (n, m).
        """
        if self._normalize:
            return embeddings_a @ embeddings_b.T
        else:
            # Manual cosine similarity
            norm_a = embeddings_a / (np.linalg.norm(embeddings_a, axis=1, keepdims=True) + 1e-9)
            norm_b = embeddings_b / (np.linalg.norm(embeddings_b, axis=1, keepdims=True) + 1e-9)
            return norm_a @ norm_b.T

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._model is not None

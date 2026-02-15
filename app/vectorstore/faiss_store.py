"""
FAISS vector store service.

Uses HNSW (Hierarchical Navigable Small World) index for approximate
nearest neighbor search. HNSW chosen over IVF for:
- No training phase required (important for small-to-medium skill ontologies)
- Better recall at low latency
- Good scaling to ~1M vectors

The store is designed to be populated once at startup with canonical
skill embeddings, then queried at inference time.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from app.core.exceptions import VectorStoreError

logger = logging.getLogger(__name__)


class FAISSStore:
    """
    FAISS HNSW-backed vector store for skill embeddings.

    Lifecycle:
        1. Instantiate with dimension + HNSW parameters
        2. Call build_index() with embeddings + labels
        3. Call search() to find nearest neighbors
    """

    def __init__(
        self,
        dimension: int = 384,
        m: int = 32,
        ef_construction: int = 200,
        ef_search: int = 64,
    ):
        """
        Args:
            dimension: Embedding vector size (must match SBERT output).
            m: HNSW graph degree. Higher = better recall, more memory.
            ef_construction: Build-time beam width. Higher = slower build, better graph.
            ef_search: Query-time beam width. Higher = slower query, better recall.
        """
        self._dimension = dimension
        self._m = m
        self._ef_construction = ef_construction
        self._ef_search = ef_search
        self._index: Optional[faiss.IndexHNSWFlat] = None
        self._labels: list[str] = []

    def build_index(self, embeddings: np.ndarray, labels: list[str]) -> None:
        """
        Build the HNSW index from a matrix of embeddings.

        Args:
            embeddings: (n, dimension) float32 array. Must be L2-normalized
                        if you want cosine similarity via inner product.
            labels: Parallel list of n label strings (canonical skill names).

        Raises:
            VectorStoreError: On dimension mismatch or build failure.
        """
        if embeddings.shape[1] != self._dimension:
            raise VectorStoreError(
                f"Dimension mismatch: expected {self._dimension}, got {embeddings.shape[1]}"
            )
        if embeddings.shape[0] != len(labels):
            raise VectorStoreError(
                f"Embedding/label count mismatch: {embeddings.shape[0]} vs {len(labels)}"
            )

        try:
            # IndexHNSWFlat stores raw vectors + HNSW graph
            # Using inner product (IP) because embeddings are L2-normalized
            index = faiss.IndexHNSWFlat(self._dimension, self._m, faiss.METRIC_INNER_PRODUCT)
            index.hnsw.efConstruction = self._ef_construction
            index.hnsw.efSearch = self._ef_search

            embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)
            index.add(embeddings)

            self._index = index
            self._labels = list(labels)

            logger.info(
                "FAISS HNSW index built: %d vectors, dim=%d, M=%d",
                index.ntotal, self._dimension, self._m,
            )
        except Exception as exc:
            raise VectorStoreError(f"Index build failed: {exc}") from exc

    def search(
        self,
        query_embeddings: np.ndarray,
        top_k: int = 5,
    ) -> list[list[tuple[str, float]]]:
        """
        Search the index for nearest neighbors.

        Args:
            query_embeddings: (n, dimension) float32 array.
            top_k: Number of results per query.

        Returns:
            List of n result lists, each containing (label, score) tuples
            sorted by descending similarity.

        Raises:
            VectorStoreError: If index is not built.
        """
        if self._index is None:
            raise VectorStoreError("Index not built — call build_index() first")

        query_embeddings = np.ascontiguousarray(query_embeddings, dtype=np.float32)
        top_k = min(top_k, self._index.ntotal)

        try:
            scores, indices = self._index.search(query_embeddings, top_k)
            results: list[list[tuple[str, float]]] = []

            for row_scores, row_indices in zip(scores, indices):
                row_results: list[tuple[str, float]] = []
                for score, idx in zip(row_scores, row_indices):
                    if idx < 0:  # FAISS returns -1 for missing results
                        continue
                    row_results.append((self._labels[idx], float(score)))
                results.append(row_results)

            return results
        except Exception as exc:
            raise VectorStoreError(f"Search failed: {exc}") from exc

    def save(self, path: Path) -> None:
        """Persist the index to disk."""
        if self._index is None:
            raise VectorStoreError("No index to save")
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(path))
        logger.info("FAISS index saved to %s", path)

    def load(self, path: Path, labels: list[str]) -> None:
        """Load a pre-built index from disk."""
        if not path.exists():
            raise VectorStoreError(f"Index file not found: {path}")
        self._index = faiss.read_index(str(path))
        self._labels = labels
        logger.info("FAISS index loaded from %s (%d vectors)", path, self._index.ntotal)

    @property
    def is_built(self) -> bool:
        return self._index is not None and self._index.ntotal > 0

    @property
    def size(self) -> int:
        return self._index.ntotal if self._index else 0

"""
Embedding service: loads Sentence-BERT model, generates embeddings, and provides
an optional in-process numpy similarity index.

Production search runs through pgvector (see vector_search.py); the in-memory
index here exists only for the standalone evaluation harness (eval/benchmark.py),
which has no database. It is intentionally minimal: build once, search, no
persistence and no incremental mutation.
"""
import numpy as np
import logging
import threading
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize each row so inner product equals cosine similarity.

    Zero vectors are left untouched (norm forced to 1) to avoid division by zero.
    """
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class EmbeddingService:
    """Singleton-style service for embedding generation and in-memory indexing.

    Index mutations are guarded by ``_lock`` so concurrent requests within a
    process cannot race on the matrix. The index lives in process memory and is
    used only by the evaluation harness; the production app searches pgvector.
    """

    def __init__(self):
        self.model: SentenceTransformer = None
        self.cross_encoder = None  # lazily loaded CrossEncoder for re-ranking
        self._matrix: np.ndarray = None  # normalized section embeddings, one per row
        self.dimension: int = 384  # paraphrase-multilingual-MiniLM-L12-v2 output dimension
        self.id_map: list[dict] = []  # Maps matrix row index → section metadata
        self._lock = threading.Lock()
        self._ce_lock = threading.Lock()

    def load_model(self):
        """Load the sentence-transformer model into memory."""
        logger.info(f"Loading model: {settings.MODEL_NAME}")
        self.model = SentenceTransformer(settings.MODEL_NAME)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")

    # ── Cross-encoder re-ranking ────────────────────────────
    def load_cross_encoder(self):
        """Load the cross-encoder re-ranking model on first use.

        Imported lazily (and only when re-ranking is actually requested) so the
        bi-encoder-only deployment never pays the extra model download, and so
        the stubbed unit-test environment never needs the real dependency.
        """
        if self.cross_encoder is not None:
            return
        with self._ce_lock:
            if self.cross_encoder is not None:
                return
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading cross-encoder: {settings.RERANK_MODEL}")
            self.cross_encoder = CrossEncoder(settings.RERANK_MODEL)
            logger.info("Cross-encoder loaded")

    def rerank(self, query: str, candidates: list[str]) -> np.ndarray:
        """Score each candidate's relevance to ``query`` with the cross-encoder.

        Returns scores squashed to [0, 1] via a logistic sigmoid so they can be
        blended with cosine similarity on the same scale. Returns an empty array
        for empty input.
        """
        if not candidates:
            return np.empty(0, dtype=np.float32)
        if self.cross_encoder is None:
            self.load_cross_encoder()
        pairs = [[query, c] for c in candidates]
        raw = self.cross_encoder.predict(
            pairs, convert_to_numpy=True, show_progress_bar=False
        )
        # CrossEncoder emits unbounded relevance logits; logistic-squash to [0,1].
        return 1.0 / (1.0 + np.exp(-raw.astype(np.float64)))

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode a list of texts into L2-normalized embeddings (cosine-ready)."""
        if self.model is None:
            self.load_model()
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        # L2 normalize for cosine similarity via inner product
        return _l2_normalize(embeddings)

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text string."""
        return self.encode([text])[0]

    # ── In-memory index (evaluation harness only) ───────────

    def build_index(self, embeddings: np.ndarray, metadata: list[dict]):
        """Build a fresh in-memory index from embeddings and their metadata."""
        with self._lock:
            self._matrix = _l2_normalize(embeddings)
            self.id_map = metadata
            logger.info(f"In-memory index built with {len(self.id_map)} vectors")

    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> list[dict]:
        """
        Search the in-memory index for the top_k most cosine-similar vectors.
        Returns a list of {**metadata, score} dicts.
        """
        if self._matrix is None or len(self._matrix) == 0:
            logger.warning("In-memory index is empty or not initialized")
            return []

        query = _l2_normalize(query_embedding)[0]
        # Rows are normalized, so the inner product is cosine similarity.
        scores = self._matrix @ query
        k = min(top_k, len(self._matrix))
        # argpartition picks the top-k cheaply; then sort just those by score.
        top_idx = np.argpartition(-scores, k - 1)[:k]
        top_idx = top_idx[np.argsort(-scores[top_idx])]

        return [{**self.id_map[i], "score": float(scores[i])} for i in top_idx]


# Module-level singleton
embedding_service = EmbeddingService()

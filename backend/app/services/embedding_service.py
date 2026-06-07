"""
Embedding service: loads Sentence-BERT model, generates embeddings,
manages FAISS index for fast similarity search.
"""
import numpy as np
import faiss
import os
import pickle
import logging
import threading
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """Singleton-style service for embedding generation and FAISS indexing.

    Index mutations and persistence are guarded by ``_lock`` so concurrent
    requests within a process cannot corrupt the in-memory index or race on the
    on-disk files. NOTE: the index lives in process memory, so the app must run
    with a SINGLE worker — with multiple workers each holds its own copy and
    runtime add/delete mutations would not propagate. See tests/README.md.
    """

    def __init__(self):
        self.model: SentenceTransformer = None
        self.cross_encoder = None  # lazily loaded CrossEncoder for re-ranking
        self.index: faiss.IndexFlatIP = None  # Inner-product (cosine after normalization)
        self.dimension: int = 384  # paraphrase-multilingual-MiniLM-L12-v2 output dimension
        self.id_map: list[dict] = []  # Maps FAISS row index → section metadata
        self._index_path = settings.FAISS_INDEX_PATH
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
        """Encode a list of texts into normalized embeddings."""
        if self.model is None:
            self.load_model()
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        # L2 normalize for cosine similarity via inner product
        faiss.normalize_L2(embeddings)
        return embeddings

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text string."""
        return self.encode([text])[0]

    # ── FAISS Index Management ──────────────────────────────

    def build_index(self, embeddings: np.ndarray, metadata: list[dict]):
        """Build a new FAISS index from embeddings and metadata."""
        with self._lock:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(embeddings.astype(np.float32))
            self.id_map = metadata
            logger.info(f"FAISS index built with {self.index.ntotal} vectors")

    def add_to_index(self, embeddings: np.ndarray, metadata: list[dict]):
        """Add embeddings to the existing FAISS index."""
        if self.index is None:
            self.build_index(embeddings, metadata)
            return
        with self._lock:
            self.index.add(embeddings.astype(np.float32))
            self.id_map.extend(metadata)
            logger.info(f"Added {len(metadata)} vectors. Total: {self.index.ntotal}")

    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> list[dict]:
        """
        Search the FAISS index for top_k most similar vectors.
        Returns list of {metadata, score} dicts.
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS index is empty or not initialized")
            return []

        query = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query)
        scores, indices = self.index.search(query, min(top_k, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            result = {**self.id_map[idx], "score": float(score)}
            results.append(result)
        return results

    # ── Persistence ─────────────────────────────────────────

    def save_index(self):
        """Persist the FAISS index and metadata atomically.

        Each file is written to a ``.tmp`` sibling and then ``os.replace``d into
        place — an atomic rename on the same filesystem — so a crash or a
        concurrent reader never observes a half-written index that would fail to
        load on the next startup.
        """
        if self.index is None:
            return
        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        faiss_path = f"{self._index_path}.faiss"
        meta_path = f"{self._index_path}.meta"

        with self._lock:
            faiss_tmp = f"{faiss_path}.tmp"
            meta_tmp = f"{meta_path}.tmp"
            faiss.write_index(self.index, faiss_tmp)
            with open(meta_tmp, "wb") as f:
                pickle.dump({"id_map": self.id_map, "model_name": settings.MODEL_NAME}, f)
            os.replace(faiss_tmp, faiss_path)
            os.replace(meta_tmp, meta_path)
            logger.info(f"FAISS index saved to {self._index_path}")

    def load_index(self) -> bool:
        """
        Load a persisted FAISS index from disk.
        Returns False (triggering re-embed) if the saved model name differs from the
        current model — prevents stale embeddings after a model upgrade.
        """
        faiss_path = f"{self._index_path}.faiss"
        meta_path = f"{self._index_path}.meta"
        if not (os.path.exists(faiss_path) and os.path.exists(meta_path)):
            logger.info("No saved FAISS index found")
            return False

        self.index = faiss.read_index(faiss_path)
        with open(meta_path, "rb") as f:
            data = pickle.load(f)

        # Support legacy format (plain list) and new dict format
        if isinstance(data, list):
            saved_model = ""
            self.id_map = data
        else:
            saved_model = data.get("model_name", "")
            self.id_map = data["id_map"]

        if saved_model != settings.MODEL_NAME:
            logger.warning(
                f"Embedding model changed: '{saved_model}' → '{settings.MODEL_NAME}'. "
                "Discarding stale index; will re-embed all sections."
            )
            self.index = None
            self.id_map = []
            return False

        logger.info(f"FAISS index loaded: {self.index.ntotal} vectors (model={saved_model})")
        return True


# Module-level singleton
embedding_service = EmbeddingService()

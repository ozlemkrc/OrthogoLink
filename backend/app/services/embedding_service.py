"""
Embedding service: loads Sentence-BERT model, generates embeddings,
manages FAISS index for fast similarity search.
"""
import numpy as np
import faiss
import os
import pickle
import logging
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """Singleton-style service for embedding generation and FAISS indexing."""

    def __init__(self):
        self.model: SentenceTransformer = None
        self.index: faiss.IndexFlatIP = None  # Inner-product (cosine after normalization)
        self.dimension: int = 384  # all-MiniLM-L6-v2 output dimension
        self.id_map: list[dict] = []  # Maps FAISS row index → section metadata
        self._index_path = settings.FAISS_INDEX_PATH

    def load_model(self):
        """Load the sentence-transformer model into memory."""
        logger.info(f"Loading model: {settings.MODEL_NAME}")
        self.model = SentenceTransformer(settings.MODEL_NAME)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")

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
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings.astype(np.float32))
        self.id_map = metadata
        logger.info(f"FAISS index built with {self.index.ntotal} vectors")

    def add_to_index(self, embeddings: np.ndarray, metadata: list[dict]):
        """Add embeddings to the existing FAISS index."""
        if self.index is None:
            self.build_index(embeddings, metadata)
            return
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
        """Persist the FAISS index and metadata to disk."""
        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, f"{self._index_path}.faiss")
            with open(f"{self._index_path}.meta", "wb") as f:
                pickle.dump(self.id_map, f)
            logger.info(f"FAISS index saved to {self._index_path}")

    def load_index(self):
        """Load a persisted FAISS index from disk."""
        faiss_path = f"{self._index_path}.faiss"
        meta_path = f"{self._index_path}.meta"
        if os.path.exists(faiss_path) and os.path.exists(meta_path):
            self.index = faiss.read_index(faiss_path)
            with open(meta_path, "rb") as f:
                self.id_map = pickle.load(f)
            logger.info(f"FAISS index loaded: {self.index.ntotal} vectors")
            return True
        logger.info("No saved FAISS index found")
        return False


# Module-level singleton
embedding_service = EmbeddingService()

"""
pgvector-backed similarity search.

This is the production search backend (``SEARCH_BACKEND="pgvector"``). It queries
embeddings stored in PostgreSQL, so the result set is shared across processes — the
API can run with multiple uvicorn workers and search results reflect runtime course
add/update/delete/import immediately, with no in-memory index to keep in sync.

The query vector is rendered as a plain numeric literal (``'[...]'::vector``) rather
than a bound parameter. The values come straight from the embedding model (floats),
so there is no injection surface, and this avoids per-driver pgvector codec
registration (asyncpg/psycopg2) entirely — the same SQL works everywhere.
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)

# Returned columns mirror the dict shape produced by EmbeddingService.search so
# the comparison pipeline is backend-agnostic.
_SEARCH_SQL = """
    SELECT cs.course_id,
           c.code        AS course_code,
           c.name        AS course_name,
           c.university  AS university,
           c.faculty     AS faculty,
           c.department  AS department,
           cs.heading    AS section_heading,
           cs.content    AS section_content,
           1 - (cs.embedding_vec <=> '{lit}'::vector) AS score
    FROM course_sections cs
    JOIN courses c ON c.id = cs.course_id
    WHERE cs.embedding_vec IS NOT NULL
    ORDER BY cs.embedding_vec <=> '{lit}'::vector
    LIMIT :k
"""


def to_vector_literal(vec) -> str:
    """Render an embedding as a pgvector text literal, e.g. ``[0.1,-0.2,...]``."""
    arr = np.asarray(vec, dtype=np.float32).ravel()
    return "[" + ",".join(f"{x:.8f}" for x in arr.tolist()) + "]"


def _engine():
    """Lazily resolve the synchronous engine (avoids importing the DB layer at
    module import time, which keeps the stubbed unit-test env clean)."""
    from app.core.database import sync_engine
    return sync_engine


def search_sections(query_embedding, top_k: int = 10) -> list[dict]:
    """Return the ``top_k`` most cosine-similar course sections to the query.

    Each result dict has: course_id, course_code, course_name, university,
    faculty, department, section_heading, section_content, score (1 = identical).
    """
    from sqlalchemy import text

    lit = to_vector_literal(query_embedding)
    sql = text(_SEARCH_SQL.format(lit=lit))
    try:
        with _engine().connect() as conn:
            rows = conn.execute(sql, {"k": int(top_k)}).mappings().all()
    except Exception:  # pragma: no cover - surfaced as empty result, logged
        logger.exception("pgvector search failed")
        return []
    return [dict(r) for r in rows]

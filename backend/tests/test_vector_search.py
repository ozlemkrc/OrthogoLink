"""
Unit tests for the pgvector literal helper.

``to_vector_literal`` renders an embedding directly into SQL (``'[...]'::vector``),
so its output must be a well-formed, numeric-only pgvector literal — any stray
character would be both a syntax error and, in principle, an injection vector.
These tests pin that contract. (The full search query is exercised against a real
database by the integration/eval path, not here.)
"""
import re

import numpy as np

from app.services.vector_search import to_vector_literal


def test_literal_is_bracketed_and_comma_separated():
    out = to_vector_literal(np.array([0.1, 0.2, 0.3], dtype=np.float32))
    assert out.startswith("[") and out.endswith("]")
    assert out.count(",") == 2


def test_literal_contains_only_numeric_characters():
    out = to_vector_literal(np.array([0.5, -0.25, 1.0, -1.0], dtype=np.float32))
    # Only digits, sign, decimal point, comma, and the enclosing brackets.
    assert re.fullmatch(r"\[-?\d+\.\d+(,-?\d+\.\d+)*\]", out)


def test_literal_preserves_sign_and_order():
    out = to_vector_literal([1.0, -2.0, 3.0])
    nums = [float(x) for x in out.strip("[]").split(",")]
    assert nums == [1.0, -2.0, 3.0]


def test_literal_accepts_list_and_ndarray_equally():
    arr = np.array([0.1, 0.2], dtype=np.float32)
    assert to_vector_literal(arr) == to_vector_literal(arr.tolist())


def test_literal_flattens_2d_single_row():
    out = to_vector_literal(np.array([[0.1, 0.2, 0.3]], dtype=np.float32))
    assert out.count(",") == 2  # flattened to 3 values

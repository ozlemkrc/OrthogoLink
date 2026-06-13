"""
Shared pytest configuration.

The deterministic-logic unit tests (``test_comparison_service.py``,
``test_pdf_service.py``) exercise pure functions that do **not** need the
embedding model or PDF parsing at runtime — those heavy dependencies are only
imported at module load time. To keep the unit tests fast and runnable on any
machine (no ~90MB model download), we register lightweight stub modules in
``sys.modules`` *before* the app packages are imported. The real dependencies
are still used by the evaluation harness (``eval/benchmark.py``), which runs
against the actual model.
"""
import os
import sys
import types
from pathlib import Path

# Make ``app`` importable (tests/ lives next to app/).
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _install_stub(name: str, attrs: dict | None = None) -> types.ModuleType:
    """Register a minimal stub module if the real one is unavailable."""
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    for key, value in (attrs or {}).items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _ensure_heavy_stubs() -> None:
    """Stub sentence_transformers / PyPDF2 only if not installed."""
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        class _StubModel:
            def __init__(self, *a, **k):
                pass

            def get_sentence_embedding_dimension(self):
                return 384

            def encode(self, *a, **k):
                raise RuntimeError(
                    "SentenceTransformer stub cannot encode; install "
                    "sentence-transformers to run the evaluation harness."
                )

        _install_stub("sentence_transformers", {"SentenceTransformer": _StubModel})

    try:
        import PyPDF2  # noqa: F401
    except ImportError:
        class _StubReader:
            def __init__(self, *a, **k):
                self.pages = []

        _install_stub("PyPDF2", {"PdfReader": _StubReader})


# Provide a default secret so importing config never depends on a real .env.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
_ensure_heavy_stubs()

"""
Unit tests for the input-size guards used by the comparison routes.
"""
import pytest

from app.services.input_guard import (
    validate_syllabus_text,
    check_upload_size,
    InputValidationError,
)
from app.core.config import get_settings

settings = get_settings()


# ── validate_syllabus_text ───────────────────────────────────────

def test_valid_text_is_returned_stripped():
    text = "  " + ("Course content about algorithms and data structures. " * 3) + "  "
    out = validate_syllabus_text(text)
    assert out == text.strip()
    assert not out.startswith(" ")


def test_too_short_text_rejected():
    with pytest.raises(InputValidationError) as exc:
        validate_syllabus_text("too short")
    assert "too short" in str(exc.value).lower()


def test_empty_and_none_rejected():
    with pytest.raises(InputValidationError):
        validate_syllabus_text("")
    with pytest.raises(InputValidationError):
        validate_syllabus_text(None)


def test_too_long_text_rejected():
    text = "a" * (settings.MAX_INPUT_CHARS + 1)
    with pytest.raises(InputValidationError) as exc:
        validate_syllabus_text(text)
    assert "too large" in str(exc.value).lower()


def test_at_max_boundary_is_accepted():
    text = "a" * settings.MAX_INPUT_CHARS
    # Exactly at the limit must pass (boundary is inclusive).
    assert validate_syllabus_text(text) == text


def test_custom_min_overrides_default():
    # A 60-char string passes the default floor but not a custom 100 floor.
    text = "x" * 60
    assert validate_syllabus_text(text, min_chars=50)
    with pytest.raises(InputValidationError):
        validate_syllabus_text(text, min_chars=100)


def test_whitespace_only_counts_as_too_short():
    with pytest.raises(InputValidationError):
        validate_syllabus_text("    \n\t   ")


# ── check_upload_size ────────────────────────────────────────────

def test_upload_within_limit_passes():
    check_upload_size(1024)  # 1 KB, well under the cap — no raise


def test_upload_at_limit_passes():
    check_upload_size(settings.MAX_UPLOAD_BYTES)


def test_upload_over_limit_rejected():
    with pytest.raises(InputValidationError) as exc:
        check_upload_size(settings.MAX_UPLOAD_BYTES + 1)
    assert "too large" in str(exc.value).lower()


def test_upload_custom_max():
    with pytest.raises(InputValidationError):
        check_upload_size(2048, max_bytes=1024)

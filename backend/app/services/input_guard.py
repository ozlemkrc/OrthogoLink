"""
Input validation guards for the comparison pipeline.

Kept as pure functions (no FastAPI / DB imports) so they are trivially unit
testable and reusable across the text, PDF, and cross-university routes. Routes
translate :class:`InputValidationError` into an HTTP 400 response.
"""
from app.core.config import get_settings

settings = get_settings()


class InputValidationError(ValueError):
    """Raised when user-supplied syllabus input is too short or too large."""


def validate_syllabus_text(
    text: str,
    *,
    min_chars: int | None = None,
    max_chars: int | None = None,
) -> str:
    """Validate and normalise syllabus text.

    Returns the stripped text when valid; raises :class:`InputValidationError`
    with a user-facing message otherwise. ``min``/``max`` default to the
    configured limits but are overridable (e.g. for extracted PDF text).
    """
    min_chars = settings.MIN_INPUT_CHARS if min_chars is None else min_chars
    max_chars = settings.MAX_INPUT_CHARS if max_chars is None else max_chars

    cleaned = (text or "").strip()
    length = len(cleaned)

    if length < min_chars:
        raise InputValidationError(
            "Input text is too short. Please provide a meaningful syllabus "
            f"(at least {min_chars} characters)."
        )
    if length > max_chars:
        raise InputValidationError(
            f"Input text is too large ({length:,} characters). "
            f"Please limit it to {max_chars:,} characters."
        )
    return cleaned


def check_upload_size(num_bytes: int, *, max_bytes: int | None = None) -> None:
    """Raise :class:`InputValidationError` if an uploaded file exceeds the cap."""
    max_bytes = settings.MAX_UPLOAD_BYTES if max_bytes is None else max_bytes
    if num_bytes > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise InputValidationError(
            f"Uploaded file is too large. Maximum allowed size is {mb:.0f} MB."
        )

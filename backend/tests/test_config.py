"""
Unit tests for production-safety config checks.

These guard the fail-loud behavior: a deploy must not silently run with the
built-in default JWT secret (which would let anyone forge auth tokens).
"""
from app.core.config import Settings


def test_default_secret_is_a_blocking_issue():
    s = Settings(SECRET_KEY=Settings._DEFAULT_SECRET)
    issues = s.production_issues()
    assert any("SECRET_KEY" in i for i in issues)


def test_custom_secret_has_no_blocking_issues():
    s = Settings(SECRET_KEY="a-strong-unique-random-value-123456")
    assert s.production_issues() == []


def test_default_db_credentials_raise_a_warning_not_an_issue():
    s = Settings(
        SECRET_KEY="a-strong-unique-random-value-123456",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@db:5432/orthogonality",
    )
    # Default DB creds are advisory, never blocking.
    assert s.production_issues() == []
    assert any("postgres:postgres" in w for w in s.production_warnings())


def test_strong_db_credentials_have_no_warning():
    s = Settings(
        SECRET_KEY="a-strong-unique-random-value-123456",
        DATABASE_URL="postgresql+asyncpg://app:s3cr3t@db:5432/orthogonality",
    )
    assert s.production_warnings() == []

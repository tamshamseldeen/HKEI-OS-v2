"""Tests for stable generated-article parsing errors."""

import pytest

from src.parsing.parsing_error import ParsingError


ERROR_CODES = (
    "GENERATED_CONTENT_EMPTY",
    "ARTICLE_HEADLINE_MISSING",
    "ARTICLE_HEADLINE_MULTIPLE",
    "ARTICLE_BODY_MISSING",
    "UNSUPPORTED_GENERATED_FORMAT",
    "GENERATED_ARTICLE_INVALID",
)


def test_parsing_error_stores_code_and_original_exception() -> None:
    """Store stable code and internal original exception unchanged."""
    original = ValueError("private parsing details")
    error = ParsingError("GENERATED_ARTICLE_INVALID", original)

    assert error.code == "GENERATED_ARTICLE_INVALID"
    assert error.original_exception is original
    assert str(error) == "GENERATED_ARTICLE_INVALID"
    assert "private parsing details" not in str(error)


def test_parsing_error_accepts_no_original_exception() -> None:
    """Default the internal original exception to None."""
    error = ParsingError("GENERATED_CONTENT_EMPTY")

    assert error.original_exception is None
    assert str(error) == error.code


@pytest.mark.parametrize("code", ERROR_CODES)
def test_documented_error_codes_are_stored_unchanged(code: str) -> None:
    """Accept every documented stable parsing error code unchanged."""
    error = ParsingError(code)

    assert error.code == code
    assert str(error) == code

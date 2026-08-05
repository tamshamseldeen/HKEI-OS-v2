"""Tests for raw source validation."""

import pytest

from src.intake.source_validator import SourceValidator


@pytest.fixture
def validator() -> SourceValidator:
    """Provide a source validator."""
    return SourceValidator()


def test_fully_valid_input_returns_no_errors(validator: SourceValidator) -> None:
    """Return an empty tuple for fully valid input."""
    result = validator.validate(
        title="Title",
        body="Body",
        source_name="Source",
        source_url="https://example.com",
        language="en",
    )

    assert result == ()


def test_missing_required_fields(validator: SourceValidator) -> None:
    """Report missing required fields."""
    result = validator.validate(title=None, body=None, source_name=None)

    assert result == (
        "MISSING_TITLE",
        "MISSING_BODY",
        "MISSING_SOURCE_NAME",
    )


def test_whitespace_only_required_fields(validator: SourceValidator) -> None:
    """Report whitespace-only required fields as empty."""
    result = validator.validate(title=" ", body="\t", source_name="\n")

    assert result == ("EMPTY_TITLE", "EMPTY_BODY", "EMPTY_SOURCE_NAME")


def test_malformed_url(validator: SourceValidator) -> None:
    """Report a URL without an allowed scheme."""
    result = validator.validate(
        title="Title",
        body="Body",
        source_name="Source",
        source_url="example.com",
    )

    assert result == ("MALFORMED_URL",)


def test_valid_http_url(validator: SourceValidator) -> None:
    """Allow an HTTP URL."""
    result = validator.validate(
        title="Title",
        body="Body",
        source_name="Source",
        source_url="http://example.com",
    )

    assert result == ()


def test_valid_https_url(validator: SourceValidator) -> None:
    """Allow an HTTPS URL."""
    result = validator.validate(
        title="Title",
        body="Body",
        source_name="Source",
        source_url="https://example.com",
    )

    assert result == ()


def test_unsupported_language(validator: SourceValidator) -> None:
    """Report a language outside the supported set."""
    result = validator.validate(
        title="Title", body="Body", source_name="Source", language="fr"
    )

    assert result == ("UNSUPPORTED_LANGUAGE",)


def test_supported_arabic_language(validator: SourceValidator) -> None:
    """Allow the Arabic language code."""
    result = validator.validate(
        title="Title", body="Body", source_name="Source", language="ar"
    )

    assert result == ()


def test_supported_english_language(validator: SourceValidator) -> None:
    """Allow the English language code."""
    result = validator.validate(
        title="Title", body="Body", source_name="Source", language="en"
    )

    assert result == ()


def test_exact_error_ordering(validator: SourceValidator) -> None:
    """Return simultaneous errors in the required order."""
    result = validator.validate(
        title=None,
        body=None,
        source_name=None,
        source_url="ftp://example.com",
        language="fr",
    )

    assert result == (
        "MISSING_TITLE",
        "MISSING_BODY",
        "MISSING_SOURCE_NAME",
        "MALFORMED_URL",
        "UNSUPPORTED_LANGUAGE",
    )


def test_missing_fields_do_not_also_return_empty_errors(
    validator: SourceValidator,
) -> None:
    """Avoid empty errors for required fields that are missing."""
    result = validator.validate(title=None, body=None, source_name=None)

    assert "EMPTY_TITLE" not in result
    assert "EMPTY_BODY" not in result
    assert "EMPTY_SOURCE_NAME" not in result

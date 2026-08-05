"""Tests for the public source intake service."""

from unittest.mock import Mock

import pytest

from src.intake.normalized_source import NormalizedSource
from src.intake.source_intake import SourceIntake, SourceValidationError
from src.intake.source_normalizer import SourceNormalizer
from src.intake.source_validator import SourceValidator


def test_valid_input_returns_normalized_source() -> None:
    """Return a NormalizedSource for valid input."""
    result = SourceIntake().process(
        title="Title", body="Body", source_name="Source"
    )

    assert isinstance(result, NormalizedSource)


def test_returned_values_are_normalized() -> None:
    """Return values normalized by SourceNormalizer."""
    result = SourceIntake().process(
        title="  Saudi   Traffic  ",
        body=" First\r\n\r\n\r\n Second ",
        source_name="  News   Agency  ",
    )

    assert result.title == "Saudi Traffic"
    assert result.body == "First\n\nSecond"
    assert result.source_name == "News Agency"


def test_invalid_input_raises_source_validation_error() -> None:
    """Raise SourceValidationError when validation fails."""
    with pytest.raises(SourceValidationError):
        SourceIntake().process(title=None, body="Body", source_name="Source")


def test_validation_error_stores_exact_error_codes() -> None:
    """Store all validation codes in their original order."""
    with pytest.raises(SourceValidationError) as caught:
        SourceIntake().process(title=None, body=None, source_name=None)

    assert caught.value.errors == (
        "MISSING_TITLE",
        "MISSING_BODY",
        "MISSING_SOURCE_NAME",
    )


def test_validation_error_message_uses_required_format() -> None:
    """Format the exception message exactly as required."""
    error = SourceValidationError(("MISSING_TITLE", "MISSING_BODY"))

    assert str(error) == "Source validation failed: MISSING_TITLE, MISSING_BODY"


def test_normalizer_is_not_called_when_validation_fails() -> None:
    """Skip normalization when validation returns errors."""
    validator = Mock(spec=SourceValidator)
    validator.validate.return_value = ("MISSING_TITLE",)
    normalizer = Mock(spec=SourceNormalizer)
    intake = SourceIntake(validator=validator, normalizer=normalizer)

    with pytest.raises(SourceValidationError):
        intake.process(title=None, body="Body", source_name="Source")

    normalizer.normalize.assert_not_called()


def test_validator_is_called_exactly_once() -> None:
    """Call the validator once per process request."""
    validator = Mock(spec=SourceValidator)
    validator.validate.return_value = ()
    normalizer = Mock(spec=SourceNormalizer)
    normalizer.normalize.return_value = NormalizedSource("Title", "Body", "Source")
    intake = SourceIntake(validator=validator, normalizer=normalizer)

    intake.process(title="Title", body="Body", source_name="Source")

    validator.validate.assert_called_once_with(
        title="Title",
        body="Body",
        source_name="Source",
        source_url=None,
        language=None,
    )


def test_normalizer_is_called_exactly_once_for_valid_input() -> None:
    """Call the normalizer once after successful validation."""
    validator = Mock(spec=SourceValidator)
    validator.validate.return_value = ()
    normalizer = Mock(spec=SourceNormalizer)
    expected = NormalizedSource("Title", "Body", "Source")
    normalizer.normalize.return_value = expected
    intake = SourceIntake(validator=validator, normalizer=normalizer)

    result = intake.process(title="Title", body="Body", source_name="Source")

    normalizer.normalize.assert_called_once()
    assert result is expected


def test_dependency_injection_uses_supplied_dependencies() -> None:
    """Use the supplied validator and normalizer instances."""
    validator = Mock(spec=SourceValidator)
    validator.validate.return_value = ()
    normalizer = Mock(spec=SourceNormalizer)
    expected = NormalizedSource("Injected", "Result", "Service")
    normalizer.normalize.return_value = expected

    result = SourceIntake(validator=validator, normalizer=normalizer).process(
        title="Title", body="Body", source_name="Source"
    )

    validator.validate.assert_called_once()
    normalizer.normalize.assert_called_once()
    assert result is expected


def test_optional_metadata_is_passed_through_correctly() -> None:
    """Pass all optional metadata to the normalizer."""
    validator = Mock(spec=SourceValidator)
    validator.validate.return_value = ()
    normalizer = Mock(spec=SourceNormalizer)
    normalizer.normalize.return_value = NormalizedSource("Title", "Body", "Source")
    intake = SourceIntake(validator=validator, normalizer=normalizer)

    intake.process(
        title="Title",
        body="Body",
        source_name="Source",
        source_url="https://example.com",
        published_at="2026-08-05",
        language="en",
        country="HK",
        author="Author",
        images=("image",),
        attachments=("attachment",),
        category="News",
        tags=("tag",),
    )

    normalizer.normalize.assert_called_once_with(
        title="Title",
        body="Body",
        source_name="Source",
        source_url="https://example.com",
        published_at="2026-08-05",
        language="en",
        country="HK",
        author="Author",
        images=("image",),
        attachments=("attachment",),
        category="News",
        tags=("tag",),
    )

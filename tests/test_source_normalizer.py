"""Tests for source normalization."""

import pytest

from src.intake.normalized_source import NormalizedSource
from src.intake.source_normalizer import SourceNormalizer


@pytest.fixture
def normalizer() -> SourceNormalizer:
    """Provide a source normalizer."""
    return SourceNormalizer()


def test_trims_required_fields(normalizer: SourceNormalizer) -> None:
    """Trim leading and trailing whitespace from required fields."""
    result = normalizer.normalize(
        title="  Title  ", body="  Body  ", source_name="  Source  "
    )

    assert result.title == "Title"
    assert result.body == "Body"
    assert result.source_name == "Source"


def test_collapses_repeated_spaces_in_title(normalizer: SourceNormalizer) -> None:
    """Collapse repeated title whitespace to one space."""
    result = normalizer.normalize(
        title="  Saudi   Traffic  ", body="Body", source_name="Source"
    )

    assert result.title == "Saudi Traffic"


def test_collapses_repeated_spaces_in_source_name(
    normalizer: SourceNormalizer,
) -> None:
    """Collapse repeated source name whitespace to one space."""
    result = normalizer.normalize(
        title="Title", body="Body", source_name="  Saudi   Press  "
    )

    assert result.source_name == "Saudi Press"


def test_normalizes_crlf_and_cr_line_endings(
    normalizer: SourceNormalizer,
) -> None:
    """Convert CRLF and CR line endings to LF."""
    result = normalizer.normalize(
        title="Title", body="First\r\nSecond\rThird", source_name="Source"
    )

    assert result.body == "First\nSecond\nThird"


def test_trims_each_body_line(normalizer: SourceNormalizer) -> None:
    """Trim whitespace from every body line."""
    result = normalizer.normalize(
        title="Title", body="  First  \n\tSecond\t", source_name="Source"
    )

    assert result.body == "First\nSecond"


def test_collapses_excessive_blank_lines(normalizer: SourceNormalizer) -> None:
    """Collapse three or more newlines to two."""
    result = normalizer.normalize(
        title="Title", body="First\n\n\n\nSecond", source_name="Source"
    )

    assert result.body == "First\n\nSecond"


def test_optional_blank_strings_become_none(normalizer: SourceNormalizer) -> None:
    """Convert optional strings that trim to empty into None."""
    result = normalizer.normalize(
        title="Title",
        body="Body",
        source_name="Source",
        source_url=" ",
        published_at="\t",
        language="\n",
        country="  ",
        author="",
        category=" \t ",
    )

    assert result.source_url is None
    assert result.published_at is None
    assert result.language is None
    assert result.country is None
    assert result.author is None
    assert result.category is None


def test_tuple_entries_are_trimmed(normalizer: SourceNormalizer) -> None:
    """Trim every retained tuple entry."""
    result = normalizer.normalize(
        title="Title",
        body="Body",
        source_name="Source",
        images=(" image ",),
        attachments=(" attachment ",),
        tags=(" tag ",),
    )

    assert result.images == ("image",)
    assert result.attachments == ("attachment",)
    assert result.tags == ("tag",)


def test_empty_tuple_entries_are_removed(normalizer: SourceNormalizer) -> None:
    """Remove empty and whitespace-only tuple entries."""
    result = normalizer.normalize(
        title="Title",
        body="Body",
        source_name="Source",
        images=("", " ", "image"),
        attachments=("attachment", "\t"),
        tags=("\n", "tag", ""),
    )

    assert result.images == ("image",)
    assert result.attachments == ("attachment",)
    assert result.tags == ("tag",)


def test_tuple_types_remain_tuples(normalizer: SourceNormalizer) -> None:
    """Preserve tuple types for tuple fields."""
    result = normalizer.normalize(
        title="Title",
        body="Body",
        source_name="Source",
        images=("image",),
        attachments=("attachment",),
        tags=("tag",),
    )

    assert isinstance(result.images, tuple)
    assert isinstance(result.attachments, tuple)
    assert isinstance(result.tags, tuple)


def test_returns_normalized_source_with_normalized_values(
    normalizer: SourceNormalizer,
) -> None:
    """Return all normalized values in a NormalizedSource."""
    result = normalizer.normalize(
        title="  Saudi   Traffic  ",
        body=" First\r\n\r\n\r\n Second ",
        source_name="  News   Agency ",
        source_url=" https://example.com ",
        published_at=" 2026-08-05 ",
        language=" en ",
        country=" SA ",
        author=" Author ",
        images=(" image ", ""),
        attachments=(" attachment ", " "),
        category=" News ",
        tags=(" tag ", ""),
    )

    assert isinstance(result, NormalizedSource)
    assert result == NormalizedSource(
        title="Saudi Traffic",
        body="First\n\nSecond",
        source_name="News Agency",
        source_url="https://example.com",
        published_at="2026-08-05",
        language="en",
        country="SA",
        author="Author",
        images=("image",),
        attachments=("attachment",),
        category="News",
        tags=("tag",),
    )

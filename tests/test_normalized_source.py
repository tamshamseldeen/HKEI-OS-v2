"""Tests for the normalized source model."""

from dataclasses import FrozenInstanceError

import pytest

from src.intake.normalized_source import NormalizedSource


def test_all_fields_are_stored() -> None:
    """Store every supplied field without changing its value."""
    source = NormalizedSource(
        title="Example title",
        body="Example body",
        source_name="Example source",
        source_url="https://example.com/source",
        published_at="2026-08-05T12:00:00Z",
        language="en",
        country="HK",
        author="Example author",
        images=("https://example.com/image.jpg",),
        attachments=("https://example.com/document.pdf",),
        category="news",
        tags=("example", "source"),
    )

    assert source.title == "Example title"
    assert source.body == "Example body"
    assert source.source_name == "Example source"
    assert source.source_url == "https://example.com/source"
    assert source.published_at == "2026-08-05T12:00:00Z"
    assert source.language == "en"
    assert source.country == "HK"
    assert source.author == "Example author"
    assert source.images == ("https://example.com/image.jpg",)
    assert source.attachments == ("https://example.com/document.pdf",)
    assert source.category == "news"
    assert source.tags == ("example", "source")


def test_normalized_source_is_immutable() -> None:
    """Prevent fields from being reassigned after construction."""
    source = NormalizedSource("Title", "Body", "Source")

    with pytest.raises(FrozenInstanceError):
        source.title = "Changed"  # type: ignore[misc]


def test_tuple_fields_remain_tuples() -> None:
    """Keep all tuple fields as tuples."""
    source = NormalizedSource(
        "Title",
        "Body",
        "Source",
        images=("image",),
        attachments=("attachment",),
        tags=("tag",),
    )

    assert isinstance(source.images, tuple)
    assert isinstance(source.attachments, tuple)
    assert isinstance(source.tags, tuple)


def test_optional_fields_accept_none() -> None:
    """Accept None for every optional field."""
    source = NormalizedSource(
        title="Title",
        body="Body",
        source_name="Source",
        source_url=None,
        published_at=None,
        language=None,
        country=None,
        author=None,
        category=None,
    )

    assert source.source_url is None
    assert source.published_at is None
    assert source.language is None
    assert source.country is None
    assert source.author is None
    assert source.category is None

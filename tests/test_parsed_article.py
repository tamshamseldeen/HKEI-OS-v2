"""Tests for the immutable parsed article model."""

from dataclasses import FrozenInstanceError, fields

import pytest

from src.parsing.parsed_article import ParsedArticle


def make_parsed_article(
    *,
    headings: tuple[str, ...] = ("Details", "Details"),
    paragraphs: tuple[str, ...] = ("First paragraph.", "Second paragraph."),
    bullet_items: tuple[str, ...] = ("Item", "Item"),
    warnings: tuple[str, ...] = ("ARTICLE_TOO_SHORT", "ARTICLE_TOO_SHORT"),
    reason_codes: tuple[str, ...] = ("ARTICLE_MARKDOWN_PARSED",),
) -> ParsedArticle:
    """Create a representative parsed article."""
    return ParsedArticle(
        headline="Article headline",
        body_markdown="First paragraph.\n\nSecond paragraph.",
        full_markdown=(
            "# Article headline\n\nFirst paragraph.\n\nSecond paragraph."
        ),
        headings=headings,
        paragraphs=paragraphs,
        bullet_items=bullet_items,
        table_count=2,
        faq_detected=True,
        timeline_detected=False,
        word_count=7,
        warnings=warnings,
        reason_codes=reason_codes,
    )


def test_parsed_article_stores_all_fields_in_order() -> None:
    """Store all parsed article values in specification order."""
    article = make_parsed_article()

    assert article.headline == "Article headline"
    assert article.body_markdown == "First paragraph.\n\nSecond paragraph."
    assert article.full_markdown.startswith("# Article headline\n\n")
    assert article.headings == ("Details", "Details")
    assert article.paragraphs == ("First paragraph.", "Second paragraph.")
    assert article.bullet_items == ("Item", "Item")
    assert article.table_count == 2
    assert article.faq_detected is True
    assert article.timeline_detected is False
    assert article.word_count == 7
    assert article.warnings == ("ARTICLE_TOO_SHORT", "ARTICLE_TOO_SHORT")
    assert article.reason_codes == ("ARTICLE_MARKDOWN_PARSED",)
    assert tuple(field.name for field in fields(article)) == (
        "headline",
        "body_markdown",
        "full_markdown",
        "headings",
        "paragraphs",
        "bullet_items",
        "table_count",
        "faq_detected",
        "timeline_detected",
        "word_count",
        "warnings",
        "reason_codes",
    )


def test_parsed_article_is_immutable() -> None:
    """Prevent parsed article fields from reassignment."""
    article = make_parsed_article()

    with pytest.raises(FrozenInstanceError):
        article.headline = "Changed"  # type: ignore[misc]


def test_tuple_fields_remain_tuples_and_preserve_duplicates() -> None:
    """Keep supplied tuple objects and their duplicate values unchanged."""
    headings = ("Details", "Details")
    paragraphs = ("Paragraph", "Paragraph")
    bullets = ("Item", "Item")
    warnings = ("WARNING", "WARNING")
    reasons = ("REASON", "REASON")
    article = make_parsed_article(
        headings=headings,
        paragraphs=paragraphs,
        bullet_items=bullets,
        warnings=warnings,
        reason_codes=reasons,
    )

    assert article.headings is headings
    assert article.paragraphs is paragraphs
    assert article.bullet_items is bullets
    assert article.warnings is warnings
    assert article.reason_codes is reasons
    assert all(
        isinstance(value, tuple)
        for value in (
            article.headings,
            article.paragraphs,
            article.bullet_items,
            article.warnings,
            article.reason_codes,
        )
    )


def test_empty_tuples_and_scalar_values_are_accepted() -> None:
    """Accept empty collections while preserving booleans and integers."""
    article = make_parsed_article(
        headings=(),
        paragraphs=(),
        bullet_items=(),
        warnings=(),
        reason_codes=(),
    )

    assert article.headings == ()
    assert article.paragraphs == ()
    assert article.bullet_items == ()
    assert article.warnings == ()
    assert article.reason_codes == ()
    assert article.table_count == 2
    assert article.faq_detected is True
    assert article.timeline_detected is False
    assert article.word_count == 7

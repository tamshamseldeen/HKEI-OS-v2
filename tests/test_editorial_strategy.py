"""Tests for editorial strategy models."""

from dataclasses import FrozenInstanceError, fields

import pytest

from src.strategy.article_depth import ArticleDepth
from src.strategy.article_length import ArticleLength
from src.strategy.editorial_strategy import EditorialStrategy
from src.strategy.writing_mode import WritingMode


def make_strategy() -> EditorialStrategy:
    """Create a populated editorial strategy for testing.

    Returns:
        A strategy containing representative values.
    """
    return EditorialStrategy(
        article_length=ArticleLength.MEDIUM,
        article_depth=ArticleDepth.EXPLAINED,
        writing_mode=WritingMode.SERVICE,
        use_headings=True,
        use_bullets=True,
        use_table=False,
        use_faq=False,
        use_timeline=True,
        use_background=True,
        use_quotes=False,
        use_attribution=True,
        include_missing_information=False,
        include_reader_action=True,
        target_word_count=450,
        reason_codes=("SERVICE_STRATEGY", "READER_ACTION_REQUIRED"),
        warnings=("HIGH_RISK_REVIEW_REQUIRED",),
    )


def test_article_length_values() -> None:
    """Expose every article length with its exact specified value."""
    assert tuple(length.value for length in ArticleLength) == (
        "VERY_SHORT",
        "SHORT",
        "MEDIUM",
        "LONG",
    )


def test_article_depth_values() -> None:
    """Expose every article depth with its exact specified value."""
    assert tuple(depth.value for depth in ArticleDepth) == (
        "UPDATE",
        "STANDARD",
        "EXPLAINED",
        "DETAILED",
    )


def test_writing_mode_values() -> None:
    """Expose every writing mode with its exact specified value."""
    assert tuple(mode.value for mode in WritingMode) == (
        "DIRECT_NEWS",
        "SERVICE",
        "EXPLAINER",
        "FACT_CHECK",
        "HIGH_RISK_CAUTION",
        "RESULT_REPORT",
        "TREND_UPDATE",
        "COMPARISON",
    )


def test_all_fields_are_stored_correctly() -> None:
    """Store every supplied strategy field unchanged."""
    strategy = make_strategy()

    assert strategy.article_length is ArticleLength.MEDIUM
    assert strategy.article_depth is ArticleDepth.EXPLAINED
    assert strategy.writing_mode is WritingMode.SERVICE
    assert strategy.reason_codes == (
        "SERVICE_STRATEGY",
        "READER_ACTION_REQUIRED",
    )
    assert strategy.warnings == ("HIGH_RISK_REVIEW_REQUIRED",)


def test_strategy_is_immutable() -> None:
    """Prevent editorial strategy fields from reassignment."""
    strategy = make_strategy()

    with pytest.raises(FrozenInstanceError):
        strategy.article_length = ArticleLength.LONG  # type: ignore[misc]


def test_tuple_fields_remain_tuples() -> None:
    """Preserve tuple types for every collection field."""
    strategy = make_strategy()

    assert isinstance(strategy.reason_codes, tuple)
    assert isinstance(strategy.warnings, tuple)


def test_empty_tuples_are_accepted() -> None:
    """Accept empty tuples for both collection fields."""
    strategy = make_strategy()
    empty_strategy = EditorialStrategy(
        article_length=strategy.article_length,
        article_depth=strategy.article_depth,
        writing_mode=strategy.writing_mode,
        use_headings=strategy.use_headings,
        use_bullets=strategy.use_bullets,
        use_table=strategy.use_table,
        use_faq=strategy.use_faq,
        use_timeline=strategy.use_timeline,
        use_background=strategy.use_background,
        use_quotes=strategy.use_quotes,
        use_attribution=strategy.use_attribution,
        include_missing_information=strategy.include_missing_information,
        include_reader_action=strategy.include_reader_action,
        target_word_count=strategy.target_word_count,
        reason_codes=(),
        warnings=(),
    )

    assert empty_strategy.reason_codes == ()
    assert empty_strategy.warnings == ()


def test_duplicate_values_are_preserved() -> None:
    """Preserve duplicate tuple values without deduplication."""
    duplicates = ("REPEATED", "REPEATED")
    strategy = make_strategy()
    duplicate_strategy = EditorialStrategy(
        article_length=strategy.article_length,
        article_depth=strategy.article_depth,
        writing_mode=strategy.writing_mode,
        use_headings=strategy.use_headings,
        use_bullets=strategy.use_bullets,
        use_table=strategy.use_table,
        use_faq=strategy.use_faq,
        use_timeline=strategy.use_timeline,
        use_background=strategy.use_background,
        use_quotes=strategy.use_quotes,
        use_attribution=strategy.use_attribution,
        include_missing_information=strategy.include_missing_information,
        include_reader_action=strategy.include_reader_action,
        target_word_count=strategy.target_word_count,
        reason_codes=duplicates,
        warnings=duplicates,
    )

    assert duplicate_strategy.reason_codes == duplicates
    assert duplicate_strategy.warnings == duplicates


def test_boolean_fields_preserve_values() -> None:
    """Preserve every supplied boolean control value."""
    strategy = make_strategy()

    assert strategy.use_headings is True
    assert strategy.use_bullets is True
    assert strategy.use_table is False
    assert strategy.use_faq is False
    assert strategy.use_timeline is True
    assert strategy.use_background is True
    assert strategy.use_quotes is False
    assert strategy.use_attribution is True
    assert strategy.include_missing_information is False
    assert strategy.include_reader_action is True


def test_target_word_count_preserves_integer_value() -> None:
    """Preserve the supplied integer target word count."""
    strategy = make_strategy()

    assert strategy.target_word_count == 450
    assert isinstance(strategy.target_word_count, int)


def test_field_order_matches_specification() -> None:
    """Declare fields in the order required by the specification."""
    assert tuple(field.name for field in fields(EditorialStrategy)) == (
        "article_length",
        "article_depth",
        "writing_mode",
        "use_headings",
        "use_bullets",
        "use_table",
        "use_faq",
        "use_timeline",
        "use_background",
        "use_quotes",
        "use_attribution",
        "include_missing_information",
        "include_reader_action",
        "target_word_count",
        "reason_codes",
        "warnings",
    )

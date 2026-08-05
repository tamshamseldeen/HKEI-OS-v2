"""Tests for content type classification models."""

from dataclasses import FrozenInstanceError, fields

import pytest

from src.classification.classification_confidence import (
    ClassificationConfidence,
)
from src.classification.content_type import ContentType
from src.classification.content_type_classification import (
    ContentTypeClassification,
)


def make_classification() -> ContentTypeClassification:
    """Create a populated content type classification for testing.

    Returns:
        A classification containing representative values.
    """
    return ContentTypeClassification(
        content_type=ContentType.PUBLIC_SERVICE_NEWS,
        confidence=ClassificationConfidence.HIGH,
        reason_codes=("PUBLIC_SERVICE_SIGNAL",),
        supporting_signals=("application deadline", "consumer warning"),
        warnings=("GOVERNMENT_SOURCE_RECOMMENDED",),
    )


def test_content_type_values() -> None:
    """Expose every content type with its exact specified value."""
    assert tuple(content_type.value for content_type in ContentType) == (
        "BREAKING_NEWS",
        "STANDARD_NEWS",
        "NEWS_REWRITE",
        "PUBLIC_SERVICE_NEWS",
        "GOVERNMENT_SERVICE_CONTENT",
        "EXPLAINER",
        "FACT_CHECK",
        "HEALTH_CONTENT",
        "LEGAL_FINANCIAL_HIGH_RISK_CONTENT",
        "SPORTS_NEWS",
        "TECHNOLOGY_NEWS",
        "ECONOMY_NEWS",
        "TRENDING_SOCIAL_CLAIM",
    )


def test_classification_confidence_values() -> None:
    """Expose every confidence level with its exact specified value."""
    assert tuple(confidence.value for confidence in ClassificationConfidence) == (
        "HIGH",
        "MEDIUM",
        "LOW",
    )


def test_all_fields_are_stored_correctly() -> None:
    """Store every supplied classification field unchanged."""
    classification = make_classification()

    assert classification.content_type is ContentType.PUBLIC_SERVICE_NEWS
    assert classification.confidence is ClassificationConfidence.HIGH
    assert classification.reason_codes == ("PUBLIC_SERVICE_SIGNAL",)
    assert classification.supporting_signals == (
        "application deadline",
        "consumer warning",
    )
    assert classification.warnings == ("GOVERNMENT_SOURCE_RECOMMENDED",)


def test_classification_is_immutable() -> None:
    """Prevent classification fields from being reassigned."""
    classification = make_classification()

    with pytest.raises(FrozenInstanceError):
        classification.confidence = (  # type: ignore[misc]
            ClassificationConfidence.LOW
        )


def test_tuple_fields_remain_tuples() -> None:
    """Preserve tuple types for every collection field."""
    classification = make_classification()

    assert isinstance(classification.reason_codes, tuple)
    assert isinstance(classification.supporting_signals, tuple)
    assert isinstance(classification.warnings, tuple)


def test_empty_tuples_are_accepted() -> None:
    """Accept empty tuples for every collection field."""
    classification = ContentTypeClassification(
        content_type=ContentType.STANDARD_NEWS,
        confidence=ClassificationConfidence.LOW,
        reason_codes=(),
        supporting_signals=(),
        warnings=(),
    )

    assert classification.reason_codes == ()
    assert classification.supporting_signals == ()
    assert classification.warnings == ()


def test_duplicate_values_are_preserved() -> None:
    """Preserve duplicate collection values without deduplication."""
    duplicates = ("REPEATED", "REPEATED")
    classification = ContentTypeClassification(
        content_type=ContentType.STANDARD_NEWS,
        confidence=ClassificationConfidence.MEDIUM,
        reason_codes=duplicates,
        supporting_signals=duplicates,
        warnings=duplicates,
    )

    assert classification.reason_codes == duplicates
    assert classification.supporting_signals == duplicates
    assert classification.warnings == duplicates


def test_field_order_matches_specification() -> None:
    """Declare fields in the order required by the specification."""
    assert tuple(field.name for field in fields(ContentTypeClassification)) == (
        "content_type",
        "confidence",
        "reason_codes",
        "supporting_signals",
        "warnings",
    )

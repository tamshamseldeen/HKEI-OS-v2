"""Tests for immutable topic classification models."""

from dataclasses import FrozenInstanceError, fields
from typing import get_type_hints

import pytest

from src.topic.topic import Topic
from src.topic.topic_classification import TopicClassification
from src.topic.topic_confidence import TopicConfidence


def test_all_topic_values_exist_in_specification_order() -> None:
    """Expose exactly the supported MVP topic values in specification order."""
    assert tuple(topic.value for topic in Topic) == (
        "POLITICS",
        "ECONOMY",
        "BUSINESS",
        "TECHNOLOGY",
        "SPORTS",
        "GOVERNMENT",
        "WEATHER",
        "HEALTH",
        "CULTURE",
        "SCIENCE",
        "EDUCATION",
        "CRIME",
        "ENTERTAINMENT",
        "WORLD",
        "GENERAL",
    )


def test_all_topic_confidence_values_exist() -> None:
    """Expose exactly the three supported topic confidence values."""
    assert tuple(confidence.value for confidence in TopicConfidence) == (
        "HIGH",
        "MEDIUM",
        "LOW",
    )


def test_classification_stores_all_fields_and_preserves_tuples() -> None:
    """Store supplied enum and tuple fields unchanged, including duplicates."""
    reasons = ("CATEGORY_TOPIC_MATCH", "CATEGORY_TOPIC_MATCH")
    signals = ("SOURCE_CATEGORY_TECHNOLOGY", "TITLE_TECHNOLOGY_SIGNAL")
    warnings = ("TOPIC_MIGRATION_COMPATIBILITY_WARNING",) * 2

    classification = TopicClassification(
        topic=Topic.TECHNOLOGY,
        confidence=TopicConfidence.HIGH,
        reason_codes=reasons,
        supporting_signals=signals,
        warnings=warnings,
    )

    assert classification.topic is Topic.TECHNOLOGY
    assert classification.confidence is TopicConfidence.HIGH
    assert classification.reason_codes is reasons
    assert classification.supporting_signals is signals
    assert classification.warnings is warnings
    assert all(
        isinstance(value, tuple)
        for value in (
            classification.reason_codes,
            classification.supporting_signals,
            classification.warnings,
        )
    )


def test_classification_accepts_empty_tuples() -> None:
    """Accept empty required tuple collections without optional defaults."""
    classification = TopicClassification(
        topic=Topic.GENERAL,
        confidence=TopicConfidence.LOW,
        reason_codes=(),
        supporting_signals=(),
        warnings=(),
    )

    assert classification.reason_codes == ()
    assert classification.supporting_signals == ()
    assert classification.warnings == ()


def test_classification_is_immutable() -> None:
    """Prevent reassignment of frozen classification fields."""
    classification = TopicClassification(
        Topic.SPORTS,
        TopicConfidence.MEDIUM,
        (),
        (),
        (),
    )

    with pytest.raises(FrozenInstanceError):
        classification.topic = Topic.GENERAL  # type: ignore[misc]


def test_field_order_and_types_match_specification() -> None:
    """Define only the five required non-optional fields in exact order."""
    assert tuple(field.name for field in fields(TopicClassification)) == (
        "topic",
        "confidence",
        "reason_codes",
        "supporting_signals",
        "warnings",
    )
    assert get_type_hints(TopicClassification) == {
        "topic": Topic,
        "confidence": TopicConfidence,
        "reason_codes": tuple[str, ...],
        "supporting_signals": tuple[str, ...],
        "warnings": tuple[str, ...],
    }
    assert all(
        field.default is field.default_factory
        for field in fields(TopicClassification)
    )

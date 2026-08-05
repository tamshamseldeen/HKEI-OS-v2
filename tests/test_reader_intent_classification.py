"""Tests for reader intent classification models."""

from dataclasses import FrozenInstanceError, fields

import pytest

from src.intent.reader_intent import ReaderIntent
from src.intent.reader_intent_classification import ReaderIntentClassification
from src.intent.reader_intent_confidence import ReaderIntentConfidence


def make_classification() -> ReaderIntentClassification:
    """Create a populated reader intent classification for testing.

    Returns:
        A classification containing representative values.
    """
    return ReaderIntentClassification(
        reader_intent=ReaderIntent.VERIFY_REQUIREMENTS,
        confidence=ReaderIntentConfidence.HIGH,
        reason_codes=("REQUIREMENTS_SIGNAL",),
        supporting_signals=("fees", "documents"),
        warnings=("REQUIREMENTS_SOURCE_RECOMMENDED",),
    )


def test_reader_intent_values() -> None:
    """Expose every reader intent with its exact specified value."""
    assert tuple(intent.value for intent in ReaderIntent) == (
        "GET_UPDATE",
        "UNDERSTAND_EVENT",
        "KNOW_ACTION",
        "CHECK_CLAIM",
        "COMPARE_OPTIONS",
        "FOLLOW_DEVELOPMENT",
        "FIND_RESULT",
        "UNDERSTAND_IMPACT",
        "GET_GUIDANCE",
        "VERIFY_REQUIREMENTS",
    )


def test_reader_intent_confidence_values() -> None:
    """Expose every confidence level with its exact specified value."""
    assert tuple(confidence.value for confidence in ReaderIntentConfidence) == (
        "HIGH",
        "MEDIUM",
        "LOW",
    )


def test_all_fields_are_stored_correctly() -> None:
    """Store every supplied reader intent field unchanged."""
    classification = make_classification()

    assert classification.reader_intent is ReaderIntent.VERIFY_REQUIREMENTS
    assert classification.confidence is ReaderIntentConfidence.HIGH
    assert classification.reason_codes == ("REQUIREMENTS_SIGNAL",)
    assert classification.supporting_signals == ("fees", "documents")
    assert classification.warnings == ("REQUIREMENTS_SOURCE_RECOMMENDED",)


def test_classification_is_immutable() -> None:
    """Prevent reader intent classification fields from reassignment."""
    classification = make_classification()

    with pytest.raises(FrozenInstanceError):
        classification.confidence = (  # type: ignore[misc]
            ReaderIntentConfidence.LOW
        )


def test_tuple_fields_remain_tuples() -> None:
    """Preserve tuple types for every collection field."""
    classification = make_classification()

    assert isinstance(classification.reason_codes, tuple)
    assert isinstance(classification.supporting_signals, tuple)
    assert isinstance(classification.warnings, tuple)


def test_empty_tuples_are_accepted() -> None:
    """Accept empty tuples for every collection field."""
    classification = ReaderIntentClassification(
        reader_intent=ReaderIntent.GET_UPDATE,
        confidence=ReaderIntentConfidence.LOW,
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
    classification = ReaderIntentClassification(
        reader_intent=ReaderIntent.GET_UPDATE,
        confidence=ReaderIntentConfidence.MEDIUM,
        reason_codes=duplicates,
        supporting_signals=duplicates,
        warnings=duplicates,
    )

    assert classification.reason_codes == duplicates
    assert classification.supporting_signals == duplicates
    assert classification.warnings == duplicates


def test_field_order_matches_specification() -> None:
    """Declare fields in the order required by the specification."""
    assert tuple(field.name for field in fields(ReaderIntentClassification)) == (
        "reader_intent",
        "confidence",
        "reason_codes",
        "supporting_signals",
        "warnings",
    )

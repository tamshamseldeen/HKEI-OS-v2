"""Tests for independent editorial format classification models."""

from dataclasses import FrozenInstanceError, fields
from typing import get_type_hints

import pytest

from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.formatting.editorial_format_confidence import (
    EditorialFormatConfidence,
)


def make_classification() -> EditorialFormatClassification:
    """Create a populated editorial format classification."""
    return EditorialFormatClassification(
        editorial_format=EditorialFormat.SERVICE,
        confidence=EditorialFormatConfidence.HIGH,
        reason_codes=("SERVICE_PRACTICAL_ACTION_SIGNAL",),
        supporting_signals=("traffic fine", "required action"),
        warnings=("FORMAT_MIGRATION_COMPATIBILITY_WARNING",),
    )


def test_editorial_format_values_are_exact() -> None:
    """Expose every editorial format in exact specification order."""
    assert tuple(value.value for value in EditorialFormat) == (
        "BREAKING",
        "STANDARD_NEWS",
        "SERVICE",
        "GUIDE",
        "EXPLAINER",
        "FEATURE",
        "FACT_CHECK",
        "ANALYSIS",
        "INTERVIEW",
        "PROFILE",
        "RESULT_REPORT",
        "TREND_UPDATE",
    )


def test_editorial_format_confidence_values_are_exact() -> None:
    """Expose every confidence level in exact specification order."""
    assert tuple(value.value for value in EditorialFormatConfidence) == (
        "HIGH",
        "MEDIUM",
        "LOW",
    )


def test_all_fields_are_stored_correctly() -> None:
    """Store every supplied classification field unchanged."""
    classification = make_classification()

    assert classification.editorial_format is EditorialFormat.SERVICE
    assert classification.confidence is EditorialFormatConfidence.HIGH
    assert classification.reason_codes == (
        "SERVICE_PRACTICAL_ACTION_SIGNAL",
    )
    assert classification.supporting_signals == (
        "traffic fine",
        "required action",
    )
    assert classification.warnings == (
        "FORMAT_MIGRATION_COMPATIBILITY_WARNING",
    )


def test_classification_is_immutable() -> None:
    """Prevent editorial format classification fields from reassignment."""
    classification = make_classification()

    with pytest.raises(FrozenInstanceError):
        classification.confidence = (  # type: ignore[misc]
            EditorialFormatConfidence.LOW
        )


def test_tuple_fields_remain_tuples() -> None:
    """Preserve tuple types for every collection field."""
    classification = make_classification()

    assert isinstance(classification.reason_codes, tuple)
    assert isinstance(classification.supporting_signals, tuple)
    assert isinstance(classification.warnings, tuple)


def test_empty_tuples_are_accepted() -> None:
    """Accept empty tuples for every collection field."""
    classification = EditorialFormatClassification(
        editorial_format=EditorialFormat.STANDARD_NEWS,
        confidence=EditorialFormatConfidence.LOW,
        reason_codes=(),
        supporting_signals=(),
        warnings=(),
    )

    assert classification.reason_codes == ()
    assert classification.supporting_signals == ()
    assert classification.warnings == ()


def test_duplicate_values_are_preserved() -> None:
    """Preserve duplicate tuple values without deduplication."""
    duplicates = ("REPEATED", "REPEATED")
    classification = EditorialFormatClassification(
        editorial_format=EditorialFormat.GUIDE,
        confidence=EditorialFormatConfidence.MEDIUM,
        reason_codes=duplicates,
        supporting_signals=duplicates,
        warnings=duplicates,
    )

    assert classification.reason_codes is duplicates
    assert classification.supporting_signals is duplicates
    assert classification.warnings is duplicates


def test_no_boolean_or_optional_behavior_is_introduced() -> None:
    """Keep every field required and free of boolean or optional types."""
    hints = get_type_hints(EditorialFormatClassification)

    assert bool not in hints.values()
    assert all("None" not in str(annotation) for annotation in hints.values())
    with pytest.raises(TypeError):
        EditorialFormatClassification()  # type: ignore[call-arg]


def test_field_order_matches_specification() -> None:
    """Declare fields in the exact required order."""
    assert tuple(
        field.name for field in fields(EditorialFormatClassification)
    ) == (
        "editorial_format",
        "confidence",
        "reason_codes",
        "supporting_signals",
        "warnings",
    )

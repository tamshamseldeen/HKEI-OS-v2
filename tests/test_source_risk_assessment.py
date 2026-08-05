"""Tests for source risk assessment models."""

from dataclasses import FrozenInstanceError

import pytest

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.source_status import SourceStatus
from src.assessment.verification_status import VerificationStatus


def make_assessment() -> SourceRiskAssessment:
    """Create a populated source risk assessment for testing.

    Returns:
        A source risk assessment containing representative values.
    """
    return SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=VerificationStatus.SOURCE_PROVIDED,
        risk_level=RiskLevel.HIGH,
        risk_topics=("Public safety and emergency instructions",),
        warnings=("HIGH_RISK_CONTENT", "HUMAN_REVIEW_REQUIRED"),
        requires_official_source=True,
        requires_human_review=True,
        generation_allowed=False,
        reason_codes=("HIGH_RISK_TOPIC_DETECTED",),
    )


def test_source_risk_assessment_is_immutable() -> None:
    """Prevent assessment fields from being reassigned."""
    assessment = make_assessment()

    with pytest.raises(FrozenInstanceError):
        assessment.risk_level = RiskLevel.LOW  # type: ignore[misc]


def test_enum_values() -> None:
    """Expose every enum member with its exact specified value."""
    assert tuple(status.value for status in SourceStatus) == (
        "IDENTIFIED",
        "PARTIALLY_IDENTIFIED",
        "UNIDENTIFIED",
    )
    assert tuple(status.value for status in VerificationStatus) == (
        "UNVERIFIED",
        "SOURCE_PROVIDED",
        "OFFICIAL_SOURCE_PROVIDED",
        "MULTIPLE_SOURCES_PROVIDED",
        "VERIFIED_EXTERNALLY",
    )
    assert tuple(level.value for level in RiskLevel) == (
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    )


def test_tuple_fields_are_preserved() -> None:
    """Preserve tuple values and tuple types without conversion."""
    assessment = make_assessment()

    assert assessment.risk_topics == (
        "Public safety and emergency instructions",
    )
    assert assessment.warnings == (
        "HIGH_RISK_CONTENT",
        "HUMAN_REVIEW_REQUIRED",
    )
    assert assessment.reason_codes == ("HIGH_RISK_TOPIC_DETECTED",)
    assert isinstance(assessment.risk_topics, tuple)
    assert isinstance(assessment.warnings, tuple)
    assert isinstance(assessment.reason_codes, tuple)


def test_optional_collections_can_be_empty() -> None:
    """Allow zero risk topics, warnings, and reason codes."""
    assessment = SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=VerificationStatus.SOURCE_PROVIDED,
        risk_level=RiskLevel.LOW,
        risk_topics=(),
        warnings=(),
        requires_official_source=False,
        requires_human_review=False,
        generation_allowed=True,
        reason_codes=(),
    )

    assert assessment.risk_topics == ()
    assert assessment.warnings == ()
    assert assessment.reason_codes == ()

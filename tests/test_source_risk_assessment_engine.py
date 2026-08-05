"""Tests for deterministic source risk assessment."""

import pytest

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.source_risk_assessment_engine import (
    SourceRiskAssessmentEngine,
)
from src.assessment.source_status import SourceStatus
from src.assessment.verification_status import VerificationStatus
from src.intake.normalized_source import NormalizedSource


@pytest.fixture
def engine() -> SourceRiskAssessmentEngine:
    """Provide a deterministic source assessment engine."""
    return SourceRiskAssessmentEngine()


@pytest.mark.parametrize(
    ("source_name", "source_url", "expected_status", "expected_verification", "warnings"),
    (
        (
            "Source",
            "https://example.com",
            SourceStatus.IDENTIFIED,
            VerificationStatus.SOURCE_PROVIDED,
            (),
        ),
        (
            "Source",
            None,
            SourceStatus.PARTIALLY_IDENTIFIED,
            VerificationStatus.UNVERIFIED,
            ("SOURCE_URL_MISSING", "CONTENT_UNVERIFIED"),
        ),
        (
            "",
            "https://example.com",
            SourceStatus.UNIDENTIFIED,
            VerificationStatus.SOURCE_PROVIDED,
            ("SOURCE_UNIDENTIFIED",),
        ),
        (
            "",
            None,
            SourceStatus.UNIDENTIFIED,
            VerificationStatus.UNVERIFIED,
            (
                "SOURCE_URL_MISSING",
                "SOURCE_UNIDENTIFIED",
                "CONTENT_UNVERIFIED",
            ),
        ),
    ),
)
def test_source_and_verification_combinations(
    engine: SourceRiskAssessmentEngine,
    source_name: str,
    source_url: str | None,
    expected_status: SourceStatus,
    expected_verification: VerificationStatus,
    warnings: tuple[str, ...],
) -> None:
    """Assess every source name and URL availability combination."""
    result = engine.assess(
        NormalizedSource(
            title="Title",
            body="Body",
            source_name=source_name,
            source_url=source_url,
        )
    )

    assert result.source_status is expected_status
    assert result.verification_status is expected_verification
    assert result.warnings == warnings


@pytest.mark.parametrize(
    ("title", "body", "generation_allowed"),
    (
        ("Title", "Body", True),
        ("", "Body", False),
        ("Title", "", False),
        ("", "", False),
    ),
)
def test_generation_combinations(
    engine: SourceRiskAssessmentEngine,
    title: str,
    body: str,
    generation_allowed: bool,
) -> None:
    """Allow generation only when both title and body are non-empty."""
    result = engine.assess(
        NormalizedSource(
            title=title,
            body=body,
            source_name="Source",
            source_url="https://example.com",
        )
    )

    assert result.generation_allowed is generation_allowed


def test_assessment_uses_low_risk_defaults(
    engine: SourceRiskAssessmentEngine,
) -> None:
    """Return the fixed MVP risk values without topic analysis."""
    result = engine.assess(
        NormalizedSource(
            title="Title",
            body="Body",
            source_name="Source",
            source_url="https://example.com",
        )
    )

    assert isinstance(result, SourceRiskAssessment)
    assert result.risk_level is RiskLevel.LOW
    assert result.risk_topics == ()
    assert result.requires_official_source is False
    assert result.requires_human_review is False


def test_complete_source_uses_source_ok_reason(
    engine: SourceRiskAssessmentEngine,
) -> None:
    """Mark a usable identified source as complete."""
    result = engine.assess(
        NormalizedSource(
            title="Title",
            body="Body",
            source_name="Source",
            source_url="https://example.com",
        )
    )

    assert result.reason_codes == ("SOURCE_OK",)


@pytest.mark.parametrize(
    "source",
    (
        NormalizedSource("Title", "Body", "Source"),
        NormalizedSource("Title", "Body", "", "https://example.com"),
        NormalizedSource("", "Body", "Source", "https://example.com"),
        NormalizedSource("Title", "", "Source", "https://example.com"),
    ),
)
def test_incomplete_sources_use_source_incomplete_reason(
    engine: SourceRiskAssessmentEngine,
    source: NormalizedSource,
) -> None:
    """Mark incomplete attribution or content with the incomplete reason."""
    result = engine.assess(source)

    assert result.reason_codes == ("SOURCE_INCOMPLETE",)

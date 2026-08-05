"""Tests for deterministic source risk assessment."""

from unittest.mock import Mock

import pytest

from src.assessment.risk_level import RiskLevel
from src.assessment.risk_rule import RiskRule
from src.assessment.risk_rule_engine import RiskRuleEngine
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


def make_rule(
    code: str,
    *,
    topics: tuple[str, ...] = (),
    risk_level: RiskLevel = RiskLevel.HIGH,
    warnings: tuple[str, ...] = (),
    requires_official_source: bool = False,
    requires_human_review: bool = False,
) -> RiskRule:
    """Create a matching custom risk rule for assessment tests.

    Args:
        code: Stable rule code.
        topics: Topics assigned by the rule.
        risk_level: Risk level assigned by the rule.
        warnings: Warnings assigned by the rule.
        requires_official_source: Whether the rule requires an official source.
        requires_human_review: Whether the rule requires human review.

    Returns:
        A custom rule that matches the word "match".
    """
    return RiskRule(
        code=code,
        topics=topics,
        keywords=("match",),
        risk_level=risk_level,
        warnings=warnings,
        requires_official_source=requires_official_source,
        requires_human_review=requires_human_review,
    )


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


def test_one_high_rule_produces_high_risk() -> None:
    """Use HIGH when one matching rule has HIGH risk."""
    rule = make_rule("HIGH_RULE")
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((rule,)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.risk_level is RiskLevel.HIGH


def test_multiple_rules_aggregate_topics_in_rule_order() -> None:
    """Aggregate topics while preserving rule and topic order."""
    first = make_rule("FIRST", topics=("medical", "shared"))
    second = make_rule("SECOND", topics=("legal", "financial"))
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((first, second)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.risk_topics == ("medical", "shared", "legal", "financial")


def test_duplicate_topics_are_removed() -> None:
    """Keep only the first occurrence of each topic."""
    first = make_rule("FIRST", topics=("shared", "medical"))
    second = make_rule("SECOND", topics=("shared", "legal"))
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((first, second)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.risk_topics == ("shared", "medical", "legal")


def test_rule_warnings_follow_source_warnings() -> None:
    """Append rule warnings after ordered source warnings."""
    rule = make_rule("RULE", warnings=("HIGH_RISK_CONTENT", "RULE_WARNING"))
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((rule,)))

    result = engine.assess(NormalizedSource("Title", "match", "Source"))

    assert result.warnings == (
        "SOURCE_URL_MISSING",
        "CONTENT_UNVERIFIED",
        "HIGH_RISK_CONTENT",
        "RULE_WARNING",
    )


def test_duplicate_warnings_are_removed() -> None:
    """Keep only the first occurrence of each warning."""
    first = make_rule("FIRST", warnings=("SHARED_WARNING", "FIRST_WARNING"))
    second = make_rule("SECOND", warnings=("SHARED_WARNING", "SECOND_WARNING"))
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((first, second)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.warnings == (
        "SHARED_WARNING",
        "FIRST_WARNING",
        "SECOND_WARNING",
    )


def test_rule_order_is_preserved_in_reason_codes() -> None:
    """Append matched rule codes in declaration order."""
    first = make_rule("FIRST")
    second = make_rule("SECOND")
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((first, second)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.reason_codes == ("SOURCE_OK", "FIRST", "SECOND")


def test_requires_official_source_is_aggregated() -> None:
    """Require an official source when any matching rule requires one."""
    optional = make_rule("OPTIONAL")
    required = make_rule("REQUIRED", requires_official_source=True)
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((optional, required)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.requires_official_source is True


def test_high_risk_enables_human_review() -> None:
    """Require human review for HIGH risk even when the rule flag is false."""
    rule = make_rule("HIGH_RULE", requires_human_review=False)
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((rule,)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.requires_human_review is True


def test_high_risk_allows_generation_for_valid_content() -> None:
    """Allow valid HIGH-risk content to continue to generation."""
    rule = make_rule("HIGH_RULE")
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((rule,)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.generation_allowed is True


def test_critical_custom_rule_prevents_generation() -> None:
    """Stop generation when the highest matched risk is CRITICAL."""
    high = make_rule("HIGH_RULE")
    critical = make_rule("CRITICAL_RULE", risk_level=RiskLevel.CRITICAL)
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((high, critical)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.risk_level is RiskLevel.CRITICAL
    assert result.generation_allowed is False
    assert result.requires_human_review is True


def test_reason_codes_remove_duplicate_rule_codes() -> None:
    """Append each distinct matching rule code only once."""
    first = make_rule("SHARED")
    second = make_rule("SHARED", topics=("other",))
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((first, second)))

    result = engine.assess(
        NormalizedSource("Title", "match", "Source", "https://example.com")
    )

    assert result.reason_codes == ("SOURCE_OK", "SHARED")


def test_risk_match_does_not_upgrade_verification() -> None:
    """Keep verification independent from matched risk rules."""
    rule = make_rule("HIGH_RULE")
    engine = SourceRiskAssessmentEngine(RiskRuleEngine((rule,)))

    result = engine.assess(NormalizedSource("Title", "match", "Source"))

    assert result.verification_status is VerificationStatus.UNVERIFIED


def test_risk_rule_engine_is_called_exactly_once() -> None:
    """Evaluate risk rules exactly once for each assessment."""
    risk_rule_engine = Mock(spec=RiskRuleEngine)
    risk_rule_engine.evaluate.return_value = ()
    engine = SourceRiskAssessmentEngine(risk_rule_engine)
    source = NormalizedSource("Title", "Body", "Source")

    engine.assess(source)

    risk_rule_engine.evaluate.assert_called_once_with(source)


def test_injected_risk_rule_engine_is_used() -> None:
    """Use the supplied rule engine and its returned matches."""
    rule = make_rule("INJECTED", risk_level=RiskLevel.MEDIUM)
    risk_rule_engine = Mock(spec=RiskRuleEngine)
    risk_rule_engine.evaluate.return_value = (rule,)
    engine = SourceRiskAssessmentEngine(risk_rule_engine)

    result = engine.assess(
        NormalizedSource("Title", "Body", "Source", "https://example.com")
    )

    assert engine.risk_rule_engine is risk_rule_engine
    assert result.risk_level is RiskLevel.MEDIUM
    assert result.reason_codes == ("SOURCE_OK", "INJECTED")


def test_existing_source_assessment_behavior_remains_compatible() -> None:
    """Retain source status, warning, and incomplete-content behavior."""
    engine = SourceRiskAssessmentEngine(RiskRuleEngine(()))

    result = engine.assess(NormalizedSource("", "Body", ""))

    assert result.source_status is SourceStatus.UNIDENTIFIED
    assert result.verification_status is VerificationStatus.UNVERIFIED
    assert result.risk_level is RiskLevel.LOW
    assert result.warnings == (
        "SOURCE_URL_MISSING",
        "SOURCE_UNIDENTIFIED",
        "CONTENT_UNVERIFIED",
    )
    assert result.generation_allowed is False
    assert result.reason_codes == ("SOURCE_INCOMPLETE",)


@pytest.mark.parametrize("phrase", ("مخالفة مرورية", "غرامة مرورية"))
def test_public_service_penalties_produce_medium_risk(
    engine: SourceRiskAssessmentEngine,
    phrase: str,
) -> None:
    """Assess specified public-service penalty phrases as MEDIUM risk."""
    result = engine.assess(
        NormalizedSource(
            "تنبيه مروري",
            phrase,
            "Official Source",
            "https://example.com",
        )
    )

    assert result.risk_level is RiskLevel.MEDIUM
    assert result.risk_topics == ("public_service_penalty",)
    assert result.warnings == (
        "OFFICIAL_SOURCE_REQUIRED",
        "TIME_SENSITIVE_INFORMATION",
    )
    assert result.requires_official_source is True
    assert result.requires_human_review is False
    assert result.reason_codes == (
        "SOURCE_OK",
        "PUBLIC_SERVICE_PENALTY_MEDIUM_RISK",
    )


def test_legal_high_risk_wins_over_public_service_medium(
    engine: SourceRiskAssessmentEngine,
) -> None:
    """Select HIGH when legal and public-service penalty rules both match."""
    result = engine.assess(
        NormalizedSource(
            "حكم قضائي",
            "فرضت المحكمة غرامة مرورية في الدعوى",
            "Official Source",
            "https://example.com",
        )
    )

    assert result.risk_level is RiskLevel.HIGH
    assert result.risk_topics == ("legal", "public_service_penalty")
    assert result.reason_codes == (
        "SOURCE_OK",
        "LEGAL_HIGH_RISK",
        "PUBLIC_SERVICE_PENALTY_MEDIUM_RISK",
    )
    assert result.requires_human_review is True

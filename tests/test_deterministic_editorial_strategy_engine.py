"""Tests for deterministic editorial strategy selection."""

from dataclasses import replace

import pytest

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.source_status import SourceStatus
from src.assessment.verification_status import VerificationStatus
from src.classification.classification_confidence import (
    ClassificationConfidence,
)
from src.classification.content_type import ContentType
from src.classification.content_type_classification import (
    ContentTypeClassification,
)
from src.facts.extracted_facts import ExtractedFacts
from src.intent.reader_intent import ReaderIntent
from src.intent.reader_intent_classification import ReaderIntentClassification
from src.intent.reader_intent_confidence import ReaderIntentConfidence
from src.intake.normalized_source import NormalizedSource
from src.strategy.article_depth import ArticleDepth
from src.strategy.article_length import ArticleLength
from src.strategy.deterministic_editorial_strategy_engine import (
    DeterministicEditorialStrategyEngine,
)
from src.strategy.editorial_strategy import EditorialStrategy
from src.strategy.writing_mode import WritingMode


def words(count: int) -> str:
    """Create source text with a deterministic word count."""
    return " ".join(f"word{index}" for index in range(count))


def make_source(word_count: int = 80) -> NormalizedSource:
    """Create normalized source material for strategy tests."""
    return NormalizedSource("title", words(word_count - 1), "News Agency")


def make_assessment(
    risk_level: RiskLevel = RiskLevel.LOW,
) -> SourceRiskAssessment:
    """Create a source assessment for strategy tests."""
    return SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=VerificationStatus.SOURCE_PROVIDED,
        risk_level=risk_level,
        risk_topics=(),
        warnings=(),
        requires_official_source=False,
        requires_human_review=False,
        generation_allowed=True,
        reason_codes=("SOURCE_OK",),
    )


def make_facts(
    *,
    fact_count: int = 3,
    claims: tuple[str, ...] = (),
    quotes: tuple[str, ...] = (),
    dates: tuple[str, ...] = (),
    numbers: tuple[str, ...] = (),
    currencies: tuple[str, ...] = (),
    unknown_information: tuple[str, ...] = (),
    attributions: tuple[str, ...] = (),
) -> ExtractedFacts:
    """Create extracted facts with a requested depth count."""
    allocated = (
        len(claims)
        + len(quotes)
        + len(dates)
        + len(numbers)
        + len(currencies)
    )
    core_count = max(fact_count - allocated, 0)
    return ExtractedFacts(
        core_facts=tuple(f"fact{index}" for index in range(core_count)),
        claims=claims,
        quotes=quotes,
        named_people=(),
        organizations=(),
        government_entities=(),
        locations=(),
        countries=(),
        dates=dates,
        times=(),
        numbers=numbers,
        percentages=(),
        currencies=currencies,
        laws_and_regulations=(),
        products=(),
        events=(),
        unknown_information=unknown_information,
        attributions=attributions,
    )


def make_content(content_type: ContentType) -> ContentTypeClassification:
    """Create a content classification for strategy tests."""
    return ContentTypeClassification(
        content_type,
        ClassificationConfidence.HIGH,
        (),
        (),
        (),
    )


def make_intent(intent: ReaderIntent) -> ReaderIntentClassification:
    """Create a reader intent classification for strategy tests."""
    return ReaderIntentClassification(
        intent,
        ReaderIntentConfidence.HIGH,
        (),
        (),
        (),
    )


def decide(
    *,
    source: NormalizedSource | None = None,
    assessment: SourceRiskAssessment | None = None,
    facts: ExtractedFacts | None = None,
    content_type: ContentType = ContentType.STANDARD_NEWS,
    intent: ReaderIntent = ReaderIntent.GET_UPDATE,
    user_instruction: str | None = None,
) -> EditorialStrategy:
    """Select a strategy from representative analysis inputs."""
    return DeterministicEditorialStrategyEngine().decide(
        source=source or make_source(),
        assessment=assessment or make_assessment(),
        facts=facts or make_facts(),
        content_classification=make_content(content_type),
        reader_intent=make_intent(intent),
        user_instruction=user_instruction,
    )


@pytest.mark.parametrize(
    ("content_type", "length", "depth", "mode", "target"),
    (
        (
            ContentType.BREAKING_NEWS,
            ArticleLength.VERY_SHORT,
            ArticleDepth.UPDATE,
            WritingMode.DIRECT_NEWS,
            120,
        ),
        (
            ContentType.STANDARD_NEWS,
            ArticleLength.SHORT,
            ArticleDepth.STANDARD,
            WritingMode.DIRECT_NEWS,
            220,
        ),
        (
            ContentType.PUBLIC_SERVICE_NEWS,
            ArticleLength.MEDIUM,
            ArticleDepth.EXPLAINED,
            WritingMode.SERVICE,
            450,
        ),
        (
            ContentType.GOVERNMENT_SERVICE_CONTENT,
            ArticleLength.MEDIUM,
            ArticleDepth.EXPLAINED,
            WritingMode.SERVICE,
            450,
        ),
        (
            ContentType.EXPLAINER,
            ArticleLength.MEDIUM,
            ArticleDepth.EXPLAINED,
            WritingMode.EXPLAINER,
            450,
        ),
        (
            ContentType.FACT_CHECK,
            ArticleLength.MEDIUM,
            ArticleDepth.DETAILED,
            WritingMode.FACT_CHECK,
            450,
        ),
        (
            ContentType.HEALTH_CONTENT,
            ArticleLength.SHORT,
            ArticleDepth.EXPLAINED,
            WritingMode.HIGH_RISK_CAUTION,
            220,
        ),
        (
            ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT,
            ArticleLength.SHORT,
            ArticleDepth.EXPLAINED,
            WritingMode.HIGH_RISK_CAUTION,
            220,
        ),
        (
            ContentType.SPORTS_NEWS,
            ArticleLength.VERY_SHORT,
            ArticleDepth.UPDATE,
            WritingMode.RESULT_REPORT,
            120,
        ),
        (
            ContentType.TECHNOLOGY_NEWS,
            ArticleLength.SHORT,
            ArticleDepth.STANDARD,
            WritingMode.DIRECT_NEWS,
            220,
        ),
        (
            ContentType.ECONOMY_NEWS,
            ArticleLength.SHORT,
            ArticleDepth.STANDARD,
            WritingMode.DIRECT_NEWS,
            220,
        ),
        (
            ContentType.TRENDING_SOCIAL_CLAIM,
            ArticleLength.VERY_SHORT,
            ArticleDepth.UPDATE,
            WritingMode.TREND_UPDATE,
            120,
        ),
    ),
)
def test_base_strategies(
    content_type: ContentType,
    length: ArticleLength,
    depth: ArticleDepth,
    mode: WritingMode,
    target: int,
) -> None:
    """Apply each documented base content strategy."""
    result = decide(content_type=content_type)

    assert result.article_length is length
    assert result.article_depth is depth
    assert result.writing_mode is mode
    assert result.target_word_count == target


def test_thin_source_forces_very_short_strategy() -> None:
    """Restrict medium base treatment when source depth is thin."""
    result = decide(
        source=make_source(20),
        facts=make_facts(fact_count=2),
        content_type=ContentType.EXPLAINER,
    )

    assert result.article_length is ArticleLength.VERY_SHORT
    assert result.article_depth is ArticleDepth.UPDATE
    assert result.target_word_count == 120
    assert "SOURCE_TOO_THIN_FOR_LONG_FORM" in result.warnings


def test_standard_source_does_not_exceed_medium() -> None:
    """Cap a long instruction at medium for standard depth."""
    result = decide(user_instruction="long")

    assert result.article_length is ArticleLength.MEDIUM
    assert result.target_word_count == 450


@pytest.mark.parametrize(
    "content_type", (ContentType.EXPLAINER, ContentType.FACT_CHECK)
)
def test_rich_explainer_and_fact_check_become_long(
    content_type: ContentType,
) -> None:
    """Allow rich explainers and fact checks to use long treatment."""
    result = decide(
        source=make_source(260),
        facts=make_facts(fact_count=13),
        content_type=content_type,
    )

    assert result.article_length is ArticleLength.LONG
    assert result.target_word_count == 800


def test_reader_intent_adjustments() -> None:
    """Apply action, claim, result, guidance, and requirements treatments."""
    action = decide(intent=ReaderIntent.KNOW_ACTION)
    claim = decide(intent=ReaderIntent.CHECK_CLAIM)
    result = decide(intent=ReaderIntent.FIND_RESULT)
    guidance = decide(intent=ReaderIntent.GET_GUIDANCE)
    requirements = decide(
        content_type=ContentType.GOVERNMENT_SERVICE_CONTENT,
        intent=ReaderIntent.VERIFY_REQUIREMENTS,
    )

    assert action.use_bullets is True
    assert action.include_reader_action is True
    assert claim.writing_mode is WritingMode.FACT_CHECK
    assert claim.use_attribution is True
    assert claim.include_missing_information is True
    assert result.writing_mode is WritingMode.RESULT_REPORT
    assert guidance.writing_mode is WritingMode.HIGH_RISK_CAUTION
    assert requirements.writing_mode is WritingMode.SERVICE
    assert requirements.use_headings is True
    assert requirements.use_bullets is True


def test_comparison_table_support_and_rejection() -> None:
    """Enable supported comparison tables and warn on unsupported ones."""
    supported = decide(
        intent=ReaderIntent.COMPARE_OPTIONS,
        facts=make_facts(numbers=("1", "2")),
    )
    unsupported = decide(intent=ReaderIntent.COMPARE_OPTIONS)

    assert supported.use_table is True
    assert unsupported.use_table is False
    assert "TABLE_NOT_JUSTIFIED" in unsupported.reason_codes
    assert "UNSUPPORTED_TABLE_REQUEST" in unsupported.warnings


def test_timeline_support_and_rejection() -> None:
    """Enable supported timelines and warn on unsupported ones."""
    supported = decide(
        intent=ReaderIntent.FOLLOW_DEVELOPMENT,
        facts=make_facts(dates=("2026-08-05", "2026-08-06")),
    )
    unsupported = decide(intent=ReaderIntent.FOLLOW_DEVELOPMENT)

    assert supported.use_timeline is True
    assert unsupported.use_timeline is False
    assert "TIMELINE_NOT_JUSTIFIED" in unsupported.reason_codes
    assert "UNSUPPORTED_TIMELINE_REQUEST" in unsupported.warnings


def test_quotes_attribution_and_missing_information_defaults() -> None:
    """Enable structures directly supported by extracted facts."""
    result = decide(
        facts=make_facts(
            claims=("claim",),
            quotes=("quote",),
            unknown_information=("unknown",),
        )
    )

    assert result.use_quotes is True
    assert result.use_attribution is True
    assert result.include_missing_information is True
    assert "MISSING_INFORMATION_MUST_BE_SHOWN" in result.reason_codes
    assert "MISSING_INFORMATION_NOTICE_REQUIRED" in result.warnings


def test_high_and_critical_risk_constraints() -> None:
    """Apply review warning and critical structural restrictions."""
    high = decide(assessment=make_assessment(RiskLevel.HIGH))
    critical = decide(
        assessment=make_assessment(RiskLevel.CRITICAL),
        intent=ReaderIntent.VERIFY_REQUIREMENTS,
    )

    assert high.writing_mode is WritingMode.HIGH_RISK_CAUTION
    assert "HIGH_RISK_REVIEW_REQUIRED" in high.warnings
    assert critical.article_length is ArticleLength.VERY_SHORT
    assert critical.article_depth is ArticleDepth.UPDATE
    assert critical.writing_mode is WritingMode.HIGH_RISK_CAUTION
    assert critical.use_headings is False
    assert critical.use_bullets is False
    assert critical.use_table is False
    assert critical.use_faq is False
    assert critical.use_timeline is False
    assert critical.use_background is False


def test_explicit_length_requests_obey_depth_limits() -> None:
    """Allow reduction while rejecting unsupported thin expansion."""
    shortened = decide(
        content_type=ContentType.EXPLAINER,
        user_instruction="short",
    )
    thin_long = decide(
        source=make_source(20),
        facts=make_facts(fact_count=2),
        user_instruction="long",
    )

    assert shortened.article_length is ArticleLength.SHORT
    assert thin_long.article_length is ArticleLength.VERY_SHORT
    assert "SOURCE_TOO_THIN_FOR_LONG_FORM" in thin_long.warnings
    assert "SOURCE_TOO_THIN_FOR_REQUESTED_LENGTH" in thin_long.reason_codes


def test_explicit_structural_requests_obey_rules() -> None:
    """Reject requested structures when their support rules are unmet."""
    result = decide(
        source=make_source(20),
        facts=make_facts(fact_count=2),
        user_instruction="use headings use table FAQ timeline",
    )

    assert result.use_headings is False
    assert result.use_table is False
    assert result.use_faq is False
    assert result.use_timeline is False
    assert "HEADINGS_NOT_JUSTIFIED" in result.reason_codes
    assert "TABLE_NOT_JUSTIFIED" in result.reason_codes
    assert "FAQ_NOT_JUSTIFIED" in result.reason_codes
    assert "TIMELINE_NOT_JUSTIFIED" in result.reason_codes


def test_get_update_disables_unnecessary_headings() -> None:
    """Keep concise update strategies free from headings."""
    result = decide(
        content_type=ContentType.STANDARD_NEWS,
        intent=ReaderIntent.GET_UPDATE,
    )

    assert result.use_headings is False


def test_outputs_are_unique_and_inputs_unchanged() -> None:
    """Deduplicate outputs while preserving every immutable input."""
    source = make_source(20)
    assessment = make_assessment(RiskLevel.CRITICAL)
    facts = make_facts(
        fact_count=2,
        unknown_information=("unknown", "unknown"),
    )
    content = make_content(ContentType.EXPLAINER)
    intent = make_intent(ReaderIntent.VERIFY_REQUIREMENTS)
    originals = (
        replace(source),
        replace(assessment),
        replace(facts),
        replace(content),
        replace(intent),
    )

    result = DeterministicEditorialStrategyEngine().decide(
        source=source,
        assessment=assessment,
        facts=facts,
        content_classification=content,
        reader_intent=intent,
        user_instruction="long use headings",
    )

    assert len(result.reason_codes) == len(set(result.reason_codes))
    assert len(result.warnings) == len(set(result.warnings))
    assert (source, assessment, facts, content, intent) == originals
    assert isinstance(result, EditorialStrategy)

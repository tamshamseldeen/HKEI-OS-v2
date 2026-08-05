"""Tests for additive editorial format strategy adaptation."""

from dataclasses import replace

import pytest

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.source_status import SourceStatus
from src.assessment.verification_status import VerificationStatus
from src.facts.extracted_facts import ExtractedFacts
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.strategy.article_depth import ArticleDepth
from src.strategy.article_length import ArticleLength
from src.strategy.editorial_format_strategy_adapter import (
    EditorialFormatStrategyAdapter,
)
from src.strategy.editorial_strategy import EditorialStrategy
from src.strategy.writing_mode import WritingMode


def make_strategy(**changes: object) -> EditorialStrategy:
    """Create a representative safe existing strategy."""
    strategy = EditorialStrategy(
        article_length=ArticleLength.SHORT,
        article_depth=ArticleDepth.STANDARD,
        writing_mode=WritingMode.DIRECT_NEWS,
        use_headings=False,
        use_bullets=False,
        use_table=False,
        use_faq=False,
        use_timeline=False,
        use_background=False,
        use_quotes=False,
        use_attribution=False,
        include_missing_information=False,
        include_reader_action=False,
        target_word_count=220,
        reason_codes=("EXISTING_REASON",),
        warnings=("EXISTING_WARNING",),
    )
    return replace(strategy, **changes)


def make_facts(**changes: object) -> ExtractedFacts:
    """Create immutable extracted facts with empty optional collections."""
    facts = ExtractedFacts(
        core_facts=("title", "body"),
        claims=(),
        quotes=(),
        named_people=(),
        organizations=(),
        government_entities=(),
        locations=(),
        countries=(),
        dates=(),
        times=(),
        numbers=(),
        percentages=(),
        currencies=(),
        laws_and_regulations=(),
        products=(),
        events=(),
        unknown_information=(),
        attributions=(),
    )
    return replace(facts, **changes)


def make_assessment(risk_level: RiskLevel = RiskLevel.LOW) -> SourceRiskAssessment:
    """Create an immutable assessment at the requested risk level."""
    return SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=VerificationStatus.SOURCE_PROVIDED,
        risk_level=risk_level,
        risk_topics=(),
        warnings=(),
        requires_official_source=False,
        requires_human_review=False,
        generation_allowed=True,
        reason_codes=(),
    )


def make_format(
    editorial_format: EditorialFormat,
    confidence: EditorialFormatConfidence = EditorialFormatConfidence.HIGH,
) -> EditorialFormatClassification:
    """Create a format classification for adaptation."""
    return EditorialFormatClassification(
        editorial_format=editorial_format,
        confidence=confidence,
        reason_codes=(),
        supporting_signals=(),
        warnings=(),
    )


def adapt(
    editorial_format: EditorialFormat,
    *,
    strategy: EditorialStrategy | None = None,
    facts: ExtractedFacts | None = None,
    risk_level: RiskLevel = RiskLevel.LOW,
    confidence: EditorialFormatConfidence = EditorialFormatConfidence.HIGH,
) -> EditorialStrategy:
    """Adapt convenient default fixtures for one format."""
    return EditorialFormatStrategyAdapter().adapt(
        strategy=strategy or make_strategy(),
        format_classification=make_format(editorial_format, confidence),
        facts=facts or make_facts(),
        assessment=make_assessment(risk_level),
    )


def test_breaking_adaptation() -> None:
    """Apply the compact breaking-news strategy fields."""
    result = adapt(EditorialFormat.BREAKING, strategy=make_strategy(use_faq=True))

    assert (
        result.article_length,
        result.article_depth,
        result.writing_mode,
        result.target_word_count,
    ) == (
        ArticleLength.VERY_SHORT,
        ArticleDepth.UPDATE,
        WritingMode.DIRECT_NEWS,
        120,
    )
    assert not any(
        (
            result.use_headings,
            result.use_bullets,
            result.use_table,
            result.use_faq,
            result.use_timeline,
            result.use_background,
        )
    )
    assert result.reason_codes[-1] == "FORMAT_BREAKING_STRATEGY_APPLIED"


def test_standard_news_preserves_strategy_and_returns_new_instance() -> None:
    """Preserve every strategy value except the appended confirmation reason."""
    strategy = make_strategy()
    result = adapt(EditorialFormat.STANDARD_NEWS, strategy=strategy)

    assert result is not strategy
    assert replace(result, reason_codes=strategy.reason_codes) == strategy
    assert result.reason_codes == (
        "EXISTING_REASON",
        "FORMAT_STANDARD_NEWS_CONFIRMED",
    )


def test_service_adaptation_and_table_support() -> None:
    """Expand service content and enable tables only with two monetary values."""
    result = adapt(
        EditorialFormat.SERVICE,
        facts=make_facts(numbers=("1",), currencies=("2 SAR",)),
    )

    assert result.article_length is ArticleLength.MEDIUM
    assert result.article_depth is ArticleDepth.EXPLAINED
    assert result.writing_mode is WritingMode.SERVICE
    assert result.target_word_count == 450
    assert result.use_headings and result.use_bullets and result.use_table
    assert result.include_reader_action

    compact = adapt(
        EditorialFormat.SERVICE,
        strategy=make_strategy(
            article_length=ArticleLength.VERY_SHORT,
            article_depth=ArticleDepth.UPDATE,
            target_word_count=120,
        ),
    )
    assert compact.article_length is ArticleLength.VERY_SHORT
    assert compact.article_depth is ArticleDepth.UPDATE
    assert compact.target_word_count == 120
    assert not compact.use_headings and not compact.use_table


def test_guide_adaptation_table_and_faq_support() -> None:
    """Apply guide structure based on deterministic structured-fact counts."""
    facts = make_facts(
        core_facts=("one", "two"),
        dates=("date",),
        times=("time",),
        numbers=("one",),
        currencies=("money",),
    )
    result = adapt(EditorialFormat.GUIDE, facts=facts)

    assert (
        result.article_length,
        result.article_depth,
        result.writing_mode,
        result.target_word_count,
    ) == (
        ArticleLength.MEDIUM,
        ArticleDepth.EXPLAINED,
        WritingMode.SERVICE,
        450,
    )
    assert result.use_headings and result.use_bullets
    assert result.use_table and result.use_faq and result.include_reader_action

    unsupported = adapt(EditorialFormat.GUIDE)
    assert not unsupported.use_table and not unsupported.use_faq


@pytest.mark.parametrize(
    ("original_length", "expected_length", "words", "headings"),
    (
        (ArticleLength.VERY_SHORT, ArticleLength.SHORT, 220, False),
        (ArticleLength.SHORT, ArticleLength.MEDIUM, 450, True),
    ),
)
def test_explainer_adaptation(
    original_length: ArticleLength,
    expected_length: ArticleLength,
    words: int,
    headings: bool,
) -> None:
    """Apply the specified short or medium explainer expansion."""
    result = adapt(
        EditorialFormat.EXPLAINER,
        strategy=make_strategy(article_length=original_length),
    )

    assert result.article_length is expected_length
    assert result.article_depth is ArticleDepth.EXPLAINED
    assert result.writing_mode is WritingMode.EXPLAINER
    assert result.target_word_count == words
    assert result.use_headings is headings


def test_feature_adaptation_preserves_disallowed_structure() -> None:
    """Expand a supported feature without newly enabling table, FAQ, or timeline."""
    result = adapt(
        EditorialFormat.FEATURE,
        strategy=make_strategy(use_table=True, use_faq=False, use_timeline=True),
        facts=make_facts(quotes=("quote",)),
        confidence=EditorialFormatConfidence.MEDIUM,
    )

    assert result.article_length is ArticleLength.LONG
    assert result.article_depth is ArticleDepth.DETAILED
    assert result.writing_mode is WritingMode.EXPLAINER
    assert result.target_word_count == 800
    assert result.use_headings and result.use_background and result.use_quotes
    assert result.use_table and not result.use_faq and result.use_timeline


@pytest.mark.parametrize("risk_level", (RiskLevel.HIGH, RiskLevel.CRITICAL))
def test_feature_risk_restriction(risk_level: RiskLevel) -> None:
    """Restrict feature expansion before applying the final risk override."""
    result = adapt(EditorialFormat.FEATURE, risk_level=risk_level)

    assert "FORMAT_FEATURE_RESTRICTION_APPLIED" in result.reason_codes
    assert "FORMAT_FEATURE_RESTRICTED_BY_RISK" in result.warnings
    assert "FORMAT_FEATURE_STRATEGY_APPLIED" not in result.reason_codes


def test_fact_check_adaptation() -> None:
    """Apply detailed, attributed fact-check treatment."""
    result = adapt(EditorialFormat.FACT_CHECK)

    assert result.article_length is ArticleLength.MEDIUM
    assert result.article_depth is ArticleDepth.DETAILED
    assert result.writing_mode is WritingMode.FACT_CHECK
    assert result.target_word_count == 450
    assert result.use_headings and result.use_attribution
    assert result.include_missing_information


def test_analysis_adaptation_and_critical_restriction() -> None:
    """Expand safe analysis while restricting critical-risk analysis."""
    result = adapt(EditorialFormat.ANALYSIS)
    assert result.article_length is ArticleLength.LONG
    assert result.article_depth is ArticleDepth.DETAILED
    assert result.writing_mode is WritingMode.EXPLAINER
    assert result.target_word_count == 800
    assert result.use_headings and result.use_background and result.use_attribution

    restricted = adapt(EditorialFormat.ANALYSIS, risk_level=RiskLevel.CRITICAL)
    assert "FORMAT_ANALYSIS_RESTRICTION_APPLIED" in restricted.reason_codes
    assert "FORMAT_ANALYSIS_RESTRICTED_BY_RISK" in restricted.warnings
    assert "FORMAT_ANALYSIS_STRATEGY_APPLIED" not in restricted.reason_codes


def test_interview_adaptation_preserves_disallowed_structure() -> None:
    """Apply interview treatment without newly changing structure exclusions."""
    result = adapt(
        EditorialFormat.INTERVIEW,
        strategy=make_strategy(use_table=True, use_faq=False, use_timeline=True),
    )

    assert result.article_length is ArticleLength.MEDIUM
    assert result.article_depth is ArticleDepth.DETAILED
    assert result.writing_mode is WritingMode.DIRECT_NEWS
    assert result.target_word_count == 450
    assert result.use_headings and result.use_quotes and result.use_attribution
    assert result.use_table and not result.use_faq and result.use_timeline


def test_profile_adaptation_and_risk_restriction() -> None:
    """Expand a safe profile and preserve a safer high-risk profile strategy."""
    result = adapt(EditorialFormat.PROFILE, facts=make_facts(quotes=("quote",)))
    assert result.article_length is ArticleLength.LONG
    assert result.article_depth is ArticleDepth.DETAILED
    assert result.writing_mode is WritingMode.EXPLAINER
    assert result.target_word_count == 800
    assert result.use_headings and result.use_background and result.use_quotes

    restricted = adapt(EditorialFormat.PROFILE, risk_level=RiskLevel.HIGH)
    assert "FORMAT_PROFILE_RESTRICTED_BY_RISK" in restricted.warnings
    assert "FORMAT_PROFILE_STRATEGY_APPLIED" not in restricted.reason_codes


@pytest.mark.parametrize(
    ("editorial_format", "mode", "reason"),
    (
        (
            EditorialFormat.RESULT_REPORT,
            WritingMode.RESULT_REPORT,
            "FORMAT_RESULT_REPORT_STRATEGY_APPLIED",
        ),
        (
            EditorialFormat.TREND_UPDATE,
            WritingMode.TREND_UPDATE,
            "FORMAT_TREND_UPDATE_STRATEGY_APPLIED",
        ),
    ),
)
def test_compact_update_adaptations(
    editorial_format: EditorialFormat,
    mode: WritingMode,
    reason: str,
) -> None:
    """Apply compact result-report and trend-update strategies."""
    result = adapt(editorial_format, strategy=make_strategy(use_background=True))

    assert result.article_length is ArticleLength.VERY_SHORT
    assert result.article_depth is ArticleDepth.UPDATE
    assert result.writing_mode is mode
    assert result.target_word_count == 120
    assert not any(
        (
            result.use_headings,
            result.use_bullets,
            result.use_table,
            result.use_faq,
            result.use_timeline,
            result.use_background,
        )
    )
    assert result.reason_codes[-1] == reason
    if editorial_format is EditorialFormat.TREND_UPDATE:
        assert result.use_attribution and result.include_missing_information


def test_high_risk_override_wins_after_format_expansion() -> None:
    """Apply high-risk caution fields after a nonrestricted format rule."""
    result = adapt(EditorialFormat.GUIDE, risk_level=RiskLevel.HIGH)

    assert result.writing_mode is WritingMode.HIGH_RISK_CAUTION
    assert result.use_attribution and not result.use_background
    assert result.warnings[-1] == "HIGH_RISK_REVIEW_REQUIRED"


def test_critical_risk_override_wins_after_format_expansion() -> None:
    """Apply every critical-risk compact safety field last."""
    result = adapt(
        EditorialFormat.GUIDE,
        strategy=make_strategy(use_timeline=True, use_background=True),
        risk_level=RiskLevel.CRITICAL,
    )

    assert (
        result.article_length,
        result.article_depth,
        result.writing_mode,
        result.target_word_count,
    ) == (
        ArticleLength.VERY_SHORT,
        ArticleDepth.UPDATE,
        WritingMode.HIGH_RISK_CAUTION,
        120,
    )
    assert not any(
        (
            result.use_headings,
            result.use_bullets,
            result.use_table,
            result.use_faq,
            result.use_timeline,
            result.use_background,
        )
    )
    assert result.use_attribution
    assert result.warnings[-1] == "CRITICAL_RISK_GENERATION_RESTRICTED"


def test_codes_preserve_order_append_and_remove_duplicates() -> None:
    """Keep existing codes first and deduplicate all warnings and reasons."""
    strategy = make_strategy(
        reason_codes=("FIRST", "FORMAT_STANDARD_NEWS_CONFIRMED", "FIRST"),
        warnings=("FIRST_WARNING", "HIGH_RISK_REVIEW_REQUIRED", "FIRST_WARNING"),
    )
    result = adapt(
        EditorialFormat.STANDARD_NEWS,
        strategy=strategy,
        risk_level=RiskLevel.HIGH,
    )

    assert result.reason_codes == ("FIRST", "FORMAT_STANDARD_NEWS_CONFIRMED")
    assert result.warnings == ("FIRST_WARNING", "HIGH_RISK_REVIEW_REQUIRED")


def test_inputs_are_unchanged_and_identical_inputs_are_deterministic() -> None:
    """Avoid mutation and return equal single strategies for identical inputs."""
    strategy = make_strategy()
    facts = make_facts(numbers=("1",), currencies=("2 SAR",))
    assessment = make_assessment()
    classification = make_format(EditorialFormat.SERVICE)
    snapshots = (strategy, facts, assessment)
    adapter = EditorialFormatStrategyAdapter()

    first = adapter.adapt(
        strategy=strategy,
        format_classification=classification,
        facts=facts,
        assessment=assessment,
    )
    second = adapter.adapt(
        strategy=strategy,
        format_classification=classification,
        facts=facts,
        assessment=assessment,
    )

    assert isinstance(first, EditorialStrategy)
    assert first == second
    assert first is not second
    assert (strategy, facts, assessment) == snapshots

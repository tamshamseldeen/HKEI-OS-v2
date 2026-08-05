"""Tests for deterministic article planning."""

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
from src.planning.article_plan import ArticlePlan
from src.planning.article_section_id import ArticleSectionId
from src.planning.deterministic_article_planner import DeterministicArticlePlanner
from src.strategy.article_depth import ArticleDepth
from src.strategy.article_length import ArticleLength
from src.strategy.editorial_strategy import EditorialStrategy
from src.strategy.writing_mode import WritingMode


def make_source(title: str = "Source title") -> NormalizedSource:
    """Create normalized source material for planner tests."""
    return NormalizedSource(title, "Source body", "News Agency")


def make_assessment(
    risk_level: RiskLevel = RiskLevel.LOW,
    warnings: tuple[str, ...] = ("ASSESSMENT_WARNING",),
) -> SourceRiskAssessment:
    """Create a source assessment for planner tests."""
    return SourceRiskAssessment(
        SourceStatus.IDENTIFIED,
        VerificationStatus.SOURCE_PROVIDED,
        risk_level,
        (),
        warnings,
        False,
        False,
        True,
        ("SOURCE_OK",),
    )


def make_facts(
    *,
    claims: tuple[str, ...] = ("Claim",),
    quotes: tuple[str, ...] = (),
    numbers: tuple[str, ...] = ("10",),
    currencies: tuple[str, ...] = (),
    dates: tuple[str, ...] = (),
    times: tuple[str, ...] = (),
    unknown: tuple[str, ...] = (),
    attributions: tuple[str, ...] = ("Official Agency",),
) -> ExtractedFacts:
    """Create extracted facts for planner tests."""
    return ExtractedFacts(
        core_facts=("Fact one", "Fact two", "Fact three"),
        claims=claims,
        quotes=quotes,
        named_people=(),
        organizations=(),
        government_entities=(),
        locations=(),
        countries=(),
        dates=dates,
        times=times,
        numbers=numbers,
        percentages=("25%",),
        currencies=currencies,
        laws_and_regulations=(),
        products=(),
        events=("Event",),
        unknown_information=unknown,
        attributions=attributions,
    )


def make_content(
    content_type: ContentType,
    warnings: tuple[str, ...] = ("CONTENT_WARNING",),
) -> ContentTypeClassification:
    """Create a content classification for planner tests."""
    return ContentTypeClassification(
        content_type,
        ClassificationConfidence.HIGH,
        (),
        (),
        warnings,
    )


def make_intent(
    intent: ReaderIntent,
    warnings: tuple[str, ...] = ("INTENT_WARNING",),
) -> ReaderIntentClassification:
    """Create a reader intent classification for planner tests."""
    return ReaderIntentClassification(
        intent,
        ReaderIntentConfidence.HIGH,
        (),
        (),
        warnings,
    )


def make_strategy(
    *,
    length: ArticleLength = ArticleLength.MEDIUM,
    headings: bool = True,
    quotes: bool = False,
    attribution: bool = True,
    missing: bool = False,
    reader_action: bool = False,
    background: bool = False,
    target: int = 450,
    warnings: tuple[str, ...] = ("STRATEGY_WARNING",),
) -> EditorialStrategy:
    """Create an editorial strategy for planner tests."""
    return EditorialStrategy(
        article_length=length,
        article_depth=ArticleDepth.EXPLAINED,
        writing_mode=WritingMode.DIRECT_NEWS,
        use_headings=headings,
        use_bullets=False,
        use_table=False,
        use_faq=False,
        use_timeline=False,
        use_background=background,
        use_quotes=quotes,
        use_attribution=attribution,
        include_missing_information=missing,
        include_reader_action=reader_action,
        target_word_count=target,
        reason_codes=("STRATEGY_REASON",),
        warnings=warnings,
    )


def plan(
    *,
    source: NormalizedSource | None = None,
    assessment: SourceRiskAssessment | None = None,
    facts: ExtractedFacts | None = None,
    content_type: ContentType = ContentType.STANDARD_NEWS,
    intent: ReaderIntent = ReaderIntent.GET_UPDATE,
    strategy: EditorialStrategy | None = None,
) -> ArticlePlan:
    """Build a plan from representative editorial inputs."""
    return DeterministicArticlePlanner().plan(
        source=source or make_source(),
        assessment=assessment or make_assessment(),
        facts=facts or make_facts(),
        content_classification=make_content(content_type),
        reader_intent=make_intent(intent),
        strategy=strategy or make_strategy(),
    )


@pytest.mark.parametrize(
    ("content_type", "expected"),
    (
        (
            ContentType.BREAKING_NEWS,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.STANDARD_NEWS,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
                ArticleSectionId.OFFICIAL_INFORMATION,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.NEWS_REWRITE,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
                ArticleSectionId.OFFICIAL_INFORMATION,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.PUBLIC_SERVICE_NEWS,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
                ArticleSectionId.FEES,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.GOVERNMENT_SERVICE_CONTENT,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.REQUIREMENTS,
                ArticleSectionId.PROCEDURE,
                ArticleSectionId.FEES,
                ArticleSectionId.OFFICIAL_INFORMATION,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.EXPLAINER,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.EXPLANATION,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.FACT_CHECK,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CLAIM,
                ArticleSectionId.EVIDENCE,
                ArticleSectionId.VERDICT,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.HEALTH_CONTENT,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.OFFICIAL_INFORMATION,
                ArticleSectionId.EXPLANATION,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.OFFICIAL_INFORMATION,
                ArticleSectionId.IMPACT,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.SPORTS_NEWS,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.RESULT,
                ArticleSectionId.KEY_DETAILS,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.TECHNOLOGY_NEWS,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
                ArticleSectionId.OFFICIAL_INFORMATION,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.ECONOMY_NEWS,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
                ArticleSectionId.IMPACT,
                ArticleSectionId.OFFICIAL_INFORMATION,
                ArticleSectionId.CLOSING,
            ),
        ),
        (
            ContentType.TRENDING_SOCIAL_CLAIM,
            (
                ArticleSectionId.LEAD,
                ArticleSectionId.CLAIM,
                ArticleSectionId.OFFICIAL_INFORMATION,
                ArticleSectionId.EVIDENCE,
                ArticleSectionId.CLOSING,
            ),
        ),
    ),
)
def test_content_type_section_plans(
    content_type: ContentType,
    expected: tuple[ArticleSectionId, ...],
) -> None:
    """Create each content type's ordered default sections."""
    result = plan(content_type=content_type)

    assert tuple(section.section_id for section in result.sections) == expected


def test_conditional_sections_and_protected_order() -> None:
    """Create result, requirement, missing, quote, and official sections."""
    sports = plan(
        content_type=ContentType.SPORTS_NEWS,
        facts=make_facts(quotes=("Quote",), unknown=("Unknown",)),
        strategy=make_strategy(quotes=True, missing=True),
    )
    government = plan(content_type=ContentType.GOVERNMENT_SERVICE_CONTENT)
    fact_check = plan(content_type=ContentType.FACT_CHECK)

    sports_ids = tuple(section.section_id for section in sports.sections)
    government_ids = tuple(section.section_id for section in government.sections)
    fact_check_ids = tuple(section.section_id for section in fact_check.sections)
    assert sports_ids.index(ArticleSectionId.RESULT) == 1
    assert ArticleSectionId.QUOTES in sports_ids
    assert ArticleSectionId.MISSING_INFORMATION in sports_ids
    assert ArticleSectionId.REQUIREMENTS in government_ids
    assert ArticleSectionId.PROCEDURE in government_ids
    assert ArticleSectionId.CLAIM in fact_check_ids
    assert ArticleSectionId.EVIDENCE in fact_check_ids


def test_headings_respect_strategy_and_are_not_generic() -> None:
    """Enable headings only for eligible non-edge sections."""
    headed = plan()
    very_short = plan(
        strategy=make_strategy(
            length=ArticleLength.VERY_SHORT,
            headings=True,
            target=120,
        )
    )

    assert any(section.include_heading for section in headed.sections)
    assert all(not section.include_heading for section in very_short.sections)
    guidance = tuple(
        section.heading_guidance
        for section in headed.sections
        if section.heading_guidance is not None
    )
    assert all(value not in ("التفاصيل", "معلومات", "خاتمة") for value in guidance)


def test_required_values_preserve_stage_order_and_remove_duplicates() -> None:
    """Build ordered unique facts, attributions, and workflow warnings."""
    facts = replace(
        make_facts(),
        core_facts=("Fact", "Fact", ""),
        events=("Event", "Fact"),
        numbers=("10", "10"),
        percentages=("25%",),
        currencies=("USD 10",),
        dates=("2026-08-05",),
        times=("10:00",),
        attributions=("Agency", "Agency"),
    )
    result = DeterministicArticlePlanner().plan(
        source=make_source(),
        assessment=make_assessment(warnings=("A", "SHARED")),
        facts=facts,
        content_classification=make_content(
            ContentType.STANDARD_NEWS, ("B", "SHARED")
        ),
        reader_intent=make_intent(ReaderIntent.GET_UPDATE, ("C",)),
        strategy=make_strategy(warnings=("D", "A")),
    )

    assert result.required_facts == (
        "Fact",
        "Event",
        "10",
        "25%",
        "USD 10",
        "2026-08-05",
        "10:00",
    )
    assert result.required_attributions == ("Agency", "News Agency")
    assert result.required_warnings == ("A", "SHARED", "B", "C", "D")


@pytest.mark.parametrize(
    ("content_type", "prohibited"),
    (
        (ContentType.HEALTH_CONTENT, "UNSUPPORTED_MEDICAL_GUIDANCE"),
        (
            ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT,
            "UNSUPPORTED_LEGAL_INTERPRETATION",
        ),
        (ContentType.SPORTS_NEWS, "UNSUPPORTED_RESULT_DETAILS"),
        (ContentType.TRENDING_SOCIAL_CLAIM, "UNVERIFIED_SOCIAL_CLAIM_AS_FACT"),
    ),
)
def test_content_specific_prohibited_claims(
    content_type: ContentType, prohibited: str
) -> None:
    """Add base and content-specific prohibited claims."""
    result = plan(content_type=content_type)

    assert result.prohibited_claims[:7] == (
        "UNSUPPORTED_FACT",
        "UNSUPPORTED_QUOTE",
        "UNSUPPORTED_NUMBER",
        "UNSUPPORTED_DATE",
        "UNSUPPORTED_CAUSE",
        "UNSUPPORTED_CONSEQUENCE",
        "UNSUPPORTED_ATTRIBUTION",
    )
    assert prohibited in result.prohibited_claims


def test_lead_and_closing_instructions_follow_intent_and_strategy() -> None:
    """Map intent instructions and append attribution and uncertainty."""
    result = plan(
        intent=ReaderIntent.CHECK_CLAIM,
        strategy=make_strategy(attribution=True, missing=True),
    )

    assert result.lead_instruction.startswith("Begin with the claim")
    assert result.lead_instruction.endswith(
        " Attribution is required. Preserve material uncertainty."
    )
    assert result.closing_instruction.startswith(
        "End with the supported verification status"
    )


@pytest.mark.parametrize(
    ("length", "target", "limit"),
    (
        (ArticleLength.VERY_SHORT, 120, 4),
        (ArticleLength.SHORT, 220, 6),
        (ArticleLength.MEDIUM, 450, 8),
        (ArticleLength.LONG, 800, 10),
    ),
)
def test_section_limits_and_word_allocation(
    length: ArticleLength, target: int, limit: int
) -> None:
    """Respect section limits, minimums, and total word budget."""
    result = plan(
        content_type=ContentType.PUBLIC_SERVICE_NEWS,
        facts=make_facts(
            currencies=("USD 10",),
            dates=("2026-08-05",),
            unknown=("Unknown",),
        ),
        strategy=make_strategy(
            length=length,
            missing=True,
            reader_action=True,
            target=target,
        ),
    )

    assert len(result.sections) <= limit
    assert abs(sum(section.max_words for section in result.sections) - target) <= 5
    assert all(section.max_words >= 20 for section in result.sections)
    lead = next(
        section
        for section in result.sections
        if section.section_id is ArticleSectionId.LEAD
    )
    assert lead.max_words >= 25


def test_optional_removal_preserves_protected_sections() -> None:
    """Remove optional sections before protected mandatory sections."""
    result = plan(
        content_type=ContentType.GOVERNMENT_SERVICE_CONTENT,
        facts=make_facts(
            currencies=("USD 10",),
            dates=("2026-08-05",),
            unknown=("Unknown",),
        ),
        strategy=make_strategy(
            length=ArticleLength.SHORT,
            missing=True,
            reader_action=True,
            target=220,
        ),
    )
    section_ids = tuple(section.section_id for section in result.sections)

    assert ArticleSectionId.REQUIREMENTS in section_ids
    assert ArticleSectionId.PROCEDURE in section_ids
    assert ArticleSectionId.MISSING_INFORMATION in section_ids
    assert ArticleSectionId.OFFICIAL_INFORMATION not in section_ids
    assert "UNSUPPORTED_SECTION_REMOVED" in result.reason_codes


def test_planner_warnings_and_unique_outputs() -> None:
    """Add thin, attribution, high-risk, and fact-check warnings once."""
    result = plan(
        source=NormalizedSource("Source title", "Source body", ""),
        assessment=make_assessment(RiskLevel.HIGH, ("SHARED", "SHARED")),
        facts=replace(
            make_facts(claims=(), numbers=(), attributions=()),
            core_facts=("Only fact",),
            events=(),
            percentages=(),
        ),
        content_type=ContentType.FACT_CHECK,
        strategy=make_strategy(
            length=ArticleLength.VERY_SHORT,
            attribution=True,
            target=120,
            warnings=("SHARED",),
        ),
    )

    assert "PLAN_SOURCE_TOO_THIN" in result.warnings
    assert "PLAN_ATTRIBUTION_REQUIRED" in result.warnings
    assert "PLAN_HIGH_RISK_REVIEW_REQUIRED" in result.warnings
    assert "PLAN_FACT_CHECK_EVIDENCE_INSUFFICIENT" in result.warnings
    assert len(result.reason_codes) == len(set(result.reason_codes))
    assert len(result.warnings) == len(set(result.warnings))


def test_working_title_fallback_and_inputs_unchanged() -> None:
    """Use title fallback while preserving all immutable input objects."""
    source = make_source("   ")
    assessment = make_assessment()
    facts = make_facts()
    content = make_content(ContentType.STANDARD_NEWS)
    intent = make_intent(ReaderIntent.GET_UPDATE)
    strategy = make_strategy()
    originals = tuple(
        replace(value)
        for value in (source, assessment, facts, content, intent, strategy)
    )

    result = DeterministicArticlePlanner().plan(
        source=source,
        assessment=assessment,
        facts=facts,
        content_classification=content,
        reader_intent=intent,
        strategy=strategy,
    )

    assert result.working_title == "Untitled Source"
    assert (source, assessment, facts, content, intent, strategy) == originals
    assert isinstance(result, ArticlePlan)

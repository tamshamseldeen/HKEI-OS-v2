"""Tests for deterministic reader intent classification."""

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
from src.intent.deterministic_reader_intent_classifier import (
    DeterministicReaderIntentClassifier,
)
from src.intent.reader_intent import ReaderIntent
from src.intent.reader_intent_classification import ReaderIntentClassification
from src.intent.reader_intent_confidence import ReaderIntentConfidence
from src.intake.normalized_source import NormalizedSource


def make_source(
    *, body: str = "تفاصيل الخبر", category: str | None = None
) -> NormalizedSource:
    """Create source material for reader intent tests."""
    return NormalizedSource(
        title="عنوان الخبر",
        body=body,
        source_name="وكالة الأنباء",
        category=category,
        tags=(),
    )


def make_assessment(
    *, risk_level: RiskLevel = RiskLevel.LOW, risk_topics: tuple[str, ...] = ()
) -> SourceRiskAssessment:
    """Create a source assessment for reader intent tests."""
    return SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=VerificationStatus.SOURCE_PROVIDED,
        risk_level=risk_level,
        risk_topics=risk_topics,
        warnings=(),
        requires_official_source=False,
        requires_human_review=False,
        generation_allowed=True,
        reason_codes=("SOURCE_OK",),
    )


def make_facts(*, claims: tuple[str, ...] = ()) -> ExtractedFacts:
    """Create extracted facts for reader intent tests."""
    return ExtractedFacts(
        core_facts=(), claims=claims, quotes=(), named_people=(),
        organizations=(), government_entities=(), locations=(), countries=(),
        dates=(), times=(), numbers=(), percentages=(), currencies=(),
        laws_and_regulations=(), products=(), events=(),
        unknown_information=(), attributions=(),
    )


def make_content_classification(
    content_type: ContentType = ContentType.STANDARD_NEWS,
    confidence: ClassificationConfidence = ClassificationConfidence.MEDIUM,
) -> ContentTypeClassification:
    """Create a content classification for reader intent tests."""
    return ContentTypeClassification(content_type, confidence, (), (), ())


def classify(
    *,
    source: NormalizedSource | None = None,
    assessment: SourceRiskAssessment | None = None,
    facts: ExtractedFacts | None = None,
    content_type: ContentType = ContentType.STANDARD_NEWS,
    content_confidence: ClassificationConfidence = ClassificationConfidence.MEDIUM,
    user_instruction: str | None = None,
) -> ReaderIntentClassification:
    """Classify representative reader intent inputs."""
    return DeterministicReaderIntentClassifier().classify(
        source=source or make_source(),
        assessment=assessment or make_assessment(),
        facts=facts or make_facts(),
        content_classification=make_content_classification(
            content_type, content_confidence
        ),
        user_instruction=user_instruction,
    )


@pytest.mark.parametrize(
    ("instruction", "expected", "reason", "signal"),
    (
        (
            "fact check this",
            ReaderIntent.CHECK_CLAIM,
            "EXPLICIT_CHECK_CLAIM_INTENT",
            "USER_INSTRUCTION_CHECK_CLAIM",
        ),
        (
            "requirements",
            ReaderIntent.VERIFY_REQUIREMENTS,
            "EXPLICIT_VERIFY_REQUIREMENTS_INTENT",
            "USER_INSTRUCTION_VERIFY_REQUIREMENTS",
        ),
        (
            "what should I do",
            ReaderIntent.KNOW_ACTION,
            "EXPLICIT_KNOW_ACTION_INTENT",
            "USER_INSTRUCTION_KNOW_ACTION",
        ),
        (
            "who won",
            ReaderIntent.FIND_RESULT,
            "EXPLICIT_FIND_RESULT_INTENT",
            "USER_INSTRUCTION_FIND_RESULT",
        ),
        (
            "advice",
            ReaderIntent.GET_GUIDANCE,
            "EXPLICIT_GET_GUIDANCE_INTENT",
            "USER_INSTRUCTION_GET_GUIDANCE",
        ),
        (
            "compare",
            ReaderIntent.COMPARE_OPTIONS,
            "EXPLICIT_COMPARE_OPTIONS_INTENT",
            "USER_INSTRUCTION_COMPARE_OPTIONS",
        ),
        (
            "latest developments",
            ReaderIntent.FOLLOW_DEVELOPMENT,
            "EXPLICIT_FOLLOW_DEVELOPMENT_INTENT",
            "USER_INSTRUCTION_FOLLOW_DEVELOPMENT",
        ),
        (
            "who is affected",
            ReaderIntent.UNDERSTAND_IMPACT,
            "EXPLICIT_UNDERSTAND_IMPACT_INTENT",
            "USER_INSTRUCTION_UNDERSTAND_IMPACT",
        ),
        (
            "explain",
            ReaderIntent.UNDERSTAND_EVENT,
            "EXPLICIT_UNDERSTAND_EVENT_INTENT",
            "USER_INSTRUCTION_UNDERSTAND_EVENT",
        ),
        (
            "latest news",
            ReaderIntent.GET_UPDATE,
            "EXPLICIT_GET_UPDATE_INTENT",
            "USER_INSTRUCTION_GET_UPDATE",
        ),
    ),
)
def test_explicit_intents(
    instruction: str, expected: ReaderIntent, reason: str, signal: str
) -> None:
    """Give each explicit instruction high-confidence precedence."""
    result = classify(user_instruction=instruction)

    assert result.reader_intent is expected
    assert result.confidence is ReaderIntentConfidence.HIGH
    assert result.reason_codes == (reason,)
    assert result.supporting_signals == (signal,)


@pytest.mark.parametrize(
    ("content_type", "expected"),
    (
        (ContentType.FACT_CHECK, ReaderIntent.CHECK_CLAIM),
        (ContentType.GOVERNMENT_SERVICE_CONTENT, ReaderIntent.VERIFY_REQUIREMENTS),
        (ContentType.PUBLIC_SERVICE_NEWS, ReaderIntent.KNOW_ACTION),
        (ContentType.SPORTS_NEWS, ReaderIntent.FIND_RESULT),
        (ContentType.HEALTH_CONTENT, ReaderIntent.GET_GUIDANCE),
        (ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT, ReaderIntent.UNDERSTAND_IMPACT),
        (ContentType.ECONOMY_NEWS, ReaderIntent.UNDERSTAND_IMPACT),
        (ContentType.EXPLAINER, ReaderIntent.UNDERSTAND_EVENT),
        (ContentType.TRENDING_SOCIAL_CLAIM, ReaderIntent.CHECK_CLAIM),
        (ContentType.BREAKING_NEWS, ReaderIntent.GET_UPDATE),
        (ContentType.STANDARD_NEWS, ReaderIntent.GET_UPDATE),
    ),
)
def test_content_type_defaults(
    content_type: ContentType, expected: ReaderIntent
) -> None:
    """Respect the documented content-type default mapping."""
    assert classify(content_type=content_type).reader_intent is expected


def test_comparison_and_ongoing_text_signals() -> None:
    """Classify comparison and ongoing-development terminology."""
    comparison = classify(source=make_source(body="مقارنة مزايا الخيارات"))
    ongoing = classify(source=make_source(body="آخر تطورات التحقيق"))

    assert comparison.reader_intent is ReaderIntent.COMPARE_OPTIONS
    assert ongoing.reader_intent is ReaderIntent.FOLLOW_DEVELOPMENT


def test_high_risk_guidance_adds_warning() -> None:
    """Warn when high-risk material requests guidance."""
    result = classify(
        assessment=make_assessment(risk_level=RiskLevel.HIGH),
        user_instruction="نصائح",
    )

    assert result.reader_intent is ReaderIntent.GET_GUIDANCE
    assert result.warnings == ("HIGH_RISK_GUIDANCE_REQUIRES_REVIEW",)


def test_social_claim_without_evidence_adds_warning() -> None:
    """Warn when a social claim has no extracted claim evidence."""
    result = classify(content_type=ContentType.TRENDING_SOCIAL_CLAIM)

    assert result.reader_intent is ReaderIntent.CHECK_CLAIM
    assert result.warnings == ("CLAIM_EVIDENCE_REQUIRED",)


def test_low_content_confidence_lowers_fallback_confidence() -> None:
    """Return a low-confidence warning for a low-confidence fallback."""
    result = classify(content_confidence=ClassificationConfidence.LOW)

    assert result.reader_intent is ReaderIntent.GET_UPDATE
    assert result.confidence is ReaderIntentConfidence.LOW
    assert result.warnings == ("LOW_READER_INTENT_CONFIDENCE",)


def test_explicit_instruction_overrides_content_default() -> None:
    """Apply explicit intent before content-type defaults."""
    result = classify(
        content_type=ContentType.FACT_CHECK,
        user_instruction="who won",
    )

    assert result.reader_intent is ReaderIntent.FIND_RESULT


def test_deterministic_precedence_selects_first_supported_intent() -> None:
    """Apply the exact deterministic signal precedence."""
    result = classify(
        source=make_source(
            body="ادعاء شروط رسوم مقارنة تطورات تأثير لماذا كيف"
        ),
        facts=make_facts(claims=("ادعاء",)),
    )

    assert result.reader_intent is ReaderIntent.CHECK_CLAIM


def test_outputs_are_unique_and_inputs_are_unchanged() -> None:
    """Deduplicate outputs while preserving every immutable input."""
    source = make_source(body="علاج علاج نصائح نصائح")
    assessment = make_assessment(
        risk_level=RiskLevel.HIGH,
        risk_topics=("medical", "medical"),
    )
    facts = make_facts()
    content = make_content_classification(ContentType.HEALTH_CONTENT)
    originals = (replace(source), replace(assessment), replace(facts), replace(content))

    result = DeterministicReaderIntentClassifier().classify(
        source=source,
        assessment=assessment,
        facts=facts,
        content_classification=content,
    )

    assert len(result.reason_codes) == len(set(result.reason_codes))
    assert len(result.supporting_signals) == len(set(result.supporting_signals))
    assert len(result.warnings) == len(set(result.warnings))
    assert (source, assessment, facts, content) == originals
    assert isinstance(result.reader_intent, ReaderIntent)

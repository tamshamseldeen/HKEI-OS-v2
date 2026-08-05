"""Tests for deterministic content type classification."""

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
from src.classification.deterministic_content_type_classifier import (
    DeterministicContentTypeClassifier,
)
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource


def make_source(
    *,
    title: str = "خبر جديد",
    body: str = "تفاصيل الخبر",
    category: str | None = None,
    tags: tuple[str, ...] = (),
    source_name: str = "وكالة الأنباء",
    source_url: str | None = None,
) -> NormalizedSource:
    """Create normalized source material for classification tests."""
    return NormalizedSource(
        title=title,
        body=body,
        source_name=source_name,
        source_url=source_url,
        category=category,
        tags=tags,
    )


def make_assessment(
    *,
    risk_topics: tuple[str, ...] = (),
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
) -> SourceRiskAssessment:
    """Create a source assessment for classification tests."""
    return SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=verification_status,
        risk_level=RiskLevel.LOW,
        risk_topics=risk_topics,
        warnings=(),
        requires_official_source=False,
        requires_human_review=False,
        generation_allowed=True,
        reason_codes=("SOURCE_OK",),
    )


def make_facts(*, claims: tuple[str, ...] = ()) -> ExtractedFacts:
    """Create extracted facts for classification tests."""
    return ExtractedFacts(
        core_facts=(),
        claims=claims,
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


def classify(
    *,
    source: NormalizedSource | None = None,
    assessment: SourceRiskAssessment | None = None,
    facts: ExtractedFacts | None = None,
    user_instruction: str | None = None,
) -> ContentTypeClassification:
    """Classify representative editorial ingestion values."""
    return DeterministicContentTypeClassifier().classify(
        source=source or make_source(),
        assessment=assessment or make_assessment(),
        facts=facts or make_facts(),
        user_instruction=user_instruction,
    )


def test_explicit_rewrite_intent_has_highest_precedence() -> None:
    """Classify explicit rewrite intent before every text signal."""
    result = classify(
        source=make_source(body="دواء مباراة عاجل"),
        user_instruction="أعد كتابة هذا الخبر",
    )

    assert result.content_type is ContentType.NEWS_REWRITE
    assert result.confidence is ClassificationConfidence.HIGH
    assert result.reason_codes == ("EXPLICIT_REWRITE_INTENT",)
    assert result.supporting_signals == ("USER_INSTRUCTION_REWRITE",)


def test_explicit_fact_check_with_claims() -> None:
    """Classify explicit fact checking when claim evidence exists."""
    result = classify(
        facts=make_facts(claims=("ادعاء",)),
        user_instruction="تحقق من صحة الادعاء",
    )

    assert result.content_type is ContentType.FACT_CHECK
    assert result.confidence is ClassificationConfidence.HIGH
    assert result.reason_codes == ("EXPLICIT_FACT_CHECK_INTENT",)
    assert result.supporting_signals == (
        "USER_INSTRUCTION_FACT_CHECK",
        "CLAIMS_PRESENT",
    )


def test_fact_check_without_claims_warns_and_falls_through() -> None:
    """Carry missing evidence warning into a lower-precedence result."""
    result = classify(
        source=make_source(body="مباراة اليوم"),
        user_instruction="fact check",
    )

    assert result.content_type is ContentType.SPORTS_NEWS
    assert result.warnings == ("FACT_CHECK_EVIDENCE_MISSING",)


@pytest.mark.parametrize(
    ("source", "assessment", "expected_type", "expected_confidence"),
    (
        (
            make_source(body="خطوات التقديم على تأشيرة مع رسوم"),
            make_assessment(),
            ContentType.GOVERNMENT_SERVICE_CONTENT,
            ClassificationConfidence.HIGH,
        ),
        (
            make_source(),
            make_assessment(risk_topics=("medical",)),
            ContentType.HEALTH_CONTENT,
            ClassificationConfidence.HIGH,
        ),
        (
            make_source(body="معلومات عن دواء جديد"),
            make_assessment(),
            ContentType.HEALTH_CONTENT,
            ClassificationConfidence.MEDIUM,
        ),
        (
            make_source(),
            make_assessment(risk_topics=("legal",)),
            ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT,
            ClassificationConfidence.HIGH,
        ),
        (
            make_source(body="شروط قرض وفائدة"),
            make_assessment(),
            ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT,
            ClassificationConfidence.MEDIUM,
        ),
        (
            make_source(body="إغلاق طريق بسبب الطقس"),
            make_assessment(),
            ContentType.PUBLIC_SERVICE_NEWS,
            ClassificationConfidence.MEDIUM,
        ),
        (
            make_source(body="مباراة بين فريقين"),
            make_assessment(),
            ContentType.SPORTS_NEWS,
            ClassificationConfidence.MEDIUM,
        ),
        (
            make_source(body="تطبيق ذكاء اصطناعي"),
            make_assessment(),
            ContentType.TECHNOLOGY_NEWS,
            ClassificationConfidence.MEDIUM,
        ),
        (
            make_source(body="أسعار النفط في الأسواق"),
            make_assessment(),
            ContentType.ECONOMY_NEWS,
            ClassificationConfidence.MEDIUM,
        ),
        (
            make_source(
                source_name="Twitter",
                source_url="https://twitter.com/post/1",
            ),
            make_assessment(),
            ContentType.TRENDING_SOCIAL_CLAIM,
            ClassificationConfidence.MEDIUM,
        ),
        (
            make_source(title="عاجل: خبر جديد"),
            make_assessment(),
            ContentType.BREAKING_NEWS,
            ClassificationConfidence.MEDIUM,
        ),
    ),
)
def test_content_type_rules(
    source: NormalizedSource,
    assessment: SourceRiskAssessment,
    expected_type: ContentType,
    expected_confidence: ClassificationConfidence,
) -> None:
    """Classify each deterministic content signal."""
    result = classify(source=source, assessment=assessment)

    assert result.content_type is expected_type
    assert result.confidence is expected_confidence


def test_explainer_from_user_instruction() -> None:
    """Give explicit explainer instructions high confidence."""
    result = classify(user_instruction="اشرح هذا الموضوع")

    assert result.content_type is ContentType.EXPLAINER
    assert result.confidence is ClassificationConfidence.HIGH


def test_explainer_from_structural_terms() -> None:
    """Match an explainer when at least two structural terms exist."""
    result = classify(source=make_source(body="كيف حدث هذا وما هي الأسباب"))

    assert result.content_type is ContentType.EXPLAINER
    assert result.confidence is ClassificationConfidence.MEDIUM


def test_default_standard_news_has_low_confidence_warning() -> None:
    """Default safely to low-confidence standard news."""
    result = classify()

    assert result.content_type is ContentType.STANDARD_NEWS
    assert result.confidence is ClassificationConfidence.LOW
    assert result.reason_codes == ("DEFAULT_STANDARD_NEWS",)
    assert result.warnings == ("LOW_CLASSIFICATION_CONFIDENCE",)


def test_explicit_categories_produce_high_confidence() -> None:
    """Use explicit sports, technology, and economy categories as confidence."""
    cases = (
        ("sports", "مباراة", ContentType.SPORTS_NEWS),
        ("technology", "تطبيق", ContentType.TECHNOLOGY_NEWS),
        ("economy", "أسعار", ContentType.ECONOMY_NEWS),
    )

    for category, body, expected in cases:
        result = classify(source=make_source(body=body, category=category))
        assert result.content_type is expected
        assert result.confidence is ClassificationConfidence.HIGH


def test_exact_precedence_selects_first_matching_rule() -> None:
    """Select the first match from the required precedence order."""
    result = classify(
        source=make_source(
            body=(
                "تأشيرة رسوم دواء قانون غرامة مرورية مباراة تطبيق "
                "اقتصاد عاجل كيف الأسباب"
            ),
            source_name="Twitter",
        )
    )

    assert result.content_type is ContentType.GOVERNMENT_SERVICE_CONTENT


def test_outputs_are_unique_and_selected_rule_only() -> None:
    """Deduplicate output values and hide unmatched-rule evidence."""
    result = classify(
        source=make_source(
            body="دواء دواء علاج علاج",
            tags=("دواء", "دواء"),
        ),
        assessment=make_assessment(risk_topics=("medical", "medical")),
    )

    assert len(result.reason_codes) == len(set(result.reason_codes))
    assert len(result.supporting_signals) == len(
        set(result.supporting_signals)
    )
    assert len(result.warnings) == len(set(result.warnings))
    assert all("SPORTS" not in signal for signal in result.supporting_signals)


def test_source_objects_remain_unchanged() -> None:
    """Leave all immutable classification inputs unchanged."""
    source = make_source(body="دواء", tags=("صحة",))
    assessment = make_assessment(risk_topics=("medical",))
    facts = make_facts(claims=("claim",))
    original_source = replace(source)
    original_assessment = replace(assessment)
    original_facts = replace(facts)

    result = classify(source=source, assessment=assessment, facts=facts)

    assert source == original_source
    assert assessment == original_assessment
    assert facts == original_facts
    assert isinstance(result.content_type, ContentType)

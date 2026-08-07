"""Tests for topic-and-format-aware reader intent classification."""

from dataclasses import replace
from inspect import signature

import pytest

from examples.run_benchmark_batch_01_analysis import BATCH_ROOT, parse_source, read_manifest
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
from src.intent.deterministic_reader_intent_classifier_v2 import (
    DeterministicReaderIntentClassifierV2,
)
from src.intent.reader_intent import ReaderIntent
from src.intent.reader_intent_classification import ReaderIntentClassification
from src.intent.reader_intent_confidence import ReaderIntentConfidence
from src.intake.normalized_source import NormalizedSource
from src.topic.topic import Topic
from src.topic.topic_classification import TopicClassification
from src.topic.topic_confidence import TopicConfidence
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


def make_source(
    *,
    title: str = "عنوان الخبر",
    body: str = "تفاصيل الخبر الحالية.",
    category: str | None = None,
    tags: tuple[str, ...] = (),
) -> NormalizedSource:
    """Create normalized source material for V2 intent tests."""
    return NormalizedSource(
        title=title,
        body=body,
        source_name="Source",
        source_url="https://example.com",
        category=category,
        tags=tags,
    )


def make_assessment(
    risk_level: RiskLevel = RiskLevel.LOW,
) -> SourceRiskAssessment:
    """Create an independent assessment at the requested risk level."""
    return SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=VerificationStatus.SOURCE_PROVIDED,
        risk_level=risk_level,
        risk_topics=(),
        warnings=(),
        requires_official_source=False,
        requires_human_review=risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
        generation_allowed=risk_level is not RiskLevel.CRITICAL,
        reason_codes=("SOURCE_OK",),
    )


def make_facts(**changes: object) -> ExtractedFacts:
    """Create extracted facts with configurable structural collections."""
    facts = ExtractedFacts(
        core_facts=(),
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


def make_topic(topic: Topic = Topic.GENERAL) -> TopicClassification:
    """Create an independent topic classification."""
    return TopicClassification(topic, TopicConfidence.HIGH, (), (), ())


def make_format(
    editorial_format: EditorialFormat = EditorialFormat.STANDARD_NEWS,
    confidence: EditorialFormatConfidence = EditorialFormatConfidence.HIGH,
) -> EditorialFormatClassification:
    """Create an independent editorial format classification."""
    return EditorialFormatClassification(
        editorial_format,
        confidence,
        (),
        (),
        (),
    )


def classify(
    *,
    source: NormalizedSource | None = None,
    assessment: SourceRiskAssessment | None = None,
    facts: ExtractedFacts | None = None,
    topic: Topic = Topic.GENERAL,
    editorial_format: EditorialFormat = EditorialFormat.STANDARD_NEWS,
    format_confidence: EditorialFormatConfidence = EditorialFormatConfidence.HIGH,
    user_instruction: str | None = None,
) -> ReaderIntentClassification:
    """Classify convenient deterministic default inputs."""
    return DeterministicReaderIntentClassifierV2().classify(
        source=source or make_source(),
        assessment=assessment or make_assessment(),
        facts=facts or make_facts(),
        topic_classification=make_topic(topic),
        format_classification=make_format(editorial_format, format_confidence),
        user_instruction=user_instruction,
    )


@pytest.mark.parametrize(
    ("editorial_format", "expected"),
    (
        (EditorialFormat.BREAKING, ReaderIntent.GET_UPDATE),
        (EditorialFormat.STANDARD_NEWS, ReaderIntent.GET_UPDATE),
        (EditorialFormat.SERVICE, ReaderIntent.KNOW_ACTION),
        (EditorialFormat.GUIDE, ReaderIntent.VERIFY_REQUIREMENTS),
        (EditorialFormat.EXPLAINER, ReaderIntent.UNDERSTAND_EVENT),
        (EditorialFormat.FEATURE, ReaderIntent.UNDERSTAND_EVENT),
        (EditorialFormat.FACT_CHECK, ReaderIntent.CHECK_CLAIM),
        (EditorialFormat.ANALYSIS, ReaderIntent.UNDERSTAND_IMPACT),
        (EditorialFormat.INTERVIEW, ReaderIntent.UNDERSTAND_EVENT),
        (EditorialFormat.PROFILE, ReaderIntent.UNDERSTAND_EVENT),
        (EditorialFormat.RESULT_REPORT, ReaderIntent.FIND_RESULT),
        (EditorialFormat.TREND_UPDATE, ReaderIntent.CHECK_CLAIM),
    ),
)
def test_format_defaults(
    editorial_format: EditorialFormat,
    expected: ReaderIntent,
) -> None:
    """Map every editorial format to its specified default reader intent."""
    result = classify(editorial_format=editorial_format)

    assert result.reader_intent is expected
    assert result.confidence is ReaderIntentConfidence.HIGH
    assert f"FORMAT_{editorial_format.value}" in result.supporting_signals


@pytest.mark.parametrize(
    ("editorial_format", "expected"),
    (
        (EditorialFormat.STANDARD_NEWS, ReaderIntent.GET_UPDATE),
        (EditorialFormat.FEATURE, ReaderIntent.UNDERSTAND_EVENT),
        (EditorialFormat.GUIDE, ReaderIntent.VERIFY_REQUIREMENTS),
        (EditorialFormat.RESULT_REPORT, ReaderIntent.FIND_RESULT),
    ),
)
def test_sports_topic_follows_format_not_legacy_result_assumption(
    editorial_format: EditorialFormat,
    expected: ReaderIntent,
) -> None:
    """Select FIND_RESULT for sports only when format is RESULT_REPORT."""
    result = classify(topic=Topic.SPORTS, editorial_format=editorial_format)

    assert result.reader_intent is expected


@pytest.mark.parametrize(
    ("topic", "editorial_format", "expected"),
    (
        (Topic.ECONOMY, EditorialFormat.STANDARD_NEWS, ReaderIntent.GET_UPDATE),
        (Topic.ECONOMY, EditorialFormat.ANALYSIS, ReaderIntent.UNDERSTAND_IMPACT),
        (Topic.GOVERNMENT, EditorialFormat.SERVICE, ReaderIntent.KNOW_ACTION),
        (
            Topic.GOVERNMENT,
            EditorialFormat.GUIDE,
            ReaderIntent.VERIFY_REQUIREMENTS,
        ),
        (Topic.TECHNOLOGY, EditorialFormat.STANDARD_NEWS, ReaderIntent.GET_UPDATE),
        (Topic.CULTURE, EditorialFormat.STANDARD_NEWS, ReaderIntent.GET_UPDATE),
        (Topic.WEATHER, EditorialFormat.BREAKING, ReaderIntent.GET_UPDATE),
    ),
)
def test_topic_context_does_not_override_format(
    topic: Topic,
    editorial_format: EditorialFormat,
    expected: ReaderIntent,
) -> None:
    """Use topic only as supporting context for format-led intent."""
    result = classify(topic=topic, editorial_format=editorial_format)

    assert result.reader_intent is expected
    assert f"TOPIC_{topic.value}" in result.supporting_signals


def test_risk_alone_does_not_create_understand_impact() -> None:
    """Keep ordinary news at GET_UPDATE despite high independent risk."""
    result = classify(
        assessment=make_assessment(RiskLevel.HIGH),
        topic=Topic.ECONOMY,
        editorial_format=EditorialFormat.STANDARD_NEWS,
    )

    assert result.reader_intent is ReaderIntent.GET_UPDATE


def test_health_topic_alone_does_not_force_guidance() -> None:
    """Keep ordinary health news at its standard-news update intent."""
    result = classify(
        topic=Topic.HEALTH,
        editorial_format=EditorialFormat.STANDARD_NEWS,
    )

    assert result.reader_intent is ReaderIntent.GET_UPDATE


def test_high_risk_guidance_adds_review_warning() -> None:
    """Add review warning when supported health guidance is high risk."""
    result = classify(
        source=make_source(body="إرشادات وقاية للمريض"),
        assessment=make_assessment(RiskLevel.HIGH),
        topic=Topic.HEALTH,
    )

    assert result.reader_intent is ReaderIntent.GET_GUIDANCE
    assert result.warnings == ("HIGH_RISK_GUIDANCE_REQUIRES_REVIEW",)


def test_explicit_instruction_overrides_format_default() -> None:
    """Preserve existing explicit vocabulary at highest precedence."""
    result = classify(
        topic=Topic.SPORTS,
        editorial_format=EditorialFormat.RESULT_REPORT,
        user_instruction="اشرح لماذا حدث ذلك",
    )

    assert result.reader_intent is ReaderIntent.UNDERSTAND_EVENT
    assert result.confidence is ReaderIntentConfidence.HIGH
    assert result.reason_codes[:2] == (
        "EXPLICIT_READER_INTENT",
        "EXPLICIT_UNDERSTAND_EVENT_INTENT",
    )


def test_low_format_confidence_produces_low_update_confidence() -> None:
    """Downgrade a GET_UPDATE fallback when format confidence is low."""
    result = classify(
        editorial_format=EditorialFormat.STANDARD_NEWS,
        format_confidence=EditorialFormatConfidence.LOW,
    )

    assert result.reader_intent is ReaderIntent.GET_UPDATE
    assert result.confidence is ReaderIntentConfidence.LOW
    assert result.warnings == ("LOW_READER_INTENT_CONFIDENCE",)


def test_structural_claim_requirements_action_and_impact_rules() -> None:
    """Apply supported structural evidence without legacy content classification."""
    claim = classify(
        source=make_source(body="ورد ادعاء يحتاج التحقق من كونه صحيح"),
        facts=make_facts(claims=("claim",)),
    )
    requirements = classify(
        source=make_source(body="الموعد والقنوات الناقلة"),
        topic=Topic.SPORTS,
        editorial_format=EditorialFormat.GUIDE,
    )
    action = classify(
        source=make_source(body="تنبيه: يجب الالتزام لتجنب مخالفة"),
        topic=Topic.GOVERNMENT,
        editorial_format=EditorialFormat.SERVICE,
    )
    impact = classify(
        source=make_source(body="يوضح التأثير والتداعيات على الأسواق"),
        topic=Topic.ECONOMY,
    )

    assert claim.reader_intent is ReaderIntent.CHECK_CLAIM
    assert requirements.reader_intent is ReaderIntent.VERIFY_REQUIREMENTS
    assert action.reader_intent is ReaderIntent.KNOW_ACTION
    assert impact.reader_intent is ReaderIntent.UNDERSTAND_IMPACT


def test_output_collections_are_deduplicated() -> None:
    """Return ordered reason, signal, and warning tuples without duplicates."""
    result = classify(
        source=make_source(body="تنبيه تنبيه يجب يجب مخالفة مخالفة"),
        assessment=make_assessment(RiskLevel.HIGH),
        topic=Topic.GOVERNMENT,
        editorial_format=EditorialFormat.SERVICE,
    )

    assert len(result.reason_codes) == len(set(result.reason_codes))
    assert len(result.supporting_signals) == len(set(result.supporting_signals))
    assert len(result.warnings) == len(set(result.warnings))


def test_inputs_remain_unchanged_and_results_are_deterministic() -> None:
    """Avoid mutation and return equal single results for identical inputs."""
    source = make_source(
        title="دليل المباراة",
        body="الموعد والقنوات الناقلة وكيف تشاهد",
        category="sports",
        tags=("السوبر",),
    )
    assessment = make_assessment()
    facts = make_facts(dates=("2026-08-07",), times=("22:00",))
    topic = make_topic(Topic.SPORTS)
    editorial_format = make_format(EditorialFormat.GUIDE)
    snapshots = (source, assessment, facts, topic, editorial_format)
    classifier = DeterministicReaderIntentClassifierV2()

    first = classifier.classify(
        source=source,
        assessment=assessment,
        facts=facts,
        topic_classification=topic,
        format_classification=editorial_format,
        user_instruction=None,
    )
    second = classifier.classify(
        source=source,
        assessment=assessment,
        facts=facts,
        topic_classification=topic,
        format_classification=editorial_format,
        user_instruction=None,
    )

    assert isinstance(first, ReaderIntentClassification)
    assert first == second
    assert first is not second
    assert (source, assessment, facts, topic, editorial_format) == snapshots
    assert "content_classification" not in signature(classifier.classify).parameters


def test_batch_01_target_scenarios() -> None:
    """Produce all specified topic-and-format-aware Batch 01 intents."""
    expected = (
        ReaderIntent.GET_UPDATE,
        ReaderIntent.GET_UPDATE,
        ReaderIntent.GET_UPDATE,
        ReaderIntent.GET_UPDATE,
        ReaderIntent.GET_UPDATE,
        ReaderIntent.GET_UPDATE,
        ReaderIntent.VERIFY_REQUIREMENTS,
        ReaderIntent.GET_UPDATE,
        ReaderIntent.FIND_RESULT,
        ReaderIntent.GET_UPDATE,
    )
    actual: list[ReaderIntent] = []

    for manifest_case in read_manifest():
        benchmark_source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        fields = {
            "title": benchmark_source.title,
            "body": benchmark_source.body,
            "source_name": benchmark_source.source_name,
            "source_url": benchmark_source.source_url,
            "published_at": None,
            "language": "ar",
            "country": None,
            "author": None,
            "images": (),
            "attachments": (),
            "category": benchmark_source.benchmark_category,
            "tags": (),
            "user_instruction": None,
        }
        topic_result = EditorialTopicWorkflow().process(**fields)
        format_result = EditorialFormatWorkflow().process(**fields)
        ingestion = topic_result.classification_result.ingestion
        actual.append(
            DeterministicReaderIntentClassifierV2()
            .classify(
                source=ingestion.source,
                assessment=ingestion.assessment,
                facts=ingestion.facts,
                topic_classification=topic_result.topic_classification,
                format_classification=format_result.format_classification,
                user_instruction=None,
            )
            .reader_intent
        )

    assert tuple(actual) == expected

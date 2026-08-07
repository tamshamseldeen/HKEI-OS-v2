"""Tests for the additive editorial topic workflow."""

from dataclasses import FrozenInstanceError
from unittest.mock import Mock, call, create_autospec

import pytest

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.source_status import SourceStatus
from src.assessment.verification_status import VerificationStatus
from src.classification.classification_confidence import ClassificationConfidence
from src.classification.content_type import ContentType
from src.classification.content_type_classification import ContentTypeClassification
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource
from src.intake.source_intake import SourceValidationError
from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier
from src.topic.topic import Topic
from src.topic.topic_classification import TopicClassification
from src.topic.topic_confidence import TopicConfidence
from src.workflows.editorial_classification_result import (
    EditorialClassificationResult,
)
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.editorial_ingestion_result import EditorialIngestionResult
from src.workflows.editorial_topic_result import EditorialTopicResult
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


SOURCE_FIELDS = {
    "title": "البنك المركزي يثبت أسعار الفائدة",
    "body": "يتابع البنك التضخم واستقرار الأسواق.",
    "source_name": "Official Source",
    "source_url": "https://example.com/economy",
    "published_at": "2026-08-07T10:00:00Z",
    "language": "ar",
    "country": "Egypt",
    "author": "Reporter",
    "images": ("image.jpg",),
    "attachments": ("document.pdf",),
    "category": "economy",
    "tags": ("اقتصاد", "فائدة"),
}


def make_classification_result(
    *,
    generation_allowed: bool = True,
) -> EditorialClassificationResult:
    """Create one complete upstream result with configurable generation status."""
    source = NormalizedSource(
        title=SOURCE_FIELDS["title"],
        body=SOURCE_FIELDS["body"],
        source_name=SOURCE_FIELDS["source_name"],
        source_url=SOURCE_FIELDS["source_url"],
        published_at=SOURCE_FIELDS["published_at"],
        language=SOURCE_FIELDS["language"],
        country=SOURCE_FIELDS["country"],
        author=SOURCE_FIELDS["author"],
        images=SOURCE_FIELDS["images"],
        attachments=SOURCE_FIELDS["attachments"],
        category=SOURCE_FIELDS["category"],
        tags=SOURCE_FIELDS["tags"],
    )
    assessment = SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=VerificationStatus.SOURCE_PROVIDED,
        risk_level=RiskLevel.LOW,
        risk_topics=(),
        warnings=(),
        requires_official_source=False,
        requires_human_review=False,
        generation_allowed=generation_allowed,
        reason_codes=("SOURCE_OK",),
    )
    facts = ExtractedFacts(
        core_facts=(source.title, source.body),
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
        events=(source.title,),
        unknown_information=(),
        attributions=(source.source_name,),
    )
    ingestion = EditorialIngestionResult(source, assessment, facts)
    classification = ContentTypeClassification(
        content_type=ContentType.ECONOMY_NEWS,
        confidence=ClassificationConfidence.HIGH,
        reason_codes=("ECONOMY_SIGNAL",),
        supporting_signals=(),
        warnings=(),
    )
    return EditorialClassificationResult(ingestion, classification)


def make_topic_classification() -> TopicClassification:
    """Create a representative deterministic topic result."""
    return TopicClassification(
        topic=Topic.ECONOMY,
        confidence=TopicConfidence.HIGH,
        reason_codes=("SOURCE_CATEGORY_TOPIC_MATCH",),
        supporting_signals=("CATEGORY_ECONOMY",),
        warnings=(),
    )


def make_mocked_workflow(
    *,
    generation_allowed: bool = True,
) -> tuple[
    EditorialTopicWorkflow,
    EditorialClassificationWorkflow,
    DeterministicTopicClassifier,
    EditorialClassificationResult,
    TopicClassification,
]:
    """Create an additive workflow with configured dependency mocks."""
    classification_result = make_classification_result(
        generation_allowed=generation_allowed
    )
    topic_classification = make_topic_classification()
    classification_workflow = create_autospec(
        EditorialClassificationWorkflow,
        instance=True,
    )
    topic_classifier = create_autospec(
        DeterministicTopicClassifier,
        instance=True,
    )
    classification_workflow.process.return_value = classification_result
    topic_classifier.classify.return_value = topic_classification
    workflow = EditorialTopicWorkflow(
        classification_workflow=classification_workflow,
        topic_classifier=topic_classifier,
    )
    return (
        workflow,
        classification_workflow,
        topic_classifier,
        classification_result,
        topic_classification,
    )


def test_valid_input_returns_result_with_default_dependencies() -> None:
    """Process valid raw input using default additive dependencies."""
    workflow = EditorialTopicWorkflow()

    result = workflow.process(**SOURCE_FIELDS)

    assert isinstance(
        workflow.classification_workflow,
        EditorialClassificationWorkflow,
    )
    assert isinstance(workflow.topic_classifier, DeterministicTopicClassifier)
    assert isinstance(result, EditorialTopicResult)
    assert isinstance(result.classification_result, EditorialClassificationResult)
    assert isinstance(result.topic_classification, TopicClassification)
    assert result.topic_classification.topic is Topic.ECONOMY


def test_injected_dependencies_are_used_once_in_order_with_exact_values() -> None:
    """Store dependencies and call each once in order with unchanged values."""
    workflow, upstream, classifier, classification_result, topic_result = (
        make_mocked_workflow()
    )
    ingestion = classification_result.ingestion
    calls = Mock()
    calls.attach_mock(upstream, "classification")
    calls.attach_mock(classifier, "topic")

    result = workflow.process(
        **SOURCE_FIELDS,
        user_instruction="ركز على الاقتصاد",
    )

    assert workflow.classification_workflow is upstream
    assert workflow.topic_classifier is classifier
    assert result.classification_result is classification_result
    assert result.topic_classification is topic_result
    assert calls.mock_calls == [
        call.classification.process(
            **SOURCE_FIELDS,
            user_instruction="ركز على الاقتصاد",
        ),
        call.topic.classify(
            source=ingestion.source,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
            content_classification=classification_result.classification,
            user_instruction="ركز على الاقتصاد",
        ),
    ]


@pytest.mark.parametrize(
    "failure",
    (
        SourceValidationError(("MISSING_TITLE",)),
        RuntimeError("classification workflow failed"),
    ),
)
def test_classification_workflow_failures_propagate_unchanged(
    failure: Exception,
) -> None:
    """Propagate upstream failures without invoking topic classification."""
    workflow, upstream, classifier, *_ = make_mocked_workflow()
    upstream.process.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    assert classifier.mock_calls == []


def test_topic_classifier_failure_propagates_unchanged() -> None:
    """Propagate topic failure after exactly one upstream call."""
    workflow, upstream, classifier, classification_result, _ = (
        make_mocked_workflow()
    )
    ingestion = classification_result.ingestion
    failure = RuntimeError("topic classification failed")
    classifier.classify.side_effect = failure

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    classifier.classify.assert_called_once_with(
        source=ingestion.source,
        facts=ingestion.facts,
        assessment=ingestion.assessment,
        content_classification=classification_result.classification,
        user_instruction=None,
    )


def test_topic_runs_when_generation_is_not_allowed() -> None:
    """Continue additive topic analysis when generation is blocked."""
    workflow, upstream, classifier, classification_result, topic_result = (
        make_mocked_workflow(generation_allowed=False)
    )

    result = workflow.process(**SOURCE_FIELDS)

    assert classification_result.ingestion.assessment.generation_allowed is False
    assert result.topic_classification is topic_result
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    classifier.classify.assert_called_once()


def test_raw_source_objects_are_forwarded_unchanged() -> None:
    """Forward tuple inputs by identity without changing the caller mapping."""
    workflow, upstream, *_ = make_mocked_workflow()
    fields = dict(SOURCE_FIELDS)
    images = fields["images"]
    attachments = fields["attachments"]
    tags = fields["tags"]

    workflow.process(**fields)

    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    assert fields == SOURCE_FIELDS
    assert fields["images"] is images
    assert fields["attachments"] is attachments
    assert fields["tags"] is tags


def test_result_model_is_immutable() -> None:
    """Prevent reassignment of additive result fields."""
    classification_result = make_classification_result()
    topic_classification = make_topic_classification()
    result = EditorialTopicResult(classification_result, topic_classification)

    with pytest.raises(FrozenInstanceError):
        result.topic_classification = topic_classification  # type: ignore[misc]

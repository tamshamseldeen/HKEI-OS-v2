"""Tests for the editorial intent workflow."""

from dataclasses import FrozenInstanceError
from unittest.mock import Mock, call, create_autospec

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
from src.intake.source_intake import SourceValidationError
from src.workflows.editorial_classification_result import (
    EditorialClassificationResult,
)
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.editorial_ingestion_result import EditorialIngestionResult
from src.workflows.editorial_intent_result import EditorialIntentResult
from src.workflows.editorial_intent_workflow import EditorialIntentWorkflow


SOURCE_FIELDS = {
    "title": "Headline",
    "body": "Article body",
    "source_name": "News Agency",
    "source_url": "https://example.com/article",
    "published_at": "2026-08-05T10:00:00Z",
    "language": "en",
    "country": "Saudi Arabia",
    "author": "Reporter",
    "images": ("image.jpg",),
    "attachments": ("document.pdf",),
    "category": "news",
    "tags": ("example",),
}


def make_classification_result(
    *, generation_allowed: bool = True
) -> EditorialClassificationResult:
    """Create a complete classification result for workflow tests.

    Args:
        generation_allowed: Whether the assessment permits generation.

    Returns:
        A representative editorial classification result.
    """
    source = NormalizedSource("Headline", "Article body", "News Agency")
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
        content_type=ContentType.STANDARD_NEWS,
        confidence=ClassificationConfidence.MEDIUM,
        reason_codes=("DEFAULT_STANDARD_NEWS",),
        supporting_signals=(),
        warnings=(),
    )
    return EditorialClassificationResult(ingestion, classification)


def make_reader_intent() -> ReaderIntentClassification:
    """Create a reader intent classification for workflow tests.

    Returns:
        A representative reader intent classification.
    """
    return ReaderIntentClassification(
        reader_intent=ReaderIntent.GET_UPDATE,
        confidence=ReaderIntentConfidence.MEDIUM,
        reason_codes=("DEFAULT_GET_UPDATE",),
        supporting_signals=("CONTENT_TYPE_FALLBACK",),
        warnings=(),
    )


def make_mocked_workflow(
    classification_result: EditorialClassificationResult | None = None,
) -> tuple[
    EditorialIntentWorkflow,
    EditorialClassificationWorkflow,
    DeterministicReaderIntentClassifier,
    EditorialClassificationResult,
    ReaderIntentClassification,
]:
    """Create an intent workflow with configured mock dependencies.

    Args:
        classification_result: Upstream result, or None for a default result.

    Returns:
        The workflow, dependencies, and configured results.
    """
    upstream_result = classification_result or make_classification_result()
    intent = make_reader_intent()
    classification_workflow = create_autospec(
        EditorialClassificationWorkflow, instance=True
    )
    intent_classifier = create_autospec(
        DeterministicReaderIntentClassifier, instance=True
    )
    classification_workflow.process.return_value = upstream_result
    intent_classifier.classify.return_value = intent
    workflow = EditorialIntentWorkflow(
        classification_workflow=classification_workflow,
        reader_intent_classifier=intent_classifier,
    )
    return (
        workflow,
        classification_workflow,
        intent_classifier,
        upstream_result,
        intent,
    )


def test_valid_raw_input_returns_result_with_default_dependencies() -> None:
    """Process valid raw input using default workflow dependencies."""
    workflow = EditorialIntentWorkflow()

    result = workflow.process(**SOURCE_FIELDS, user_instruction=None)

    assert isinstance(
        workflow.classification_workflow, EditorialClassificationWorkflow
    )
    assert isinstance(
        workflow.reader_intent_classifier,
        DeterministicReaderIntentClassifier,
    )
    assert isinstance(result, EditorialIntentResult)
    assert isinstance(result.classification_result, EditorialClassificationResult)
    assert isinstance(result.reader_intent, ReaderIntentClassification)


def test_injected_dependencies_are_used_once_in_order() -> None:
    """Store and call injected dependencies once in required order."""
    workflow, upstream, classifier, classification_result, intent = (
        make_mocked_workflow()
    )
    ingestion = classification_result.ingestion
    classification = classification_result.classification
    calls = Mock()
    calls.attach_mock(upstream, "classification_workflow")
    calls.attach_mock(classifier, "reader_intent")
    instruction = "latest news"

    result = workflow.process(**SOURCE_FIELDS, user_instruction=instruction)

    assert workflow.classification_workflow is upstream
    assert workflow.reader_intent_classifier is classifier
    assert result.classification_result is classification_result
    assert result.reader_intent is intent
    assert calls.mock_calls == [
        call.classification_workflow.process(
            **SOURCE_FIELDS, user_instruction=instruction
        ),
        call.reader_intent.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification,
            user_instruction=instruction,
        ),
    ]


def test_source_validation_error_propagates_unchanged() -> None:
    """Propagate source validation errors without intent classification."""
    workflow, upstream, classifier, *_ = make_mocked_workflow()
    expected = SourceValidationError(("MISSING_TITLE",))
    upstream.process.side_effect = expected

    with pytest.raises(SourceValidationError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS, user_instruction=None
    )
    assert classifier.mock_calls == []


def test_classification_workflow_failure_propagates_unchanged() -> None:
    """Propagate upstream failures without intent classification."""
    workflow, upstream, classifier, *_ = make_mocked_workflow()
    expected = RuntimeError("classification workflow failed")
    upstream.process.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS, user_instruction=None
    )
    assert classifier.mock_calls == []


def test_reader_intent_failure_propagates_unchanged() -> None:
    """Propagate intent classifier failures after one upstream call."""
    workflow, upstream, classifier, result, _ = make_mocked_workflow()
    ingestion = result.ingestion
    expected = RuntimeError("reader intent failed")
    classifier.classify.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS, user_instruction="latest news")

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS, user_instruction="latest news"
    )
    classifier.classify.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        content_classification=result.classification,
        user_instruction="latest news",
    )


def test_intent_runs_when_generation_is_not_allowed() -> None:
    """Classify reader intent when the assessment blocks generation."""
    result = make_classification_result(generation_allowed=False)
    workflow, _, classifier, _, intent = make_mocked_workflow(result)
    ingestion = result.ingestion

    actual = workflow.process(**SOURCE_FIELDS)

    classifier.classify.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        content_classification=result.classification,
        user_instruction=None,
    )
    assert actual.reader_intent is intent


def test_result_model_is_immutable() -> None:
    """Prevent editorial intent result fields from reassignment."""
    classification_result = make_classification_result()
    result = EditorialIntentResult(
        classification_result=classification_result,
        reader_intent=make_reader_intent(),
    )

    with pytest.raises(FrozenInstanceError):
        result.classification_result = (  # type: ignore[misc]
            classification_result
        )

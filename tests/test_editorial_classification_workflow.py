"""Tests for the editorial classification workflow."""

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
from src.classification.deterministic_content_type_classifier import (
    DeterministicContentTypeClassifier,
)
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource
from src.intake.source_intake import SourceValidationError
from src.workflows.editorial_classification_result import (
    EditorialClassificationResult,
)
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.editorial_ingestion_result import EditorialIngestionResult
from src.workflows.editorial_ingestion_workflow import EditorialIngestionWorkflow


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


def make_ingestion(
    *, generation_allowed: bool = True
) -> EditorialIngestionResult:
    """Create an editorial ingestion result for workflow tests.

    Args:
        generation_allowed: Whether the assessment permits generation.

    Returns:
        A representative editorial ingestion result.
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
    return EditorialIngestionResult(source, assessment, facts)


def make_classification() -> ContentTypeClassification:
    """Create a content type classification for workflow tests.

    Returns:
        A representative content type classification.
    """
    return ContentTypeClassification(
        content_type=ContentType.STANDARD_NEWS,
        confidence=ClassificationConfidence.LOW,
        reason_codes=("DEFAULT_STANDARD_NEWS",),
        supporting_signals=(),
        warnings=("LOW_CLASSIFICATION_CONFIDENCE",),
    )


def make_mocked_workflow(
    ingestion: EditorialIngestionResult | None = None,
) -> tuple[
    EditorialClassificationWorkflow,
    EditorialIngestionWorkflow,
    DeterministicContentTypeClassifier,
    EditorialIngestionResult,
    ContentTypeClassification,
]:
    """Create a workflow with configured mock dependencies.

    Args:
        ingestion: Ingestion result to use, or None for a default result.

    Returns:
        The workflow, dependencies, and configured results.
    """
    ingestion_result = ingestion or make_ingestion()
    classification = make_classification()
    ingestion_workflow = create_autospec(
        EditorialIngestionWorkflow, instance=True
    )
    classifier = create_autospec(
        DeterministicContentTypeClassifier, instance=True
    )
    ingestion_workflow.process.return_value = ingestion_result
    classifier.classify.return_value = classification
    workflow = EditorialClassificationWorkflow(
        ingestion_workflow=ingestion_workflow,
        classifier=classifier,
    )
    return (
        workflow,
        ingestion_workflow,
        classifier,
        ingestion_result,
        classification,
    )


def test_valid_raw_input_returns_result_with_default_dependencies() -> None:
    """Process valid raw input using default workflow dependencies."""
    workflow = EditorialClassificationWorkflow()

    result = workflow.process(**SOURCE_FIELDS, user_instruction=None)

    assert isinstance(workflow.ingestion_workflow, EditorialIngestionWorkflow)
    assert isinstance(workflow.classifier, DeterministicContentTypeClassifier)
    assert isinstance(result, EditorialClassificationResult)
    assert isinstance(result.ingestion, EditorialIngestionResult)
    assert isinstance(result.classification, ContentTypeClassification)


def test_injected_dependencies_are_used_once_in_order() -> None:
    """Store and call injected dependencies once in required order."""
    workflow, ingestion_workflow, classifier, ingestion, classification = (
        make_mocked_workflow()
    )
    calls = Mock()
    calls.attach_mock(ingestion_workflow, "ingestion")
    calls.attach_mock(classifier, "classification")
    instruction = "rewrite"

    result = workflow.process(
        **SOURCE_FIELDS,
        user_instruction=instruction,
    )

    assert workflow.ingestion_workflow is ingestion_workflow
    assert workflow.classifier is classifier
    assert result.ingestion is ingestion
    assert result.classification is classification
    assert calls.mock_calls == [
        call.ingestion.process(**SOURCE_FIELDS),
        call.classification.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            user_instruction=instruction,
        ),
    ]


def test_source_validation_error_propagates_unchanged() -> None:
    """Propagate source validation errors without classification."""
    workflow, ingestion_workflow, classifier, *_ = make_mocked_workflow()
    expected = SourceValidationError(("MISSING_TITLE",))
    ingestion_workflow.process.side_effect = expected

    with pytest.raises(SourceValidationError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is expected
    ingestion_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    assert classifier.mock_calls == []


def test_ingestion_failure_propagates_unchanged() -> None:
    """Propagate general ingestion failures without classification."""
    workflow, ingestion_workflow, classifier, *_ = make_mocked_workflow()
    expected = RuntimeError("ingestion failed")
    ingestion_workflow.process.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is expected
    ingestion_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    assert classifier.mock_calls == []


def test_classifier_failure_propagates_unchanged() -> None:
    """Propagate classifier failures after one ingestion call."""
    workflow, ingestion_workflow, classifier, ingestion, _ = (
        make_mocked_workflow()
    )
    expected = RuntimeError("classification failed")
    classifier.classify.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS, user_instruction="explain")

    assert raised.value is expected
    ingestion_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    classifier.classify.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        user_instruction="explain",
    )


def test_classification_runs_when_generation_is_not_allowed() -> None:
    """Classify ingestion results that do not permit generation."""
    ingestion = make_ingestion(generation_allowed=False)
    workflow, _, classifier, _, classification = make_mocked_workflow(
        ingestion
    )

    result = workflow.process(**SOURCE_FIELDS)

    classifier.classify.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        user_instruction=None,
    )
    assert result.classification is classification


def test_result_model_is_immutable() -> None:
    """Prevent editorial classification result fields from reassignment."""
    ingestion = make_ingestion()
    result = EditorialClassificationResult(
        ingestion=ingestion,
        classification=make_classification(),
    )

    with pytest.raises(FrozenInstanceError):
        result.ingestion = ingestion  # type: ignore[misc]

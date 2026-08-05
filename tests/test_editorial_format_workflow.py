"""Tests for the additive editorial format workflow."""

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
from src.formatting.deterministic_editorial_format_classifier import (
    DeterministicEditorialFormatClassifier,
)
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.intake.normalized_source import NormalizedSource
from src.intake.source_intake import SourceValidationError
from src.workflows.editorial_classification_result import (
    EditorialClassificationResult,
)
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.editorial_format_result import EditorialFormatResult
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_ingestion_result import EditorialIngestionResult


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
    *,
    generation_allowed: bool = True,
) -> EditorialClassificationResult:
    """Create a complete existing classification workflow result."""
    source = NormalizedSource("Headline", "Article body", "News Agency")
    assessment = SourceRiskAssessment(
        SourceStatus.IDENTIFIED,
        VerificationStatus.SOURCE_PROVIDED,
        RiskLevel.LOW,
        (),
        (),
        False,
        False,
        generation_allowed,
        ("SOURCE_OK",),
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
        ContentType.STANDARD_NEWS,
        ClassificationConfidence.MEDIUM,
        ("DEFAULT_STANDARD_NEWS",),
        (),
        (),
    )
    return EditorialClassificationResult(ingestion, classification)


def make_format_classification() -> EditorialFormatClassification:
    """Create a representative editorial format classification."""
    return EditorialFormatClassification(
        EditorialFormat.STANDARD_NEWS,
        EditorialFormatConfidence.MEDIUM,
        ("DEFAULT_STANDARD_NEWS_FORMAT",),
        ("EXISTING_CONTENT_TYPE_FALLBACK",),
        (),
    )


def make_mocked_workflow(
    *,
    generation_allowed: bool = True,
) -> tuple[
    EditorialFormatWorkflow,
    EditorialClassificationWorkflow,
    DeterministicEditorialFormatClassifier,
    EditorialClassificationResult,
    EditorialFormatClassification,
]:
    """Create a format workflow with configured mock dependencies."""
    classification_result = make_classification_result(
        generation_allowed=generation_allowed
    )
    format_classification = make_format_classification()
    classification_workflow = create_autospec(
        EditorialClassificationWorkflow, instance=True
    )
    format_classifier = create_autospec(
        DeterministicEditorialFormatClassifier, instance=True
    )
    classification_workflow.process.return_value = classification_result
    format_classifier.classify.return_value = format_classification
    workflow = EditorialFormatWorkflow(
        classification_workflow=classification_workflow,
        format_classifier=format_classifier,
    )
    return (
        workflow,
        classification_workflow,
        format_classifier,
        classification_result,
        format_classification,
    )


def test_valid_input_returns_result_with_default_dependencies() -> None:
    """Process valid raw input using default additive dependencies."""
    workflow = EditorialFormatWorkflow()

    result = workflow.process(**SOURCE_FIELDS)

    assert isinstance(
        workflow.classification_workflow,
        EditorialClassificationWorkflow,
    )
    assert isinstance(
        workflow.format_classifier,
        DeterministicEditorialFormatClassifier,
    )
    assert isinstance(result, EditorialFormatResult)
    assert isinstance(result.classification_result, EditorialClassificationResult)
    assert isinstance(
        result.format_classification,
        EditorialFormatClassification,
    )


def test_injected_dependencies_are_used_once_in_order() -> None:
    """Store injected dependencies and call each exactly once in order."""
    workflow, upstream, classifier, classification_result, format_result = (
        make_mocked_workflow()
    )
    ingestion = classification_result.ingestion
    calls = Mock()
    calls.attach_mock(upstream, "classification")
    calls.attach_mock(classifier, "format")

    result = workflow.process(
        **SOURCE_FIELDS,
        user_instruction="اكتب خبر خدمي",
    )

    assert workflow.classification_workflow is upstream
    assert workflow.format_classifier is classifier
    assert result.classification_result is classification_result
    assert result.format_classification is format_result
    assert calls.mock_calls == [
        call.classification.process(
            **SOURCE_FIELDS,
            user_instruction="اكتب خبر خدمي",
        ),
        call.format.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification_result.classification,
            user_instruction="اكتب خبر خدمي",
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
    """Propagate upstream failures without calling format classification."""
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


def test_format_classifier_failure_propagates_unchanged() -> None:
    """Propagate format classifier failures after exactly one upstream call."""
    workflow, upstream, classifier, classification_result, _ = (
        make_mocked_workflow()
    )
    ingestion = classification_result.ingestion
    expected = RuntimeError("format classification failed")
    classifier.classify.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    classifier.classify.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        content_classification=classification_result.classification,
        user_instruction=None,
    )


def test_format_classification_runs_when_generation_is_blocked() -> None:
    """Continue additive format analysis when generation is not allowed."""
    workflow, _, classifier, classification_result, format_result = (
        make_mocked_workflow(generation_allowed=False)
    )
    ingestion = classification_result.ingestion

    result = workflow.process(**SOURCE_FIELDS)

    classifier.classify.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        content_classification=classification_result.classification,
        user_instruction=None,
    )
    assert result.format_classification is format_result


def test_result_model_is_immutable() -> None:
    """Prevent additive editorial format result fields from reassignment."""
    classification_result = make_classification_result()
    format_result = make_format_classification()
    result = EditorialFormatResult(classification_result, format_result)

    with pytest.raises(FrozenInstanceError):
        result.format_classification = format_result  # type: ignore[misc]

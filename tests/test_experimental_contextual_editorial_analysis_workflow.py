"""Tests for experimental context-aware editorial analysis orchestration."""

from dataclasses import FrozenInstanceError
from unittest.mock import Mock, call, create_autospec

import pytest

from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.formatting.deterministic_editorial_format_classifier import (
    DeterministicEditorialFormatClassifier,
)
from src.intent.deterministic_reader_intent_classifier_v2 import (
    DeterministicReaderIntentClassifierV2,
)
from src.intake.source_intake import SourceValidationError
from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.experimental_contextual_editorial_analysis_result import (
    ExperimentalContextualEditorialAnalysisResult,
)
from src.workflows.experimental_contextual_editorial_analysis_workflow import (
    ExperimentalContextualEditorialAnalysisWorkflow,
)


SOURCE_FIELDS = {
    "title": "ويشير تحليل إلى نمو تقنية البطاريات الصلبة",
    "body": "قد تسهم التقنية في خفض الأسعار بما يؤدي إلى زيادة الطلب.",
    "source_name": "Technology Source",
    "source_url": "https://example.com/technology",
    "published_at": None,
    "language": "ar",
    "country": None,
    "author": None,
    "images": (),
    "attachments": (),
    "category": None,
    "tags": (),
}


def make_dependency_results() -> tuple[object, ...]:
    """Create real dependency outputs for isolated orchestration mocks."""
    classification = EditorialClassificationWorkflow().process(**SOURCE_FIELDS)
    ingestion = classification.ingestion
    evidence = DeterministicContextualEvidenceEngine().analyze(
        source=ingestion.source,
        user_instruction=None,
    )
    topic = DeterministicTopicClassifier().classify(
        source=ingestion.source,
        facts=ingestion.facts,
        assessment=ingestion.assessment,
        content_classification=classification.classification,
        user_instruction=None,
        contextual_evidence=evidence,
    )
    editorial_format = DeterministicEditorialFormatClassifier().classify(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        content_classification=classification.classification,
        user_instruction=None,
        contextual_evidence=evidence,
    )
    intent = DeterministicReaderIntentClassifierV2().classify(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        topic_classification=topic,
        format_classification=editorial_format,
        user_instruction=None,
    )
    return classification, evidence, topic, editorial_format, intent


def make_workflow() -> tuple[object, ...]:
    """Create configured autospec dependencies and their exact results."""
    results = make_dependency_results()
    upstream = create_autospec(EditorialClassificationWorkflow, instance=True)
    evidence_engine = create_autospec(
        DeterministicContextualEvidenceEngine, instance=True
    )
    topic = create_autospec(DeterministicTopicClassifier, instance=True)
    editorial_format = create_autospec(
        DeterministicEditorialFormatClassifier, instance=True
    )
    intent = create_autospec(DeterministicReaderIntentClassifierV2, instance=True)
    for dependency, result, method in (
        (upstream, results[0], "process"),
        (evidence_engine, results[1], "analyze"),
        (topic, results[2], "classify"),
        (editorial_format, results[3], "classify"),
        (intent, results[4], "classify"),
    ):
        getattr(dependency, method).return_value = result
    workflow = ExperimentalContextualEditorialAnalysisWorkflow(
        upstream,
        evidence_engine,
        topic,
        editorial_format,
        intent,
    )
    return workflow, upstream, evidence_engine, topic, editorial_format, intent, *results


def test_valid_input_returns_result_and_default_dependencies() -> None:
    """Create all defaults and return the complete experimental result."""
    workflow = ExperimentalContextualEditorialAnalysisWorkflow()

    result = workflow.process(**SOURCE_FIELDS)

    assert isinstance(result, ExperimentalContextualEditorialAnalysisResult)
    assert isinstance(workflow.classification_workflow, EditorialClassificationWorkflow)
    assert isinstance(workflow.evidence_engine, DeterministicContextualEvidenceEngine)
    assert isinstance(workflow.topic_classifier, DeterministicTopicClassifier)
    assert isinstance(workflow.format_classifier, DeterministicEditorialFormatClassifier)
    assert isinstance(workflow.intent_classifier, DeterministicReaderIntentClassifierV2)


def test_injected_dependencies_run_once_in_exact_order() -> None:
    """Use injected dependencies and forward exact shared intermediate results."""
    (
        workflow,
        upstream,
        engine,
        topic_classifier,
        format_classifier,
        intent_classifier,
        classification,
        evidence,
        topic,
        editorial_format,
        intent,
    ) = make_workflow()
    calls = Mock()
    for dependency, name in (
        (upstream, "classification"),
        (engine, "evidence"),
        (topic_classifier, "topic"),
        (format_classifier, "format"),
        (intent_classifier, "intent"),
    ):
        calls.attach_mock(dependency, name)
    instruction = "اشرح الأثر"

    result = workflow.process(**SOURCE_FIELDS, user_instruction=instruction)

    ingestion = classification.ingestion
    assert result.classification_result is classification
    assert result.contextual_evidence is evidence
    assert result.topic_classification is topic
    assert result.format_classification is editorial_format
    assert result.reader_intent_classification is intent
    assert calls.mock_calls == [
        call.classification.process(**SOURCE_FIELDS, user_instruction=instruction),
        call.evidence.analyze(source=ingestion.source, user_instruction=instruction),
        call.topic.classify(
            source=ingestion.source,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
            content_classification=classification.classification,
            user_instruction=instruction,
            contextual_evidence=evidence,
        ),
        call.format.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification.classification,
            user_instruction=instruction,
            contextual_evidence=evidence,
        ),
        call.intent.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            topic_classification=topic,
            format_classification=editorial_format,
            user_instruction=instruction,
        ),
    ]


@pytest.mark.parametrize(
    ("stage", "failure"),
    (
        (0, SourceValidationError(("MISSING_TITLE",))),
        (0, RuntimeError("classification failed")),
        (1, RuntimeError("evidence failed")),
        (2, RuntimeError("topic failed")),
        (3, RuntimeError("format failed")),
        (4, RuntimeError("intent failed")),
    ),
)
def test_errors_propagate_unchanged_and_stop_processing(
    stage: int,
    failure: Exception,
) -> None:
    """Propagate every failure unchanged without later dependency calls."""
    workflow_data = make_workflow()
    workflow = workflow_data[0]
    dependencies = workflow_data[1:6]
    methods = ("process", "analyze", "classify", "classify", "classify")
    getattr(dependencies[stage], methods[stage]).side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    for index, (dependency, method) in enumerate(zip(dependencies, methods)):
        assert getattr(dependency, method).call_count == (1 if index <= stage else 0)


def test_result_is_immutable() -> None:
    """Prevent reassignment of result model fields."""
    result = ExperimentalContextualEditorialAnalysisResult(*make_dependency_results())

    with pytest.raises(FrozenInstanceError):
        result.contextual_evidence = result.contextual_evidence  # type: ignore[misc]

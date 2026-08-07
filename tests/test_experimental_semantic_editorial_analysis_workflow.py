"""Tests for experimental semantic-aware editorial analysis orchestration."""

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
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)
from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.experimental_semantic_editorial_analysis_result import (
    ExperimentalSemanticEditorialAnalysisResult,
)
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


SOURCE_FIELDS = {
    "title": "هجمات الفدية الإلكترونية تستهدف المؤسسات المالية",
    "body": "حذر خبراء الأمن السيبراني الشركات بضرورة تحديث برامج الحماية.",
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


def make_results() -> tuple[object, ...]:
    """Create real ordered dependency outputs."""
    workflow = ExperimentalSemanticEditorialAnalysisWorkflow()
    result = workflow.process(**SOURCE_FIELDS)
    return (
        result.classification_result,
        result.contextual_evidence,
        result.semantic_evidence,
        result.topic_classification,
        result.format_classification,
        result.reader_intent_classification,
    )


def make_workflow() -> tuple[object, ...]:
    """Create configured dependency autospecs and exact outputs."""
    results = make_results()
    dependencies = (
        create_autospec(EditorialClassificationWorkflow, instance=True),
        create_autospec(DeterministicContextualEvidenceEngine, instance=True),
        create_autospec(DeterministicCompositionalSemanticEngine, instance=True),
        create_autospec(DeterministicTopicClassifier, instance=True),
        create_autospec(DeterministicEditorialFormatClassifier, instance=True),
        create_autospec(DeterministicReaderIntentClassifierV2, instance=True),
    )
    for dependency, result, method in zip(
        dependencies,
        results,
        ("process", "analyze", "compose", "classify", "classify", "classify"),
    ):
        getattr(dependency, method).return_value = result
    workflow = ExperimentalSemanticEditorialAnalysisWorkflow(*dependencies)
    return workflow, *dependencies, *results


def test_valid_input_returns_result_and_default_dependencies() -> None:
    """Create all defaults and return the complete semantic result."""
    workflow = ExperimentalSemanticEditorialAnalysisWorkflow()
    result = workflow.process(**SOURCE_FIELDS)

    assert isinstance(result, ExperimentalSemanticEditorialAnalysisResult)
    assert isinstance(workflow.classification_workflow, EditorialClassificationWorkflow)
    assert isinstance(workflow.evidence_engine, DeterministicContextualEvidenceEngine)
    assert isinstance(
        workflow.semantic_engine,
        DeterministicCompositionalSemanticEngine,
    )
    assert isinstance(workflow.topic_classifier, DeterministicTopicClassifier)
    assert isinstance(workflow.format_classifier, DeterministicEditorialFormatClassifier)
    assert isinstance(workflow.intent_classifier, DeterministicReaderIntentClassifierV2)


def test_injected_dependencies_run_once_in_exact_order() -> None:
    """Forward shared evidence and results through all six exact stages."""
    data = make_workflow()
    workflow = data[0]
    upstream, contextual_engine, semantic_engine, topic_engine, format_engine, intent_engine = data[1:7]
    classification, contextual, semantic, topic, editorial_format, intent = data[7:]
    calls = Mock()
    for dependency, name in zip(
        data[1:7],
        ("classification", "contextual", "semantic", "topic", "format", "intent"),
    ):
        calls.attach_mock(dependency, name)
    instruction = "ركز على الإجراء"

    result = workflow.process(**SOURCE_FIELDS, user_instruction=instruction)
    ingestion = classification.ingestion

    assert result.classification_result is classification
    assert result.contextual_evidence is contextual
    assert result.semantic_evidence is semantic
    assert result.topic_classification is topic
    assert result.format_classification is editorial_format
    assert result.reader_intent_classification is intent
    assert calls.mock_calls == [
        call.classification.process(**SOURCE_FIELDS, user_instruction=instruction),
        call.contextual.analyze(source=ingestion.source, user_instruction=instruction),
        call.semantic.compose(
            source=ingestion.source,
            contextual_evidence=contextual,
        ),
        call.topic.classify(
            source=ingestion.source,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
            content_classification=classification.classification,
            user_instruction=instruction,
            contextual_evidence=contextual,
            semantic_evidence=semantic,
        ),
        call.format.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification.classification,
            user_instruction=instruction,
            contextual_evidence=contextual,
            semantic_evidence=semantic,
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
        (1, RuntimeError("contextual failed")),
        (2, RuntimeError("semantic failed")),
        (3, RuntimeError("topic failed")),
        (4, RuntimeError("format failed")),
        (5, RuntimeError("intent failed")),
    ),
)
def test_errors_propagate_unchanged_and_stop_processing(
    stage: int,
    failure: Exception,
) -> None:
    """Propagate every dependency failure and avoid later calls."""
    data = make_workflow()
    workflow = data[0]
    dependencies = data[1:7]
    methods = ("process", "analyze", "compose", "classify", "classify", "classify")
    getattr(dependencies[stage], methods[stage]).side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    for index, (dependency, method) in enumerate(zip(dependencies, methods)):
        assert getattr(dependency, method).call_count == (1 if index <= stage else 0)


def test_result_is_immutable() -> None:
    """Prevent reassignment of every workflow result field."""
    result = ExperimentalSemanticEditorialAnalysisResult(*make_results())

    with pytest.raises(FrozenInstanceError):
        result.semantic_evidence = result.semantic_evidence  # type: ignore[misc]

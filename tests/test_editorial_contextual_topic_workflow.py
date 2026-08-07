"""Tests for the experimental context-aware topic workflow."""

from dataclasses import FrozenInstanceError
from unittest.mock import Mock, call, create_autospec

import pytest

from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.intake.source_intake import SourceValidationError
from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier
from src.topic.topic_classification import TopicClassification
from src.workflows.editorial_classification_result import (
    EditorialClassificationResult,
)
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.editorial_contextual_topic_result import (
    EditorialContextualTopicResult,
)
from src.workflows.editorial_contextual_topic_workflow import (
    EditorialContextualTopicWorkflow,
)


SOURCE_FIELDS = {
    "title": "أعلن فريق دولي من علماء الفلك اكتشاف كوكب",
    "body": "قال المرصد إن الكوكب خارج المجموعة الشمسية.",
    "source_name": "Science Source",
    "source_url": "https://example.com/science",
    "published_at": None,
    "language": "ar",
    "country": None,
    "author": None,
    "images": (),
    "attachments": (),
    "category": None,
    "tags": (),
}


def make_dependency_results() -> tuple[
    EditorialClassificationResult,
    ContextualEvidence,
    TopicClassification,
]:
    """Create real immutable dependency results for orchestration tests."""
    classification = EditorialClassificationWorkflow().process(**SOURCE_FIELDS)
    ingestion = classification.ingestion
    evidence = DeterministicContextualEvidenceEngine().analyze(
        source=ingestion.source,
        user_instruction="ركز على السياق العلمي",
    )
    topic = DeterministicTopicClassifier().classify(
        source=ingestion.source,
        facts=ingestion.facts,
        assessment=ingestion.assessment,
        content_classification=classification.classification,
        user_instruction="ركز على السياق العلمي",
        contextual_evidence=evidence,
    )
    return classification, evidence, topic


def make_workflow() -> tuple[
    EditorialContextualTopicWorkflow,
    Mock,
    Mock,
    Mock,
    EditorialClassificationResult,
    ContextualEvidence,
    TopicClassification,
]:
    """Create a workflow with configured dependency autospecs."""
    classification, evidence, topic = make_dependency_results()
    upstream = create_autospec(EditorialClassificationWorkflow, instance=True)
    engine = create_autospec(DeterministicContextualEvidenceEngine, instance=True)
    classifier = create_autospec(DeterministicTopicClassifier, instance=True)
    upstream.process.return_value = classification
    engine.analyze.return_value = evidence
    classifier.classify.return_value = topic
    workflow = EditorialContextualTopicWorkflow(upstream, engine, classifier)
    return workflow, upstream, engine, classifier, classification, evidence, topic


def test_valid_input_returns_result_with_default_dependencies() -> None:
    """Create defaults and return all three exact result types for valid input."""
    workflow = EditorialContextualTopicWorkflow()

    result = workflow.process(**SOURCE_FIELDS)

    assert isinstance(workflow.classification_workflow, EditorialClassificationWorkflow)
    assert isinstance(workflow.evidence_engine, DeterministicContextualEvidenceEngine)
    assert isinstance(workflow.topic_classifier, DeterministicTopicClassifier)
    assert isinstance(result, EditorialContextualTopicResult)
    assert isinstance(result.classification_result, EditorialClassificationResult)
    assert isinstance(result.contextual_evidence, ContextualEvidence)
    assert isinstance(result.topic_classification, TopicClassification)


def test_dependencies_are_stored_and_called_once_in_order() -> None:
    """Forward exact upstream values and context in the required sequence."""
    workflow, upstream, engine, classifier, classification, evidence, topic = (
        make_workflow()
    )
    calls = Mock()
    calls.attach_mock(upstream, "classification")
    calls.attach_mock(engine, "evidence")
    calls.attach_mock(classifier, "topic")
    instruction = "ركز على السياق العلمي"

    result = workflow.process(**SOURCE_FIELDS, user_instruction=instruction)

    ingestion = classification.ingestion
    assert workflow.classification_workflow is upstream
    assert workflow.evidence_engine is engine
    assert workflow.topic_classifier is classifier
    assert result.classification_result is classification
    assert result.contextual_evidence is evidence
    assert result.topic_classification is topic
    assert calls.mock_calls == [
        call.classification.process(**SOURCE_FIELDS, user_instruction=instruction),
        call.evidence.analyze(
            source=ingestion.source,
            user_instruction=instruction,
        ),
        call.topic.classify(
            source=ingestion.source,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
            content_classification=classification.classification,
            user_instruction=instruction,
            contextual_evidence=evidence,
        ),
    ]


@pytest.mark.parametrize(
    ("stage", "failure"),
    (
        ("classification", SourceValidationError(("MISSING_TITLE",))),
        ("classification", RuntimeError("classification failed")),
        ("evidence", RuntimeError("evidence failed")),
        ("topic", RuntimeError("topic failed")),
    ),
)
def test_dependency_failures_propagate_unchanged(
    stage: str,
    failure: Exception,
) -> None:
    """Propagate every dependency error and stop subsequent processing."""
    workflow, upstream, engine, classifier, *_ = make_workflow()
    dependency = {
        "classification": upstream.process,
        "evidence": engine.analyze,
        "topic": classifier.classify,
    }[stage]
    dependency.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    upstream.process.assert_called_once()
    assert engine.analyze.call_count == (0 if stage == "classification" else 1)
    assert classifier.classify.call_count == (1 if stage == "topic" else 0)


def test_result_model_is_immutable() -> None:
    """Prevent reassignment of every result field."""
    classification, evidence, topic = make_dependency_results()
    result = EditorialContextualTopicResult(classification, evidence, topic)

    with pytest.raises(FrozenInstanceError):
        result.topic_classification = topic  # type: ignore[misc]

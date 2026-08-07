"""Tests for the experimental semantic-aware topic workflow."""

from dataclasses import FrozenInstanceError
from unittest.mock import Mock, call, create_autospec

import pytest

from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.intake.source_intake import SourceValidationError
from src.semantics.compositional_semantic_evidence import (
    CompositionalSemanticEvidence,
)
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)
from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier
from src.topic.topic_classification import TopicClassification
from src.workflows.editorial_classification_result import (
    EditorialClassificationResult,
)
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.editorial_semantic_topic_result import (
    EditorialSemanticTopicResult,
)
from src.workflows.editorial_semantic_topic_workflow import (
    EditorialSemanticTopicWorkflow,
)


SOURCE_FIELDS = {
    "title": "الذكاء الاصطناعي يساعد في تشخيص الأورام",
    "body": "طور فريق بحثي خوارزمية لتحليل الصور الطبية.",
    "source_name": "Science Source",
    "source_url": "https://example.com/health",
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
    CompositionalSemanticEvidence,
    TopicClassification,
]:
    """Create real immutable outputs for orchestration tests."""
    classification = EditorialClassificationWorkflow().process(**SOURCE_FIELDS)
    ingestion = classification.ingestion
    contextual = DeterministicContextualEvidenceEngine().analyze(
        source=ingestion.source,
        user_instruction=None,
    )
    semantic = DeterministicCompositionalSemanticEngine().compose(
        source=ingestion.source,
        contextual_evidence=contextual,
    )
    topic = DeterministicTopicClassifier().classify(
        source=ingestion.source,
        facts=ingestion.facts,
        assessment=ingestion.assessment,
        content_classification=classification.classification,
        user_instruction=None,
        contextual_evidence=contextual,
        semantic_evidence=semantic,
    )
    return classification, contextual, semantic, topic


def make_workflow() -> tuple[EditorialSemanticTopicWorkflow, tuple[Mock, ...]]:
    """Create a workflow with configured dependency autospecs."""
    classification, contextual, semantic, topic = make_dependency_results()
    upstream = create_autospec(EditorialClassificationWorkflow, instance=True)
    evidence_engine = create_autospec(
        DeterministicContextualEvidenceEngine,
        instance=True,
    )
    semantic_engine = create_autospec(
        DeterministicCompositionalSemanticEngine,
        instance=True,
    )
    classifier = create_autospec(DeterministicTopicClassifier, instance=True)
    upstream.process.return_value = classification
    evidence_engine.analyze.return_value = contextual
    semantic_engine.compose.return_value = semantic
    classifier.classify.return_value = topic
    workflow = EditorialSemanticTopicWorkflow(
        upstream,
        evidence_engine,
        semantic_engine,
        classifier,
    )
    return workflow, (
        upstream,
        evidence_engine,
        semantic_engine,
        classifier,
        classification,
        contextual,
        semantic,
        topic,
    )


def test_defaults_create_valid_semantic_topic_result() -> None:
    """Create every default and return the exact four result layers."""
    workflow = EditorialSemanticTopicWorkflow()

    result = workflow.process(**SOURCE_FIELDS)

    assert isinstance(workflow.classification_workflow, EditorialClassificationWorkflow)
    assert isinstance(workflow.evidence_engine, DeterministicContextualEvidenceEngine)
    assert isinstance(
        workflow.semantic_engine,
        DeterministicCompositionalSemanticEngine,
    )
    assert isinstance(workflow.topic_classifier, DeterministicTopicClassifier)
    assert isinstance(result, EditorialSemanticTopicResult)
    assert isinstance(result.classification_result, EditorialClassificationResult)
    assert isinstance(result.contextual_evidence, ContextualEvidence)
    assert isinstance(result.semantic_evidence, CompositionalSemanticEvidence)
    assert isinstance(result.topic_classification, TopicClassification)


def test_dependencies_are_stored_and_called_once_in_exact_order() -> None:
    """Forward exact identities through all four required stages."""
    workflow, dependencies = make_workflow()
    (
        upstream,
        evidence_engine,
        semantic_engine,
        classifier,
        classification,
        contextual,
        semantic,
        topic,
    ) = dependencies
    calls = Mock()
    calls.attach_mock(upstream, "classification")
    calls.attach_mock(evidence_engine, "contextual")
    calls.attach_mock(semantic_engine, "semantic")
    calls.attach_mock(classifier, "topic")
    instruction = "ركز على الموضوع الطبي"

    result = workflow.process(**SOURCE_FIELDS, user_instruction=instruction)

    ingestion = classification.ingestion
    assert workflow.classification_workflow is upstream
    assert workflow.evidence_engine is evidence_engine
    assert workflow.semantic_engine is semantic_engine
    assert workflow.topic_classifier is classifier
    assert result.classification_result is classification
    assert result.contextual_evidence is contextual
    assert result.semantic_evidence is semantic
    assert result.topic_classification is topic
    assert calls.mock_calls == [
        call.classification.process(**SOURCE_FIELDS, user_instruction=instruction),
        call.contextual.analyze(
            source=ingestion.source,
            user_instruction=instruction,
        ),
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
    ]


@pytest.mark.parametrize(
    ("stage", "failure"),
    (
        ("classification", SourceValidationError(("MISSING_TITLE",))),
        ("classification", RuntimeError("classification failed")),
        ("contextual", RuntimeError("contextual failed")),
        ("semantic", RuntimeError("semantic failed")),
        ("topic", RuntimeError("topic failed")),
    ),
)
def test_dependency_failures_propagate_unchanged(
    stage: str,
    failure: Exception,
) -> None:
    """Propagate every failure unchanged and stop later stages."""
    workflow, dependencies = make_workflow()
    upstream, contextual, semantic, topic = dependencies[:4]
    methods = {
        "classification": upstream.process,
        "contextual": contextual.analyze,
        "semantic": semantic.compose,
        "topic": topic.classify,
    }
    methods[stage].side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    expected_calls = {
        "classification": (1, 0, 0, 0),
        "contextual": (1, 1, 0, 0),
        "semantic": (1, 1, 1, 0),
        "topic": (1, 1, 1, 1),
    }[stage]
    assert tuple(method.call_count for method in methods.values()) == expected_calls


def test_result_model_is_immutable() -> None:
    """Prevent reassignment of the immutable workflow result."""
    classification, contextual, semantic, topic = make_dependency_results()
    result = EditorialSemanticTopicResult(
        classification,
        contextual,
        semantic,
        topic,
    )

    with pytest.raises(FrozenInstanceError):
        result.topic_classification = topic  # type: ignore[misc]

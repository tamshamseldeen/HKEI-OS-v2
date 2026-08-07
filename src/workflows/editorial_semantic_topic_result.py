"""Immutable result of experimental semantic-aware topic analysis."""

from dataclasses import dataclass

from src.evidence.contextual_evidence import ContextualEvidence
from src.semantics.compositional_semantic_evidence import (
    CompositionalSemanticEvidence,
)
from src.topic.topic_classification import TopicClassification

from .editorial_classification_result import EditorialClassificationResult


@dataclass(frozen=True)
class EditorialSemanticTopicResult:
    """Store upstream classification, evidence, and semantic-aware topic.

    Attributes:
        classification_result: Existing editorial classification result.
        contextual_evidence: Deterministically extracted contextual evidence.
        semantic_evidence: Deterministically composed semantic evidence.
        topic_classification: Semantic-aware primary topic classification.
    """

    classification_result: EditorialClassificationResult
    contextual_evidence: ContextualEvidence
    semantic_evidence: CompositionalSemanticEvidence
    topic_classification: TopicClassification

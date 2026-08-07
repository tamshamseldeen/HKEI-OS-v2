"""Immutable result of experimental context-aware topic analysis."""

from dataclasses import dataclass

from src.evidence.contextual_evidence import ContextualEvidence
from src.topic.topic_classification import TopicClassification

from .editorial_classification_result import EditorialClassificationResult


@dataclass(frozen=True)
class EditorialContextualTopicResult:
    """Store upstream classification, contextual evidence, and topic output.

    Attributes:
        classification_result: Existing editorial classification result.
        contextual_evidence: Deterministically extracted contextual evidence.
        topic_classification: Context-aware primary topic classification.
    """

    classification_result: EditorialClassificationResult
    contextual_evidence: ContextualEvidence
    topic_classification: TopicClassification

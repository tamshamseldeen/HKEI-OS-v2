"""Immutable result of experimental context-aware editorial analysis."""

from dataclasses import dataclass

from src.evidence.contextual_evidence import ContextualEvidence
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.intent.reader_intent_classification import ReaderIntentClassification
from src.topic.topic_classification import TopicClassification

from .editorial_classification_result import EditorialClassificationResult


@dataclass(frozen=True)
class ExperimentalContextualEditorialAnalysisResult:
    """Store every result from experimental contextual editorial analysis.

    Attributes:
        classification_result: Existing upstream classification result.
        contextual_evidence: Shared contextual editorial evidence.
        topic_classification: Context-aware topic classification.
        format_classification: Context-aware editorial format classification.
        reader_intent_classification: V2 reader-intent classification.
    """

    classification_result: EditorialClassificationResult
    contextual_evidence: ContextualEvidence
    topic_classification: TopicClassification
    format_classification: EditorialFormatClassification
    reader_intent_classification: ReaderIntentClassification

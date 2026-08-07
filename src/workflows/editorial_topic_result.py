"""Immutable result of additive editorial topic classification."""

from dataclasses import dataclass

from src.topic.topic_classification import TopicClassification

from .editorial_classification_result import EditorialClassificationResult


@dataclass(frozen=True)
class EditorialTopicResult:
    """Represent existing content and additive topic classification.

    Attributes:
        classification_result: Existing authoritative classification result.
        topic_classification: Additional primary topic classification.
    """

    classification_result: EditorialClassificationResult
    topic_classification: TopicClassification

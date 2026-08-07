"""Immutable primary topic classification model."""

from dataclasses import dataclass

from .topic import Topic
from .topic_confidence import TopicConfidence


@dataclass(frozen=True)
class TopicClassification:
    """Represent one primary topic classification.

    Attributes:
        topic: Primary subject of the source material.
        confidence: Confidence in the assigned topic.
        reason_codes: Stable codes explaining the classification.
        supporting_signals: Signals supporting the classification.
        warnings: Warnings associated with the classification.
    """

    topic: Topic
    confidence: TopicConfidence
    reason_codes: tuple[str, ...]
    supporting_signals: tuple[str, ...]
    warnings: tuple[str, ...]

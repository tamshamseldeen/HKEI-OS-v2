"""Immutable editorial content type classification model."""

from dataclasses import dataclass

from .classification_confidence import ClassificationConfidence
from .content_type import ContentType


@dataclass(frozen=True)
class ContentTypeClassification:
    """Represent an editorial content type classification.

    Attributes:
        content_type: Primary editorial content type.
        confidence: Confidence in the assigned content type.
        reason_codes: Stable codes explaining the classification.
        supporting_signals: Signals supporting the classification.
        warnings: Warnings associated with the classification.
    """

    content_type: ContentType
    confidence: ClassificationConfidence
    reason_codes: tuple[str, ...]
    supporting_signals: tuple[str, ...]
    warnings: tuple[str, ...]

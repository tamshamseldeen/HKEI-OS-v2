"""Immutable independent editorial format classification model."""

from dataclasses import dataclass

from .editorial_format import EditorialFormat
from .editorial_format_confidence import EditorialFormatConfidence


@dataclass(frozen=True)
class EditorialFormatClassification:
    """Represent one primary editorial format classification.

    Attributes:
        editorial_format: Primary editorial structure and presentation format.
        confidence: Confidence in the assigned editorial format.
        reason_codes: Stable codes explaining the classification.
        supporting_signals: Signals supporting the classification.
        warnings: Warnings associated with the classification.
    """

    editorial_format: EditorialFormat
    confidence: EditorialFormatConfidence
    reason_codes: tuple[str, ...]
    supporting_signals: tuple[str, ...]
    warnings: tuple[str, ...]

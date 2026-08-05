"""Immutable reader intent classification model."""

from dataclasses import dataclass

from .reader_intent import ReaderIntent
from .reader_intent_confidence import ReaderIntentConfidence


@dataclass(frozen=True)
class ReaderIntentClassification:
    """Represent a reader intent classification.

    Attributes:
        reader_intent: Reader's primary editorial need.
        confidence: Confidence in the assigned reader intent.
        reason_codes: Stable codes explaining the classification.
        supporting_signals: Signals supporting the classification.
        warnings: Warnings associated with the classification.
    """

    reader_intent: ReaderIntent
    confidence: ReaderIntentConfidence
    reason_codes: tuple[str, ...]
    supporting_signals: tuple[str, ...]
    warnings: tuple[str, ...]

"""Immutable result of the editorial intent workflow."""

from dataclasses import dataclass

from src.intent.reader_intent_classification import ReaderIntentClassification

from .editorial_classification_result import EditorialClassificationResult


@dataclass(frozen=True)
class EditorialIntentResult:
    """Represent content classification and reader intent results.

    Attributes:
        classification_result: Complete editorial classification result.
        reader_intent: Reader intent classification for the editorial result.
    """

    classification_result: EditorialClassificationResult
    reader_intent: ReaderIntentClassification

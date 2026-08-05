"""Immutable result of additive editorial format classification."""

from dataclasses import dataclass

from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)

from .editorial_classification_result import EditorialClassificationResult


@dataclass(frozen=True)
class EditorialFormatResult:
    """Represent content classification and editorial format analysis.

    Attributes:
        classification_result: Existing authoritative classification result.
        format_classification: Additional editorial format classification.
    """

    classification_result: EditorialClassificationResult
    format_classification: EditorialFormatClassification

"""Classification confidence values."""

from enum import Enum


class ClassificationConfidence(str, Enum):
    """Describe confidence in an editorial content classification."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

"""Reader intent confidence values."""

from enum import Enum


class ReaderIntentConfidence(str, Enum):
    """Describe confidence in a reader intent classification."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

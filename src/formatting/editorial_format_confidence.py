"""Editorial format classification confidence values."""

from enum import Enum


class EditorialFormatConfidence(str, Enum):
    """Describe confidence in an editorial format classification."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

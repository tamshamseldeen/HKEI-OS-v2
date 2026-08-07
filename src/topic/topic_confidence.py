"""Confidence values for deterministic topic classification."""

from enum import Enum


class TopicConfidence(str, Enum):
    """Describe confidence in an assigned primary topic."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

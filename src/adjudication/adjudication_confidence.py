"""Supported semantic adjudication confidence values."""

from enum import Enum


class AdjudicationConfidence(str, Enum):
    """Describe HKEI-owned categorical adjudication confidence."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

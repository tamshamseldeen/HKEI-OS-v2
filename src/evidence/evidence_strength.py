"""Supported contextual editorial evidence strengths."""

from enum import Enum


class EvidenceStrength(Enum):
    """Identify the deterministic strength of one evidence item."""

    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"

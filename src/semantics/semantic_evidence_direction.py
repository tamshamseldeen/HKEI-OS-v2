"""Candidate-relative direction of deterministic semantic evidence."""

from enum import Enum


class SemanticEvidenceDirection(Enum):
    """Describe how semantic evidence affects one candidate."""

    SUPPORT = "SUPPORT"
    SUPPRESS = "SUPPRESS"
    NEUTRAL = "NEUTRAL"
    CONFLICTING = "CONFLICTING"

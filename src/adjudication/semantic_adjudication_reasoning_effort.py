"""Provider-neutral semantic adjudication reasoning effort values."""

from enum import Enum


class SemanticAdjudicationReasoningEffort(str, Enum):
    """Bound portable reasoning effort choices for adjudication providers."""

    MINIMAL = "MINIMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

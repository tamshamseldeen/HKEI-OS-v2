"""Provider-neutral deterministic semantic evidence strength."""

from enum import Enum


class SemanticEvidenceStrength(Enum):
    """Describe semantic evidence quality independently of confidence."""

    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"

"""Candidate-relative deterministic semantic evidence sufficiency."""

from enum import Enum


class SemanticEvidenceSufficiency(Enum):
    """Describe whether semantic evidence resolves one candidate decision."""

    INSUFFICIENT = "INSUFFICIENT"
    PARTIAL = "PARTIAL"
    SUFFICIENT = "SUFFICIENT"
    CONFLICTED = "CONFLICTED"

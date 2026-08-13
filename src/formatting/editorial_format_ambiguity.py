"""Explicit ambiguity values for Editorial Format V2."""

from enum import Enum


class EditorialFormatAmbiguity(str, Enum):
    """Describe competition and evidence ambiguity independently of confidence."""

    CLEAR = "CLEAR"
    COMPETING = "COMPETING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTORY = "CONTRADICTORY"

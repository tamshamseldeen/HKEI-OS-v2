"""Supported contextual editorial evidence levels."""

from enum import Enum


class EvidenceLevel(Enum):
    """Identify the deterministic level of one evidence item."""

    TOKEN = "TOKEN"
    PHRASE = "PHRASE"
    CONTEXT = "CONTEXT"
    STRUCTURAL = "STRUCTURAL"

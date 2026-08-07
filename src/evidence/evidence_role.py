"""Supported contextual editorial evidence roles."""

from enum import Enum


class EvidenceRole(Enum):
    """Identify the editorial role represented by one evidence item."""

    SUBJECT = "SUBJECT"
    ACTOR = "ACTOR"
    ACTION = "ACTION"
    AUTHORITY = "AUTHORITY"
    AFFECTED_AUDIENCE = "AFFECTED_AUDIENCE"
    REQUIREMENT = "REQUIREMENT"
    DEADLINE = "DEADLINE"
    RESULT = "RESULT"
    CONSEQUENCE = "CONSEQUENCE"
    WARNING = "WARNING"
    NUMBER = "NUMBER"
    DATE = "DATE"
    LOCATION = "LOCATION"
    ATTRIBUTION = "ATTRIBUTION"
    CLAIM = "CLAIM"
    PREDICTION = "PREDICTION"
    UNCERTAINTY = "UNCERTAINTY"
    EXPLANATION = "EXPLANATION"
    COMPARISON = "COMPARISON"
    BACKGROUND = "BACKGROUND"
    INTERPRETATION = "INTERPRETATION"

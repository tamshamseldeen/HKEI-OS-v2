"""Structural completeness values for Editorial Format V2 candidates."""

from enum import Enum


class EditorialFormatCompleteness(str, Enum):
    """Describe treatment-profile completeness independently of confidence."""

    INCOMPLETE = "INCOMPLETE"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"

"""Supported source sections for contextual editorial evidence."""

from enum import Enum


class SourceSection(Enum):
    """Identify the source section that produced one evidence item."""

    HEADLINE = "HEADLINE"
    LEAD = "LEAD"
    BODY = "BODY"
    METADATA = "METADATA"
    USER_INSTRUCTION = "USER_INSTRUCTION"

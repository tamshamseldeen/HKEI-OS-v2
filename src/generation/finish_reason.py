"""Normalized LLM generation finish reasons."""

from enum import Enum


class FinishReason(str, Enum):
    """Describe why an LLM generation request finished."""

    COMPLETED = "COMPLETED"
    LENGTH_LIMIT = "LENGTH_LIMIT"
    CONTENT_FILTERED = "CONTENT_FILTERED"
    TOOL_CALL = "TOOL_CALL"
    STOPPED = "STOPPED"
    UNKNOWN = "UNKNOWN"

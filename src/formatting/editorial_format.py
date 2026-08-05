"""Supported primary editorial format values."""

from enum import Enum


class EditorialFormat(str, Enum):
    """Describe how analyzed material should be structured editorially."""

    BREAKING = "BREAKING"
    STANDARD_NEWS = "STANDARD_NEWS"
    SERVICE = "SERVICE"
    GUIDE = "GUIDE"
    EXPLAINER = "EXPLAINER"
    FEATURE = "FEATURE"
    FACT_CHECK = "FACT_CHECK"
    ANALYSIS = "ANALYSIS"
    INTERVIEW = "INTERVIEW"
    PROFILE = "PROFILE"
    RESULT_REPORT = "RESULT_REPORT"
    TREND_UPDATE = "TREND_UPDATE"

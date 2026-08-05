"""Editorial writing mode values."""

from enum import Enum


class WritingMode(str, Enum):
    """Describe the editorial writing treatment for an article."""

    DIRECT_NEWS = "DIRECT_NEWS"
    SERVICE = "SERVICE"
    EXPLAINER = "EXPLAINER"
    FACT_CHECK = "FACT_CHECK"
    HIGH_RISK_CAUTION = "HIGH_RISK_CAUTION"
    RESULT_REPORT = "RESULT_REPORT"
    TREND_UPDATE = "TREND_UPDATE"
    COMPARISON = "COMPARISON"

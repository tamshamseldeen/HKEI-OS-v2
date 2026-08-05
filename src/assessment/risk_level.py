"""Risk level values."""

from enum import Enum


class RiskLevel(str, Enum):
    """Describe the editorial risk level of source material."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

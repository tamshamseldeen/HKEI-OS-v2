"""Supported semantic adjudication scope values."""

from enum import Enum


class AdjudicationScope(str, Enum):
    """Describe which deterministic editorial decisions need adjudication."""

    NOT_REQUIRED = "NOT_REQUIRED"
    TOPIC_REQUIRED = "TOPIC_REQUIRED"
    FORMAT_REQUIRED = "FORMAT_REQUIRED"
    TOPIC_AND_FORMAT_REQUIRED = "TOPIC_AND_FORMAT_REQUIRED"

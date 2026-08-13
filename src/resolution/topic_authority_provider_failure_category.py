"""Sanitized provider failure categories for Topic authority observations."""

from enum import Enum


class TopicAuthorityProviderFailureCategory(str, Enum):
    """Represent bounded provider outcomes without raw exception content."""

    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    INCOMPLETE_RESPONSE = "INCOMPLETE_RESPONSE"

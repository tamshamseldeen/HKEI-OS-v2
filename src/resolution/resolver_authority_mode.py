"""Runtime modes for the limited Topic authority pilot."""

from enum import Enum


class ResolverAuthorityMode(str, Enum):
    """Control whether Resolver output remains shadow-only."""

    SHADOW = "SHADOW"
    LIMITED_TOPIC_AUTHORITY = "LIMITED_TOPIC_AUTHORITY"

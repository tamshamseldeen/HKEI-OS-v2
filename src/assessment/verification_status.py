"""Verification status values."""

from enum import Enum


class VerificationStatus(str, Enum):
    """Describe the verification state of source material."""

    UNVERIFIED = "UNVERIFIED"
    SOURCE_PROVIDED = "SOURCE_PROVIDED"
    OFFICIAL_SOURCE_PROVIDED = "OFFICIAL_SOURCE_PROVIDED"
    MULTIPLE_SOURCES_PROVIDED = "MULTIPLE_SOURCES_PROVIDED"
    VERIFIED_EXTERNALLY = "VERIFIED_EXTERNALLY"

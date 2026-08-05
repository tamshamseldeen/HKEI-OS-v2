"""Source status values."""

from enum import Enum


class SourceStatus(str, Enum):
    """Describe the attribution availability of a source."""

    IDENTIFIED = "IDENTIFIED"
    PARTIALLY_IDENTIFIED = "PARTIALLY_IDENTIFIED"
    UNIDENTIFIED = "UNIDENTIFIED"

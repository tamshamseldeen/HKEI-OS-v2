"""Provider-neutral editorial resolution provenance values."""

from enum import Enum


class EditorialResolutionSource(str, Enum):
    """Identify the source represented by a resolution outcome."""

    DETERMINISTIC_V1 = "DETERMINISTIC_V1"
    FORMAT_V2_SHADOW = "FORMAT_V2_SHADOW"
    ADJUDICATION = "ADJUDICATION"
    FALLBACK = "FALLBACK"
    NONE = "NONE"

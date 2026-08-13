"""Provider-neutral editorial resolution status values."""

from enum import Enum


class EditorialResolutionStatus(str, Enum):
    """Describe the authority outcome for one editorial dimension."""

    DETERMINISTIC_ACCEPTED = "DETERMINISTIC_ACCEPTED"
    ADJUDICATED_ACCEPTED = "ADJUDICATED_ACCEPTED"
    FALLBACK_ACCEPTED = "FALLBACK_ACCEPTED"
    UNRESOLVED = "UNRESOLVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

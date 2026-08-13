"""Immutable stop recommendation for the limited Topic authority pilot."""

from dataclasses import dataclass
from enum import Enum

from .resolver_authority_mode import ResolverAuthorityMode


class TopicAuthorityPilotStopReason(str, Enum):
    """Canonical reasons to recommend the SHADOW kill switch."""

    AUTHORITY_CONTRACT_VIOLATION = "AUTHORITY_CONTRACT_VIOLATION"
    REGRESSION_BUDGET_EXCEEDED = "REGRESSION_BUDGET_EXCEEDED"
    ACCEPTED_CANDIDATE_VIOLATION = "ACCEPTED_CANDIDATE_VIOLATION"
    ACCEPTED_FINGERPRINT_VIOLATION = "ACCEPTED_FINGERPRINT_VIOLATION"
    FORMAT_AUTHORITY_VIOLATION = "FORMAT_AUTHORITY_VIOLATION"
    READER_INTENT_AUTHORITY_VIOLATION = "READER_INTENT_AUTHORITY_VIOLATION"
    OVERRIDE_PRECISION_BELOW_THRESHOLD = "OVERRIDE_PRECISION_BELOW_THRESHOLD"
    CONSECUTIVE_PROVIDER_VALIDATION_FAILURES = "CONSECUTIVE_PROVIDER_VALIDATION_FAILURES"
    PROVIDER_VALIDATION_FAILURE_RATE_EXCEEDED = "PROVIDER_VALIDATION_FAILURE_RATE_EXCEEDED"


@dataclass(frozen=True)
class TopicAuthorityPilotStopDecision:
    """Recommend but never perform a pilot mode change."""

    should_stop: bool
    reasons: tuple[TopicAuthorityPilotStopReason, ...]
    recommended_mode: ResolverAuthorityMode | None

    def __post_init__(self) -> None:
        if not isinstance(self.should_stop, bool):
            raise ValueError("should_stop must be a boolean")
        if not isinstance(self.reasons, tuple) or any(
            not isinstance(item, TopicAuthorityPilotStopReason) for item in self.reasons
        ):
            raise ValueError("reasons must be a tuple of TopicAuthorityPilotStopReason")
        if len(self.reasons) != len(set(self.reasons)):
            raise ValueError("reasons must not contain duplicates")
        if self.should_stop:
            if not self.reasons or self.recommended_mode is not ResolverAuthorityMode.SHADOW:
                raise ValueError("stop decisions require reasons and SHADOW recommendation")
        elif self.reasons or self.recommended_mode is not None:
            raise ValueError("non-stop decisions require no reasons or recommendation")

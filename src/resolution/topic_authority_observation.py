"""Sanitized immutable observation for the limited Topic authority pilot."""

from dataclasses import dataclass

from src.adjudication.adjudication_confidence import AdjudicationConfidence

from .editorial_resolution_source import EditorialResolutionSource
from .editorial_resolution_status import EditorialResolutionStatus
from .editorial_resolution_warning import EditorialResolutionWarning
from .resolver_authority_mode import ResolverAuthorityMode
from .topic_authority_block_reason import TopicAuthorityBlockReason
from .topic_authority_provider_failure_category import TopicAuthorityProviderFailureCategory


@dataclass(frozen=True)
class TopicAuthorityObservation:
    """Expose bounded provenance without source or provider payloads."""

    authority_mode: ResolverAuthorityMode
    authority_applied: bool
    authority_source: EditorialResolutionSource
    resolution_status: EditorialResolutionStatus
    provider_used: bool
    provider_called: bool
    provider_valid: bool
    topic_adjudication_requested: bool
    provider_failure_category: TopicAuthorityProviderFailureCategory | None
    provider_confidence: AdjudicationConfidence | None
    ambiguity_remaining: bool
    review_required: bool
    block_reasons: tuple[TopicAuthorityBlockReason, ...]
    warnings: tuple[EditorialResolutionWarning, ...]
    candidate_compliant: bool
    fingerprint_valid: bool
    decision_fingerprint: str | None

    def __post_init__(self) -> None:
        enum_fields = (
            (self.authority_mode, ResolverAuthorityMode, "authority_mode"),
            (self.authority_source, EditorialResolutionSource, "authority_source"),
            (self.resolution_status, EditorialResolutionStatus, "resolution_status"),
        )
        for value, expected, name in enum_fields:
            if not isinstance(value, expected):
                raise ValueError(f"{name} must be a {expected.__name__}")
        if self.provider_confidence is not None and not isinstance(
            self.provider_confidence, AdjudicationConfidence
        ):
            raise ValueError("provider_confidence must be an AdjudicationConfidence or None")
        for name in (
            "authority_applied", "provider_used", "ambiguity_remaining",
            "provider_called", "provider_valid", "topic_adjudication_requested",
            "review_required", "candidate_compliant", "fingerprint_valid",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a boolean")
        if self.provider_failure_category is not None and not isinstance(
            self.provider_failure_category, TopicAuthorityProviderFailureCategory
        ):
            raise ValueError(
                "provider_failure_category must be a TopicAuthorityProviderFailureCategory or None"
            )
        if not isinstance(self.block_reasons, tuple) or any(
            not isinstance(item, TopicAuthorityBlockReason) for item in self.block_reasons
        ):
            raise ValueError("block_reasons must be a tuple of TopicAuthorityBlockReason")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(item, EditorialResolutionWarning) for item in self.warnings
        ):
            raise ValueError("warnings must be a tuple of EditorialResolutionWarning")
        if len(self.block_reasons) != len(set(self.block_reasons)):
            raise ValueError("block_reasons must not contain duplicates")
        if len(self.warnings) != len(set(self.warnings)):
            raise ValueError("warnings must not contain duplicates")
        if self.authority_applied and self.block_reasons:
            raise ValueError("authority-applied observations require empty block_reasons")
        if self.authority_applied and self.authority_source is not EditorialResolutionSource.ADJUDICATION:
            raise ValueError("authority-applied observations require ADJUDICATION source")
        if self.decision_fingerprint is not None and (
            not isinstance(self.decision_fingerprint, str)
            or not self.decision_fingerprint.strip()
            or self.decision_fingerprint != self.decision_fingerprint.strip()
        ):
            raise ValueError("decision_fingerprint must be a normalized string or None")

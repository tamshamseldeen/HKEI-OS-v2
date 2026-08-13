"""Immutable result model for a future limited Topic authority decision."""

from dataclasses import dataclass

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.topic.topic import Topic

from .editorial_resolution_source import EditorialResolutionSource
from .editorial_resolution_status import EditorialResolutionStatus
from .editorial_resolution_warning import EditorialResolutionWarning
from .topic_authority_block_reason import TopicAuthorityBlockReason


@dataclass(frozen=True)
class TopicAuthorityDecision:
    """Store caller-calculated Topic authority fields without applying them."""

    deterministic_topic: Topic
    resolved_topic: Topic
    authoritative_topic: Topic
    authority_applied: bool
    authority_source: EditorialResolutionSource
    resolution_status: EditorialResolutionStatus
    provider_confidence: AdjudicationConfidence | None
    ambiguity_remaining: bool
    review_required: bool
    warnings: tuple[EditorialResolutionWarning, ...]
    input_fingerprint: str
    block_reasons: tuple[TopicAuthorityBlockReason, ...] = ()

    def __post_init__(self) -> None:
        for name in ("deterministic_topic", "resolved_topic", "authoritative_topic"):
            if not isinstance(getattr(self, name), Topic):
                raise ValueError(f"{name} must be a Topic")
        if not isinstance(self.authority_applied, bool):
            raise ValueError("authority_applied must be a boolean")
        if not isinstance(self.authority_source, EditorialResolutionSource):
            raise ValueError("authority_source must be an EditorialResolutionSource")
        if not isinstance(self.resolution_status, EditorialResolutionStatus):
            raise ValueError("resolution_status must be an EditorialResolutionStatus")
        if self.provider_confidence is not None and not isinstance(
            self.provider_confidence, AdjudicationConfidence
        ):
            raise ValueError("provider_confidence must be an AdjudicationConfidence or None")
        if not isinstance(self.ambiguity_remaining, bool) or not isinstance(self.review_required, bool):
            raise ValueError("ambiguity_remaining and review_required must be booleans")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(item, EditorialResolutionWarning) for item in self.warnings
        ):
            raise ValueError("warnings must be a tuple of EditorialResolutionWarning")
        if len(self.warnings) != len(set(self.warnings)):
            raise ValueError("warnings must not contain duplicates")
        if not isinstance(self.block_reasons, tuple) or any(
            not isinstance(item, TopicAuthorityBlockReason) for item in self.block_reasons
        ):
            raise ValueError("block_reasons must be a tuple of TopicAuthorityBlockReason")
        if len(self.block_reasons) != len(set(self.block_reasons)):
            raise ValueError("block_reasons must not contain duplicates")
        if self.authority_applied and self.block_reasons:
            raise ValueError("authority-applied decisions require empty block_reasons")
        if self.authority_applied and self.authority_source is not EditorialResolutionSource.ADJUDICATION:
            raise ValueError("authority-applied decisions require ADJUDICATION source")
        if self.authority_applied and self.authoritative_topic is not self.resolved_topic:
            raise ValueError("authority-applied decisions require the resolved Topic")
        if not isinstance(self.input_fingerprint, str) or not self.input_fingerprint.strip():
            raise ValueError("input_fingerprint must be a non-empty string")

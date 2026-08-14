"""Public source-free result boundary for the operational Topic canary."""

from dataclasses import dataclass

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.topic.topic import Topic

from .editorial_resolution_source import EditorialResolutionSource
from .editorial_resolution_status import EditorialResolutionStatus
from .editorial_resolution_warning import EditorialResolutionWarning
from .resolver_authority_mode import ResolverAuthorityMode
from .topic_authority_block_reason import TopicAuthorityBlockReason
from .controlled_topic_authority_consumer import TopicAuthorityConsumerRoute


@dataclass(frozen=True)
class SanitizedTopicAuthorityCanaryResult:
    deterministic_topic: Topic
    resolved_topic: Topic | None
    authoritative_topic: Topic
    consumer_topic: Topic
    route: TopicAuthorityConsumerRoute
    authority_mode: ResolverAuthorityMode
    authority_applied: bool
    authority_consumed: bool
    authority_source: EditorialResolutionSource
    consumer_source: EditorialResolutionSource
    resolution_status: EditorialResolutionStatus
    review_required: bool
    ambiguity_remaining: bool
    provider_used: bool
    provider_confidence: AdjudicationConfidence | None
    candidate_compliant: bool
    fingerprint_valid: bool
    block_reasons: tuple[TopicAuthorityBlockReason, ...]
    warnings: tuple[EditorialResolutionWarning, ...]
    stop_recommended: bool

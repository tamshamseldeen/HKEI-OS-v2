from dataclasses import replace

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.resolution import (
    EditorialResolutionSource, EditorialResolutionStatus, ResolverAuthorityMode,
    TopicAuthorityDecision, TopicAuthorityObservation,
)
from src.topic.topic import Topic


def decision(**changes):
    value = TopicAuthorityDecision(
        deterministic_topic=Topic.SCIENCE, resolved_topic=Topic.HEALTH,
        authoritative_topic=Topic.HEALTH, authority_applied=True,
        authority_source=EditorialResolutionSource.ADJUDICATION,
        resolution_status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        provider_confidence=AdjudicationConfidence.HIGH,
        ambiguity_remaining=False, review_required=False, warnings=(),
        input_fingerprint="safe-fingerprint", block_reasons=(),
    )
    return replace(value, **changes)


def observation(**changes):
    value = TopicAuthorityObservation(
        authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        authority_applied=True, authority_source=EditorialResolutionSource.ADJUDICATION,
        resolution_status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        provider_used=True, provider_called=True, provider_valid=True,
        topic_adjudication_requested=True, provider_failure_category=None,
        provider_confidence=AdjudicationConfidence.HIGH, ambiguity_remaining=False,
        review_required=False, block_reasons=(), warnings=(), candidate_compliant=True,
        fingerprint_valid=True, decision_fingerprint="safe-fingerprint",
    )
    return replace(value, **changes)

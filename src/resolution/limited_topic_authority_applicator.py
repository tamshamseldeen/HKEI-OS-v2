"""Pure deterministic applicator for the limited Topic authority pilot."""

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.topic.topic import Topic

from .editorial_resolution_result import EditorialResolutionResult
from .editorial_resolution_source import EditorialResolutionSource
from .editorial_resolution_status import EditorialResolutionStatus
from .limited_topic_authority_config import LimitedTopicAuthorityConfig
from .resolver_authority_mode import ResolverAuthorityMode
from .topic_authority_block_reason import TopicAuthorityBlockReason
from .topic_authority_decision import TopicAuthorityDecision


class LimitedTopicAuthorityApplicator:
    """Decide Topic authority from completed, trusted-domain inputs only."""

    _CONFIDENCE_RANK = {
        AdjudicationConfidence.LOW: 0,
        AdjudicationConfidence.MEDIUM: 1,
        AdjudicationConfidence.HIGH: 2,
    }

    def apply(
        self,
        resolution: EditorialResolutionResult,
        config: LimitedTopicAuthorityConfig,
        candidate_compliant: bool,
        fingerprint_valid: bool,
        response_valid: bool,
        provider_available: bool,
    ) -> TopicAuthorityDecision:
        """Return an immutable decision without side effects or orchestration."""
        if not isinstance(resolution, EditorialResolutionResult):
            raise ValueError("resolution must be an EditorialResolutionResult")
        if not isinstance(config, LimitedTopicAuthorityConfig):
            raise ValueError("config must be a LimitedTopicAuthorityConfig")
        trust_flags = {
            "candidate_compliant": candidate_compliant,
            "fingerprint_valid": fingerprint_valid,
            "response_valid": response_valid,
            "provider_available": provider_available,
        }
        for name, value in trust_flags.items():
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean")

        topic = resolution.topic_resolution
        resolved_topic = topic.value if isinstance(topic.value, Topic) else None
        confidence = self._provider_confidence(topic.confidence, topic.confidence_source)
        reasons: list[TopicAuthorityBlockReason] = []

        if config.authority_mode is ResolverAuthorityMode.SHADOW:
            reasons.append(TopicAuthorityBlockReason.MODE_SHADOW)
        if topic.status is not EditorialResolutionStatus.ADJUDICATED_ACCEPTED:
            reasons.append(TopicAuthorityBlockReason.RESOLUTION_NOT_ADJUDICATED)
        if topic.source is not EditorialResolutionSource.ADJUDICATION:
            reasons.append(TopicAuthorityBlockReason.SOURCE_NOT_ADJUDICATION)
        if config.block_on_review_required and topic.review_required:
            reasons.append(TopicAuthorityBlockReason.REVIEW_REQUIRED)
        if config.block_on_ambiguity and topic.ambiguity:
            reasons.append(TopicAuthorityBlockReason.AMBIGUITY_REMAINS)
        if not self._confidence_is_eligible(confidence, config.minimum_provider_confidence):
            reasons.append(TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW)
        if not fingerprint_valid:
            reasons.append(TopicAuthorityBlockReason.FINGERPRINT_INVALID)
        if not candidate_compliant:
            reasons.append(TopicAuthorityBlockReason.CANDIDATE_INVALID)
        if not response_valid:
            reasons.append(TopicAuthorityBlockReason.RESPONSE_INVALID)
        if not provider_available:
            reasons.append(TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE)

        if not reasons and resolved_topic is resolution.deterministic_topic:
            reasons.append(TopicAuthorityBlockReason.NO_TOPIC_CHANGE)

        block_reasons = tuple(
            reason for reason in TopicAuthorityBlockReason if reason in reasons
        )
        authority_applied = not block_reasons
        return TopicAuthorityDecision(
            deterministic_topic=resolution.deterministic_topic,
            resolved_topic=resolved_topic,
            authoritative_topic=(resolved_topic if authority_applied else resolution.deterministic_topic),
            authority_applied=authority_applied,
            authority_source=(
                EditorialResolutionSource.ADJUDICATION
                if authority_applied
                else EditorialResolutionSource.DETERMINISTIC_V1
            ),
            resolution_status=topic.status,
            provider_confidence=confidence,
            ambiguity_remaining=topic.ambiguity,
            review_required=topic.review_required,
            warnings=topic.warnings,
            input_fingerprint=resolution.input_fingerprint,
            block_reasons=block_reasons,
        )

    @classmethod
    def _confidence_is_eligible(
        cls,
        actual: AdjudicationConfidence | None,
        minimum: AdjudicationConfidence,
    ) -> bool:
        return actual is not None and cls._CONFIDENCE_RANK[actual] >= cls._CONFIDENCE_RANK[minimum]

    @staticmethod
    def _provider_confidence(
        confidence: str | None,
        source: EditorialResolutionSource,
    ) -> AdjudicationConfidence | None:
        if source is not EditorialResolutionSource.ADJUDICATION or confidence is None:
            return None
        try:
            return AdjudicationConfidence(confidence)
        except ValueError:
            return None

"""Fail-closed operational boundary for controlled Topic authority consumption."""

from .controlled_topic_authority_consumer import (
    ControlledTopicAuthorityConsumerAdapter,
    TopicAuthorityConsumerRoute,
)
from .editorial_resolution_source import EditorialResolutionSource
from .editorial_resolution_warning import EditorialResolutionWarning
from .resolver_authority_mode import ResolverAuthorityMode
from .sanitized_topic_authority_canary_result import SanitizedTopicAuthorityCanaryResult
from .topic_authority_decision import TopicAuthorityDecision
from .topic_authority_observation import TopicAuthorityObservation
from .topic_authority_observation_sink import NoOpTopicAuthorityObservationSink, TopicAuthorityObservationSink
from .topic_authority_pilot_stop_decision import TopicAuthorityPilotStopDecision
from .topic_authority_runtime_config import TopicAuthorityRuntimeConfig


class OperationalTopicAuthorityCanary:
    """Record before consumption and expose only a sanitized result."""

    def __init__(self, config=None, sink=None, consumer=None) -> None:
        if config is not None and not isinstance(config, TopicAuthorityRuntimeConfig):
            raise ValueError("config must be a TopicAuthorityRuntimeConfig or None")
        self.config = config or TopicAuthorityRuntimeConfig()
        self.sink: TopicAuthorityObservationSink = sink or NoOpTopicAuthorityObservationSink()
        self.consumer = consumer or ControlledTopicAuthorityConsumerAdapter()

    def execute(
        self,
        decision: TopicAuthorityDecision,
        observation: TopicAuthorityObservation,
        route: TopicAuthorityConsumerRoute = TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH,
        stop_signal: TopicAuthorityPilotStopDecision | None = None,
    ) -> SanitizedTopicAuthorityCanaryResult:
        if not isinstance(decision, TopicAuthorityDecision) or not isinstance(
            observation, TopicAuthorityObservation
        ):
            raise ValueError("decision and observation must use canonical authority models")
        mode = self.config.apply_stop_signal(stop_signal)
        warnings = observation.warnings
        recorded = False
        try:
            self.sink.record(observation)
            recorded = True
        except Exception:
            warning = EditorialResolutionWarning.AUTHORITY_OBSERVATION_FAILED
            warnings = warnings if warning in warnings else warnings + (warning,)
        try:
            consumer = self.consumer.consume(decision.deterministic_topic, decision, route, mode)
        except Exception:
            consumer = None
        consumed = bool(consumer and recorded and consumer.authority_consumed)
        consumer_topic = consumer.consumer_topic if consumed else decision.deterministic_topic
        consumer_source = consumer.source if consumed else EditorialResolutionSource.DETERMINISTIC_V1
        return SanitizedTopicAuthorityCanaryResult(
            deterministic_topic=decision.deterministic_topic,
            resolved_topic=decision.resolved_topic,
            authoritative_topic=decision.authoritative_topic,
            consumer_topic=consumer_topic,
            route=route,
            authority_mode=mode,
            authority_applied=decision.authority_applied,
            authority_consumed=consumed,
            authority_source=decision.authority_source,
            consumer_source=consumer_source,
            resolution_status=decision.resolution_status,
            review_required=decision.review_required,
            ambiguity_remaining=decision.ambiguity_remaining,
            provider_used=observation.provider_used,
            provider_confidence=observation.provider_confidence,
            candidate_compliant=observation.candidate_compliant,
            fingerprint_valid=observation.fingerprint_valid,
            block_reasons=decision.block_reasons,
            warnings=warnings,
            stop_recommended=bool(stop_signal and stop_signal.should_stop),
        )

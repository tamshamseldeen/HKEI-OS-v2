"""Explicit INTERNAL_SINGLE_PATH routing for Topic authority."""

from dataclasses import dataclass
from enum import Enum

from src.topic.topic import Topic

from .editorial_resolution_source import EditorialResolutionSource
from .resolver_authority_mode import ResolverAuthorityMode
from .topic_authority_decision import TopicAuthorityDecision


class TopicAuthorityConsumerRoute(str, Enum):
    NORMAL_PRODUCTION_PATH = "NORMAL_PRODUCTION_PATH"
    INTERNAL_TOPIC_AUTHORITY_CANARY_PATH = "INTERNAL_TOPIC_AUTHORITY_CANARY_PATH"


@dataclass(frozen=True)
class ControlledTopicAuthorityConsumerResult:
    consumer_topic: Topic
    authority_consumed: bool
    source: EditorialResolutionSource


class ControlledTopicAuthorityConsumerAdapter:
    """Consume authority only on the explicit internal route in LIMITED mode."""

    def consume(
        self,
        deterministic_topic: Topic,
        decision: TopicAuthorityDecision,
        route: TopicAuthorityConsumerRoute,
        effective_mode: ResolverAuthorityMode,
    ) -> ControlledTopicAuthorityConsumerResult:
        if not isinstance(deterministic_topic, Topic):
            raise ValueError("deterministic_topic must be a Topic")
        if not isinstance(decision, TopicAuthorityDecision):
            raise ValueError("decision must be a TopicAuthorityDecision")
        if not isinstance(route, TopicAuthorityConsumerRoute):
            raise ValueError("route must be a TopicAuthorityConsumerRoute")
        if not isinstance(effective_mode, ResolverAuthorityMode):
            raise ValueError("effective_mode must be a ResolverAuthorityMode")
        consumed = (
            route is TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH
            and effective_mode is ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
            and decision.authority_applied
        )
        return ControlledTopicAuthorityConsumerResult(
            consumer_topic=decision.authoritative_topic if consumed else deterministic_topic,
            authority_consumed=consumed,
            source=(decision.authority_source if consumed else EditorialResolutionSource.DETERMINISTIC_V1),
        )

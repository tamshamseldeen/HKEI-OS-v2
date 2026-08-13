from dataclasses import fields, replace
import pytest

from src.resolution import (
    ControlledTopicAuthorityConsumerAdapter, EditorialResolutionSource,
    ResolverAuthorityMode, TopicAuthorityBlockReason, TopicAuthorityConsumerRoute,
)
from src.topic.topic import Topic
from tests.topic_authority_operational_fixtures import decision


def consume(route, mode, item=None): return ControlledTopicAuthorityConsumerAdapter().consume(Topic.SCIENCE, item or decision(), route, mode)
def test_default_route_value(): assert TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH.value == "NORMAL_PRODUCTION_PATH"
def test_internal_route_value(): assert TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH.value == "INTERNAL_TOPIC_AUTHORITY_CANARY_PATH"
def test_normal_route_is_deterministic(): assert consume(TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY).consumer_topic is Topic.SCIENCE
def test_normal_route_does_not_consume(): assert not consume(TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY).authority_consumed
def test_internal_shadow_is_deterministic(): assert consume(TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH, ResolverAuthorityMode.SHADOW).consumer_topic is Topic.SCIENCE
def test_internal_limited_consumes(): assert consume(TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY).consumer_topic is Topic.HEALTH
def test_internal_limited_marks_consumed(): assert consume(TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY).authority_consumed
def test_consumed_source_is_adjudication(): assert consume(TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY).source is EditorialResolutionSource.ADJUDICATION
def test_unconsumed_source_is_deterministic(): assert consume(TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY).source is EditorialResolutionSource.DETERMINISTIC_V1
@pytest.mark.parametrize("reason", list(TopicAuthorityBlockReason))
def test_blocked_decision_never_consumed(reason):
    item = replace(decision(), authoritative_topic=Topic.SCIENCE, authority_applied=False, authority_source=EditorialResolutionSource.DETERMINISTIC_V1, block_reasons=(reason,))
    assert not consume(TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, item).authority_consumed
def test_applied_and_consumed_are_distinct():
    item = decision(); result = consume(TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, item)
    assert item.authority_applied and not result.authority_consumed
@pytest.mark.parametrize("bad", [None, "INTERNAL", 1])
def test_invalid_route_fails(bad):
    with pytest.raises(ValueError): consume(bad, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
def test_result_has_topic_only(): assert {f.name for f in fields(type(consume(TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH, ResolverAuthorityMode.SHADOW)))} == {"consumer_topic", "authority_consumed", "source"}

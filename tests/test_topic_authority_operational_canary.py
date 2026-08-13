from dataclasses import asdict, fields, replace
import json
import pytest

from src.resolution import (
    EditorialResolutionWarning, InMemoryTopicAuthorityObservationSink,
    OperationalTopicAuthorityCanary, ResolverAuthorityMode,
    SanitizedTopicAuthorityCanaryResult, TopicAuthorityConsumerRoute,
    TopicAuthorityRuntimeConfig,
)
from src.resolution.topic_authority_pilot_stop_decision import TopicAuthorityPilotStopDecision, TopicAuthorityPilotStopReason
from src.topic.topic import Topic
from tests.topic_authority_operational_fixtures import decision, observation

INTERNAL = TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH

class BrokenSink:
    def record(self, _): raise RuntimeError("raw secret source payload")
class BrokenConsumer:
    def consume(self, *_): raise RuntimeError("unsafe")
def signal(): return TopicAuthorityPilotStopDecision(True, (TopicAuthorityPilotStopReason.AUTHORITY_CONTRACT_VIOLATION,), ResolverAuthorityMode.SHADOW)
def run(mode="SHADOW", route=INTERNAL, sink=None, consumer=None, stop=None, item=None, obs=None):
    return OperationalTopicAuthorityCanary(TopicAuthorityRuntimeConfig(mode), sink, consumer).execute(item or decision(), obs or observation(), route, stop)

def test_default_shadow_prevents_consumption(): assert not run().authority_consumed
def test_unavailable_config_defaults_shadow(): assert OperationalTopicAuthorityCanary().execute(decision(), observation(), INTERNAL).authority_mode is ResolverAuthorityMode.SHADOW
def test_default_shadow_preserves_topic(): assert run().consumer_topic is Topic.SCIENCE
def test_explicit_limited_consumes(): assert run("LIMITED_TOPIC_AUTHORITY").authority_consumed
def test_explicit_limited_uses_authoritative(): assert run("LIMITED_TOPIC_AUTHORITY").consumer_topic is Topic.HEALTH
def test_normal_route_never_consumes(): assert not run("LIMITED_TOPIC_AUTHORITY", TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH).authority_consumed
def test_observation_precedes_consumption():
    sink = InMemoryTopicAuthorityObservationSink(); result = run("LIMITED_TOPIC_AUTHORITY", sink=sink); assert result.authority_consumed and len(sink.observations) == 1
def test_sink_failure_fails_closed(): assert not run("LIMITED_TOPIC_AUTHORITY", sink=BrokenSink()).authority_consumed
def test_sink_failure_preserves_deterministic(): assert run("LIMITED_TOPIC_AUTHORITY", sink=BrokenSink()).consumer_topic is Topic.SCIENCE
def test_sink_failure_uses_canonical_warning(): assert EditorialResolutionWarning.AUTHORITY_OBSERVATION_FAILED in run("LIMITED_TOPIC_AUTHORITY", sink=BrokenSink()).warnings
def test_sink_failure_does_not_leak_exception(): assert "raw secret" not in repr(run("LIMITED_TOPIC_AUTHORITY", sink=BrokenSink()))
def test_consumer_failure_fails_closed(): assert run("LIMITED_TOPIC_AUTHORITY", consumer=BrokenConsumer()).consumer_topic is Topic.SCIENCE
def test_stop_signal_switches_to_shadow(): assert run("LIMITED_TOPIC_AUTHORITY", stop=signal()).authority_mode is ResolverAuthorityMode.SHADOW
def test_stop_signal_prevents_consumption(): assert not run("LIMITED_TOPIC_AUTHORITY", stop=signal()).authority_consumed
def test_stop_signal_is_visible(): assert run("LIMITED_TOPIC_AUTHORITY", stop=signal()).stop_recommended
def test_without_stop_is_false(): assert not run().stop_recommended
def test_dual_and_consumer_provenance():
    result = run("LIMITED_TOPIC_AUTHORITY"); assert (result.deterministic_topic, result.resolved_topic, result.authoritative_topic, result.consumer_topic) == (Topic.SCIENCE, Topic.HEALTH, Topic.HEALTH, Topic.HEALTH)
def test_authority_applied_differs_from_consumed():
    result = run("LIMITED_TOPIC_AUTHORITY", TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH); assert result.authority_applied and not result.authority_consumed and result.authority_source.value == "ADJUDICATION" and result.consumer_source.value == "DETERMINISTIC_V1"
def test_sanitized_result_type(): assert isinstance(run(), SanitizedTopicAuthorityCanaryResult)
def test_sanitized_result_serializable(): json.dumps(asdict(run()), ensure_ascii=False)
@pytest.mark.parametrize("name", ["article_body", "headline", "raw_source", "raw_request", "raw_prompt", "raw_provider_response", "provider_exception", "api_key", "authorization_headers", "chain_of_thought"])
def test_sanitized_boundary_excludes_sensitive_fields(name): assert name not in {f.name for f in fields(SanitizedTopicAuthorityCanaryResult)}
def test_provider_failure_observation_fails_safe():
    obs = observation(provider_used=False, provider_valid=False); assert not run("LIMITED_TOPIC_AUTHORITY", obs=obs, item=replace(decision(), authoritative_topic=Topic.SCIENCE, authority_applied=False, authority_source=decision().authority_source.DETERMINISTIC_V1, block_reasons=(__import__('src.resolution', fromlist=['TopicAuthorityBlockReason']).TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE,))).authority_consumed
def test_end_to_end_operational_enablement_and_kill_switch():
    config = TopicAuthorityRuntimeConfig(); sink = InMemoryTopicAuthorityObservationSink(); runtime = OperationalTopicAuthorityCanary(config, sink)
    first = runtime.execute(decision(), observation(), INTERNAL)
    config.set_mode("LIMITED_TOPIC_AUTHORITY"); second = runtime.execute(decision(), replace(observation(), decision_fingerprint="second"), INTERNAL)
    runtime.execute(decision(), replace(observation(), decision_fingerprint="stop"), INTERNAL, signal())
    future = runtime.execute(decision(), replace(observation(), decision_fingerprint="future"), INTERNAL)
    assert not first.authority_consumed and second.authority_consumed and not future.authority_consumed
    assert future.consumer_topic is Topic.SCIENCE and len(sink.observations) == 4

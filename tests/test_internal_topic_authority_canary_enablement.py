"""Offline enablement tests for the explicit INTERNAL_SINGLE_PATH route."""

from dataclasses import fields, replace
import inspect

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.resolution import (
    EditorialResolutionSource, EditorialResolutionWarning,
    InMemoryTopicAuthorityObservationSink, ResolverAuthorityMode,
    SanitizedTopicAuthorityCanaryResult, TopicAuthorityBlockReason,
    TopicAuthorityCanaryRouteConfig, TopicAuthorityConsumerRoute,
    TopicAuthorityRuntimeConfig,
)
from src.topic.topic import Topic
from src.workflows.internal_topic_authority_canary import (
    InternalTopicAuthorityCanaryEntrypoint,
)
from tests.test_controlled_topic_authority_canary_workflow import ARTICLE, FakeProvider, _workflow


NORMAL = TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH
INTERNAL = TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH


def entrypoint(*, enabled=False, mode=ResolverAuthorityMode.SHADOW, provider=None, sink=None):
    workflow, provider, gate = _workflow(mode=mode, provider=provider)
    if sink is not None:
        workflow.operational_canary.sink = sink
    entry = InternalTopicAuthorityCanaryEntrypoint(
        workflow,
        TopicAuthorityCanaryRouteConfig(
            route_enabled=enabled, session_identifier="offline-session"
        ),
    )
    return entry, workflow, provider, gate


def run(**kwargs):
    entry, workflow, provider, gate = entrypoint(**kwargs)
    return entry.run_internal_topic_authority_canary(**ARTICLE), entry, workflow, provider, gate


def test_default_route_is_normal(): assert TopicAuthorityCanaryRouteConfig().resolve_route() is NORMAL
def test_internal_route_disabled_by_default(): assert TopicAuthorityCanaryRouteConfig().route_enabled is False
def test_explicit_internal_route_selection(): assert TopicAuthorityCanaryRouteConfig(True).resolve_route() is INTERNAL
def test_disabled_route_limited_cannot_consume(): assert not run(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)[0].authority_consumed
def test_enabled_route_shadow_cannot_consume(): assert not run(enabled=True)[0].authority_consumed
def test_enabled_limited_eligible_can_consume(): assert run(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)[0].authority_consumed
def test_enabled_limited_uses_authoritative_topic():
    result = run(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)[0]; assert result.consumer_topic is result.authoritative_topic
@pytest.mark.parametrize("mode", list(ResolverAuthorityMode))
@pytest.mark.parametrize("enabled", [False, True])
def test_fail_closed_matrix_except_explicit_pair(enabled, mode):
    result = run(enabled=enabled, mode=mode)[0]
    assert result.authority_consumed is (enabled and mode is ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
def test_blocked_decision_preserves_deterministic():
    result = run(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, provider=FakeProvider(confidence=AdjudicationConfidence.LOW))[0]
    assert not result.authority_consumed and result.consumer_topic is result.deterministic_topic
def test_route_disable_immediately_prevents_consumption():
    enabled = run(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)[0]
    disabled = run(enabled=False, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)[0]
    assert enabled.authority_consumed and not disabled.authority_consumed
def test_kill_switch_next_request_deterministic():
    entry, workflow, _, _ = entrypoint(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    first = entry.run_internal_topic_authority_canary(**ARTICLE)
    workflow.runtime_config.set_mode(ResolverAuthorityMode.SHADOW)
    second = entry.run_internal_topic_authority_canary(**ARTICLE)
    assert first.authority_consumed and not second.authority_consumed and second.consumer_topic is second.deterministic_topic
def test_kill_switch_has_no_stale_authority():
    entry, workflow, _, _ = entrypoint(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    workflow.runtime_config.set_mode(ResolverAuthorityMode.SHADOW)
    assert all(not entry.run_internal_topic_authority_canary(**ARTICLE).authority_consumed for _ in range(2))
def test_route_may_remain_enabled_in_shadow():
    result, entry, _, _, _ = run(enabled=True); assert entry.route_config.route_enabled and not result.authority_consumed
@pytest.mark.parametrize("confidence", [AdjudicationConfidence.LOW])
def test_low_confidence_blocked(confidence): assert not run(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, provider=FakeProvider(confidence=confidence))[0].authority_consumed
def test_review_and_ambiguity_blocked(): assert not run(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, provider=FakeProvider(ambiguity=True))[0].authority_consumed
@pytest.mark.parametrize("field,reason", [("response_valid", TopicAuthorityBlockReason.RESPONSE_INVALID), ("candidate_compliant", TopicAuthorityBlockReason.CANDIDATE_INVALID), ("fingerprint_valid", TopicAuthorityBlockReason.FINGERPRINT_INVALID), ("provider_available", TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE)])
def test_trust_failure_blocked(field, reason):
    entry, workflow, _, _ = entrypoint(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    result = workflow.analyze_operational(route=entry.route_config.resolve_route(), **ARTICLE, **{field: False})
    assert not result.authority_consumed and reason in result.block_reasons
def test_no_topic_change_not_consumed(): assert not run(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, provider=FakeProvider(same=True))[0].authority_consumed
class BrokenSink:
    def record(self, _): raise RuntimeError("unsafe raw payload")
def test_observation_failure_not_consumed():
    result = run(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, sink=BrokenSink())[0]
    assert not result.authority_consumed and result.consumer_topic is result.deterministic_topic and EditorialResolutionWarning.AUTHORITY_OBSERVATION_FAILED in result.warnings
@pytest.mark.parametrize("name", ["authoritative_format", "consumer_format", "authoritative_reader_intent", "consumer_reader_intent"])
def test_format_and_intent_unchanged(name): assert name not in {item.name for item in fields(SanitizedTopicAuthorityCanaryResult)}
def test_normal_consumer_unaffected(): assert run(enabled=False, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)[0].route is NORMAL
def test_no_global_route_mutation():
    assert TopicAuthorityCanaryRouteConfig(True).resolve_route() is INTERNAL and TopicAuthorityCanaryRouteConfig().resolve_route() is NORMAL
def test_request_local_config(): assert TopicAuthorityCanaryRouteConfig(True) is not TopicAuthorityCanaryRouteConfig(True)
def test_sanitized_output_only(): assert isinstance(run(enabled=True)[0], SanitizedTopicAuthorityCanaryResult)
def test_internal_only_marker(): assert InternalTopicAuthorityCanaryEntrypoint.INTERNAL_ONLY is True
def test_no_public_default_registration(): assert "InternalTopicAuthorityCanaryEntrypoint" not in (inspect.getsource(__import__("src.workflows", fromlist=["*"])))
def test_no_real_provider_call():
    result, _, _, provider, _ = run(enabled=False); assert provider.provider_name == "fake" and result.provider_used is True
def test_required_provenance_fields():
    assert {"deterministic_topic", "resolved_topic", "authoritative_topic", "consumer_topic", "authority_mode", "route", "authority_applied", "authority_consumed", "authority_source", "resolution_status", "review_required", "ambiguity_remaining", "provider_used", "provider_confidence", "block_reasons", "warnings", "stop_recommended"} <= {item.name for item in fields(SanitizedTopicAuthorityCanaryResult)}
def test_audit_identity_available_in_observation():
    entry, workflow, _, _ = entrypoint(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, sink=InMemoryTopicAuthorityObservationSink())
    entry.run_internal_topic_authority_canary(**ARTICLE)
    assert workflow.operational_canary.sink.observations[0].decision_fingerprint
def test_no_automatic_correctness_field(): assert "correct" not in {item.name for item in fields(SanitizedTopicAuthorityCanaryResult)}
def test_end_to_end_fake_canary_matrix():
    normal = run()[0]
    enabled_shadow = run(enabled=True)[0]
    limited = run(enabled=True, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)[0]
    disabled_limited = run(enabled=False, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)[0]
    assert not normal.authority_consumed and not enabled_shadow.authority_consumed
    assert limited.authority_consumed and not disabled_limited.authority_consumed

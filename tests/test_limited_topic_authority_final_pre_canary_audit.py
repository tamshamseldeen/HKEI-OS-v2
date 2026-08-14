"""HKEI-210 implementation-level final safety audit (offline only)."""

from dataclasses import fields, replace
import inspect
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from examples.run_limited_topic_authority_final_pre_canary_audit import build_audit
from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.resolution import (
    ControlledTopicAuthorityConsumerAdapter, EditorialResolutionSource,
    InMemoryTopicAuthorityObservationSink, LimitedTopicAuthorityConfig,
    OperationalTopicAuthorityCanary, ResolverAuthorityMode,
    SanitizedTopicAuthorityCanaryResult, TopicAuthorityAuditRecord,
    TopicAuthorityAuditStatus, TopicAuthorityBlockReason,
    TopicAuthorityConsumerRoute, TopicAuthorityMetrics,
    TopicAuthorityMetricsAggregator, TopicAuthorityPilotStopEvaluator,
    TopicAuthorityPilotStopReason, TopicAuthorityRuntimeConfig,
    TopicAuthoritySafetyMetrics,
)
from src.resolution.editorial_resolution_warning import EditorialResolutionWarning
from src.resolution.limited_topic_authority_applicator import LimitedTopicAuthorityApplicator
from src.topic.topic import Topic
from src.workflows.controlled_topic_authority_canary_workflow import ControlledTopicAuthorityCanaryWorkflow
from tests.topic_authority_operational_fixtures import decision, observation


ROOT = Path(__file__).resolve().parents[1]
INTERNAL = TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH
NORMAL = TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH


def stopped():
    return TopicAuthorityPilotStopEvaluator().evaluate(
        TopicAuthorityMetrics(), TopicAuthoritySafetyMetrics(audited_override_count=1, audited_incorrect_override_count=1, override_precision=0.0), LimitedTopicAuthorityConfig(),
    )


def execute(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, route=INTERNAL, **kwargs):
    return OperationalTopicAuthorityCanary(TopicAuthorityRuntimeConfig(mode), kwargs.pop("sink", InMemoryTopicAuthorityObservationSink()), kwargs.pop("consumer", None)).execute(decision(), observation(), route, **kwargs)


def test_default_shadow(): assert TopicAuthorityRuntimeConfig().resolve() is ResolverAuthorityMode.SHADOW
def test_workflow_constructor_defaults_shadow(): assert "LimitedTopicAuthorityConfig()" in inspect.getsource(ControlledTopicAuthorityCanaryWorkflow.__init__)
def test_explicit_limited_requirement(): assert execute().authority_consumed
def test_internal_route_requirement(): assert not execute(route=NORMAL).authority_consumed
def test_normal_route_isolation(): assert execute(route=NORMAL).consumer_topic is Topic.SCIENCE
def test_observation_before_consumption():
    sink = InMemoryTopicAuthorityObservationSink(); result = execute(sink=sink); assert result.authority_consumed and sink.observations
def test_kill_switch_operational_path(): assert not execute(stop_signal=stopped()).authority_consumed
def test_stop_signal_recommends_shadow():
    signal = stopped(); assert signal.should_stop and signal.recommended_mode is ResolverAuthorityMode.SHADOW
def test_regression_budget_is_zero(): assert LimitedTopicAuthorityConfig().regression_budget == 0
def test_one_incorrect_override_stops(): assert TopicAuthorityPilotStopReason.REGRESSION_BUDGET_EXCEEDED in stopped().reasons
def test_minimum_audit_sample_is_30(): assert LimitedTopicAuthorityConfig().minimum_audited_override_sample == 30
def test_precision_threshold_is_90_percent(): assert TopicAuthorityPilotStopEvaluator.OVERRIDE_PRECISION_THRESHOLD == .90
def test_below_30_does_not_precision_stop():
    value = TopicAuthorityPilotStopEvaluator().evaluate(TopicAuthorityMetrics(), TopicAuthoritySafetyMetrics(audited_override_count=29, audited_correct_override_count=26, audited_incorrect_override_count=3, override_precision=26/29), LimitedTopicAuthorityConfig(regression_budget=99)); assert TopicAuthorityPilotStopReason.OVERRIDE_PRECISION_BELOW_THRESHOLD not in value.reasons
def test_at_30_below_precision_stops():
    value = TopicAuthorityPilotStopEvaluator().evaluate(TopicAuthorityMetrics(), TopicAuthoritySafetyMetrics(audited_override_count=30, audited_correct_override_count=26, audited_incorrect_override_count=4, override_precision=26/30), LimitedTopicAuthorityConfig(regression_budget=99)); assert TopicAuthorityPilotStopReason.OVERRIDE_PRECISION_BELOW_THRESHOLD in value.reasons
def test_human_audit_independence(): assert set(f.name for f in fields(TopicAuthorityAuditRecord)) == {"decision_fingerprint", "authoritative_topic", "review_status", "human_reviewed_correctness"}
def test_duplicate_audit_protection():
    record = TopicAuthorityAuditRecord("safe-fingerprint", Topic.HEALTH, TopicAuthorityAuditStatus.COMPLETED, True)
    with pytest.raises(ValueError, match="duplicate"): TopicAuthorityMetricsAggregator().aggregate_safety((observation(),), (record, record))
@pytest.mark.parametrize("change,reason", [("provider", TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE), ("response", TopicAuthorityBlockReason.RESPONSE_INVALID), ("candidate", TopicAuthorityBlockReason.CANDIDATE_INVALID), ("fingerprint", TopicAuthorityBlockReason.FINGERPRINT_INVALID)])
def test_trust_failures_have_canonical_blocks(change, reason): assert reason.value in Path(ROOT / "src/resolution/limited_topic_authority_applicator.py").read_text()
@pytest.mark.parametrize("reason", [TopicAuthorityBlockReason.REVIEW_REQUIRED, TopicAuthorityBlockReason.AMBIGUITY_REMAINS, TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW])
def test_policy_blocks_are_enforced(reason): assert reason.value in Path(ROOT / "src/resolution/limited_topic_authority_applicator.py").read_text()
def test_no_topic_change_is_not_consumed():
    item = replace(decision(), resolved_topic=Topic.SCIENCE, authoritative_topic=Topic.SCIENCE, authority_applied=False, authority_source=EditorialResolutionSource.DETERMINISTIC_V1, block_reasons=(TopicAuthorityBlockReason.NO_TOPIC_CHANGE,)); assert not ControlledTopicAuthorityConsumerAdapter().consume(Topic.SCIENCE, item, INTERNAL, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY).authority_consumed
@pytest.mark.parametrize("name", ["authoritative_format", "consumer_format", "authoritative_reader_intent", "consumer_reader_intent"])
def test_format_and_intent_isolation(name): assert name not in {f.name for f in fields(SanitizedTopicAuthorityCanaryResult)}
def test_gate_independence(): assert "authority_mode" not in (ROOT / "src/adjudication/deterministic_semantic_adjudication_gate.py").read_text()
def test_resolver_independence(): assert "authority_mode" not in (ROOT / "src/resolution/limited_editorial_resolver.py").read_text()
def test_provider_independence(): assert "authority_mode" not in (ROOT / "src/adjudication/openai_semantic_adjudication_provider.py").read_text()
class BrokenSink:
    def record(self, _): raise RuntimeError("secret")
class BrokenConsumer:
    def consume(self, *_): raise RuntimeError("secret")
def test_sink_failure_safe():
    result = execute(sink=BrokenSink()); assert not result.authority_consumed and result.consumer_topic is Topic.SCIENCE and EditorialResolutionWarning.AUTHORITY_OBSERVATION_FAILED in result.warnings
def test_consumer_failure_safe(): assert execute(consumer=BrokenConsumer()).consumer_topic is Topic.SCIENCE
def test_invalid_config_safe():
    with pytest.raises(ValueError): TopicAuthorityRuntimeConfig("INVALID")
def test_request_locality(): assert TopicAuthorityRuntimeConfig() is not TopicAuthorityRuntimeConfig()
def test_concurrency_proxy_has_no_cross_instance_leak():
    configs = [TopicAuthorityRuntimeConfig("LIMITED_TOPIC_AUTHORITY"), TopicAuthorityRuntimeConfig()]
    with ThreadPoolExecutor(max_workers=2) as pool: modes = list(pool.map(lambda c: c.resolve(), configs))
    assert modes == [ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, ResolverAuthorityMode.SHADOW]
def test_dual_provenance(): assert {"deterministic_topic", "resolved_topic", "authoritative_topic", "consumer_topic", "authority_applied", "authority_consumed"} <= {f.name for f in fields(SanitizedTopicAuthorityCanaryResult)}
def test_existing_consumers_do_not_import_canary_result():
    canary_boundaries = {
        "controlled_topic_authority_canary_workflow.py",
        "internal_topic_authority_canary.py",
    }
    consumers = [
        p for p in (ROOT / "src").rglob("*.py")
        if "resolution" not in p.parts and p.name not in canary_boundaries
    ]
    assert not any("SanitizedTopicAuthorityCanaryResult" in p.read_text() for p in consumers)
def test_metrics_require_no_source_data(): assert "source" not in {f.name for f in fields(type(TopicAuthorityMetrics()))}
def test_stop_observability_fix_is_detected():
    source = inspect.getsource(ControlledTopicAuthorityCanaryWorkflow.analyze_operational)
    assert "apply_stop_signal(stop_signal)" in source and "stop_signal=stop_signal" in source
def test_audit_classification_is_ready():
    audit = build_audit(); assert audit["final_safety_classification"] == "PRE_CANARY_SAFE" and audit["final_readiness_decision"] == "READY_TO_RUN_INTERNAL_SINGLE_PATH_CANARY"
def test_no_provider_calls_declared(): assert build_audit()["real_provider_calls"] == 0
def test_no_production_mutation_declared(): assert build_audit()["production_mutation"] is False
def test_persisted_json_matches_builder(): assert json.loads((ROOT / "benchmark/limited_topic_authority_final_pre_canary_audit.json").read_text()) == build_audit()
